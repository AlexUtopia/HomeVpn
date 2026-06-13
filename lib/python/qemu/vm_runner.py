import threading
import time

from lib.python.logger import Logger
from lib.python.pci import Pci, PciPassthroughMode, Vfio, VfioPci
from lib.python.power import Power
from lib.python.startup import RunAfterReboot
from lib.python.system import LinuxKernel
from lib.python.utils import ShellSerializer
from lib.python.vm import Virtio, VmRegistry

from lib.python.qemu import QemuBuiltinKeyboardAndMousePassthrough, QemuCdRom, QemuPlatform, QemuRam


class VmRunner:
    def __init__(self, vm_name, project_config=OpenVpnConfig(), block_internet_access=False,
                 initiate_vga_passthrough=PciPassthroughMode.NONE,
                 initiate_vga_audio_passthrough=PciPassthroughMode.NONE,
                 initiate_usb_host_passthrough=PciPassthroughMode.NONE,
                 initiate_isa_bridge_passthrough=PciPassthroughMode.NONE,
                 initiate_builtin_kbd_and_mouse_passthrough=False,
                 asc_override_patched_kernel=False,
                 qemu_pci_passthrough=None, grub_config_backup_path=None,
                 vm_platform=None, ram=None, os_distr_path=None, vm_host_mode=False):
        self.__vm_name = vm_name
        self.__project_config = project_config
        self.__block_internet_access = bool(block_internet_access)
        self.__initiate_vga_passthrough = PciPassthroughMode(initiate_vga_passthrough)
        self.__initiate_vga_audio_passthrough = PciPassthroughMode(initiate_vga_audio_passthrough)
        self.__initiate_usb_host_passthrough = PciPassthroughMode(initiate_usb_host_passthrough)
        self.__initiate_isa_bridge_passthrough = PciPassthroughMode(initiate_isa_bridge_passthrough)
        self.__initiate_builtin_kbd_and_mouse_passthrough = bool(initiate_builtin_kbd_and_mouse_passthrough)
        self.__asc_override_patched_kernel = bool(asc_override_patched_kernel)
        self.__qemu_pci_passthrough = qemu_pci_passthrough
        self.__vm_platform = vm_platform
        self.__ram = ram
        self.__os_distr_path = os_distr_path
        self.__vm_host_mode = bool(vm_host_mode)
        self.__grub = Grub(grub_config_backup_path=grub_config_backup_path)
        self.__serializer = ShellSerializer()
        self.__run_after_reboot = RunAfterReboot()

    def run(self):
        if self.__initiate_vga_passthrough or self.__initiate_usb_host_passthrough or self.__initiate_isa_bridge_passthrough:
            self.before_reboot()
        else:
            self.__run()

    def before_reboot(self):
        pci_list = Pci.get_list()
        if not pci_list.is_iommu_enabled():
            Logger.instance().warning(
                "[Vm] Enable IOMMU (VT-d/AMD-Vi) in host BIOS/UEFI.\n     See guide https://us.informatiweb.net/tutorials/it/bios/enable-iommu-or-vt-d-in-your-bios.html")

            grub_config_backup_path = self.__grub.append_cmd_line_linux(
                Vfio(VfioPci(Pci.PciList())).get_kernel_parameters())
            if grub_config_backup_path is None:
                Logger.instance().error("[Vm] Make GRUB config backup FAIL")
                return
            self.__grub.update()
            Logger.instance().info(
                f"[Vm] GRUB config for IOMMU applied\n     GRUB backup: \"{grub_config_backup_path}\"")
            return

        pci_list_for_passthrough = Pci.PciList()
        pci_list_for_passthrough.update(self.__get_pci_vga_list_for_passthrough(pci_list))
        pci_list_for_passthrough.update(self.__get_usb_host_list_for_passthrough(pci_list))
        pci_list_for_passthrough.update(self.__get_isa_bridge_list_for_passthrough(pci_list))

        if len(pci_list_for_passthrough) == 0:
            Logger.instance().warning("[Vm] PCI passthrough devices NOT FOUND")
            return

        check_iommu_group_for_passthrough = pci_list.check_iommu_group_for_passthrough(pci_list_for_passthrough)
        if check_iommu_group_for_passthrough is False:
            if self.__asc_override_patched_kernel:
                Logger.instance().warning("[Vm] Add ASC override patched kernel")
                LinuxKernel().download_and_install_liquorix_kernel()
                # Параметр GRUB_TOP_LEVEL доступен начиная с GRUB 2.12
                # После завершения работы виртуальной машины ядро не откатываем.
                # Пользователь может самостоятельно или удалить liquorix ядро (пакет) или воспользоваться grub-customizer
                # Если бы откат на предыдущее ядро после выключения виртуальной машины был доступен, то пришлось бы решать следующие проблемы:
                # 1. установка GRUB_TOP_LEVEL на предыдущее ядро блокирует использование обновленного умолчательного ядра
                # 2. удаление liquorix ядра (а соответственно и правильный автоматический откат на умолчательное ядро) приводит постоянному скачиванию и установке liquorix ядра
                #    - это лишний интернет трафик
                # 3. если GRUB не чувствителен к GRUB_TOP_LEVEL, то liquorix ядро может не примениться из-за того что это ядро по версии меньше последнего умолчательного
                # 4. при использовании GRUB_TOP_LEVEL на liquorix ядро GRUB будет не чувствителен к обновлениям этого ядра
                # 5. установка GRUB_DEFAULT и/или GRUB_TOP_LEVEL мешает обновлению ядер, например, параметры указывают на удалённое ядро
                # 6. может быть единственно правильный вариант: скачивать liquorix ядро в виде deb пакета (apt download), устанавливать перед запуском виртуальной машины и удалять после
                #    (придётся решать проблему поиска последней версии liquorix ядра вручную)
                # 6.1 или пересборка текущего умолчательного ядра с ASC override патчем
                # self.__grub.set_top_level(self.__grub.get_last_liquorix_kernel_path())
                grub_config_backup_path = self.__grub.append_cmd_line_linux(
                    Vfio(VfioPci(Pci.PciList())).get_kernel_parameters(), is_acs_override=True)
                if grub_config_backup_path is None:
                    Logger.instance().error("[Vm] Make GRUB config backup FAIL")
                    return
                self.__grub.update()
                Logger.instance().warning(f"[Vm] Reboot PC and retry\n     GRUB backup: {grub_config_backup_path}")
            else:
                Logger.instance().warning(
                    "[Vm] For PCI passthrough require ASC override patched kernel.\n     Add --asc_override_patched_kernel parameter and retry")
            return
        elif check_iommu_group_for_passthrough is None:
            return

        vfio_pci = VfioPci(pci_list_for_passthrough)
        vfio = Vfio(vfio_pci)

        grub_config_backup_path = self.__grub.append_cmd_line_linux(vfio.get_kernel_parameters())
        if grub_config_backup_path is None:
            Logger.instance().error("[Vm] Make GRUB config backup FAIL")
            return
        self.__grub.update()

        self.__run_after_reboot.register_after_reboot_handler(self, self.after_reboot, is_reboot=True)

    def after_reboot(self):
        sleep_sec = 20
        # Требуется для инициализации сетевой инфраструктуры (WiFi) иначе vm не стартанёт
        # Logger.instance().debug(f"[Vm] Sleep {sleep_sec} before vm run")
        time.sleep(sleep_sec)
        # dmesg_output = subprocess.run("dmesg", shell=True, capture_output=True, text=True)
        # Logger.instance().debug(f"[Vm] dmesg:\n{dmesg_output.stdout}\n")
        Logger.instance().debug(f"[Vm] PCI device list:\n{Pci.get_list()}\n")

        is_normal_exit = False
        for i in range(1):
            try:
                self.__run()
                is_normal_exit = True
            except Exception as ex:
                Logger.instance().exception(f"[Vm] {i} Run after reboot FAIL")

        self.__exit(is_normal_exit)

    def __get_pci_vga_list_for_passthrough(self, pci_list):
        if not self.__initiate_vga_passthrough:
            return Pci.PciList()

        # VGA + Audio controller
        result = pci_list.get_vga_list(mode=self.__initiate_vga_passthrough,
                                       vga_audio_passthrough_mode=self.__initiate_vga_audio_passthrough)
        if len(result) == 0:
            Logger.instance().warning("[Vm] PCI VGA NOT FOUND")
            return Pci.PciList()

        if len(result.get_vga_list()) > 1:
            Logger.instance().warning("[Vm] Multiple VGA FOUND")  # fixme utopia Дать выбрать какой VGA пробрасывать
            return Pci.PciList()

        return result

    def __get_usb_host_list_for_passthrough(self, pci_list):
        if not self.__initiate_usb_host_passthrough:
            return Pci.PciList()

        result = pci_list.get_usb_host_list(mode=self.__initiate_usb_host_passthrough)
        if len(result) == 0:
            Logger.instance().warning("[Vm] PCI USB Host NOT FOUND")
            return Pci.PciList()

        return result

    def __get_isa_bridge_list_for_passthrough(self, pci_list):
        if not self.__initiate_isa_bridge_passthrough:
            return Pci.PciList()

        result = pci_list.get_isa_bridge_list(mode=self.__initiate_isa_bridge_passthrough)
        if len(result) == 0:
            Logger.instance().warning("[Vm] PCI ISA bridge NOT FOUND")
            return Pci.PciList()

        return result

    def __run(self):
        network_bridge = NetworkBridge(self.__project_config.get_server_name(),
                                       self.__project_config.get_vm_bridge_ip_address_and_mask(),
                                       self.__project_config.get_dns_config_dir_path(),
                                       self.__project_config.get_internet_network_interface(),
                                       block_internet_access=self.__block_internet_access,
                                       dns_suffix=self.__project_config.get_dns_suffix(),
                                       my_host=self.__project_config.get_my_host())

        vm_registry = VmRegistry(self.__project_config.get_vm_registry_dir_path())
        vm_meta_data = vm_registry.get_with_verifying(self.__vm_name)

        local_network_interface = OpenVpnConfig.get_or_default_local_network_interface(
            self.__project_config.get_local_network_interface())

        vm_ssh_forwarding = VmSshForwarding(vm_meta_data, local_network_interface,
                                            vm_meta_data.get_ssh_forward_port())
        vm_rdp_forwarding = VmRdpForwarding(vm_meta_data, local_network_interface,
                                            vm_meta_data.get_rdp_forward_port())
        stop_event = threading.Event()
        tcp_forwarding_thread = threading.Thread(
            target=lambda _stop_event: (vm_ssh_forwarding.add_with_retry(_stop_event),
                                        vm_rdp_forwarding.add_with_retry(_stop_event)), args=(stop_event,))
        tcp_forwarding_thread.start()

        if self.__initiate_isa_bridge_passthrough and self.__initiate_builtin_kbd_and_mouse_passthrough:
            self.__initiate_builtin_kbd_and_mouse_passthrough = False
            Logger.instance().warning(
                "[Vm] ignore --builtin_kbd_and_mouse_passthrough parameter because of --initiate_isa_bridge_passthrough parameter enabled")

        qemu_builtin_kbd_and_mouse_passthrough = None
        if self.__initiate_builtin_kbd_and_mouse_passthrough:
            qemu_builtin_kbd_and_mouse_passthrough = QemuBuiltinKeyboardAndMousePassthrough()

        vm = VirtualMachine(network_bridge, vm_meta_data,
                            qemu_pci_passthrough=self.__qemu_pci_passthrough,
                            qemu_platform=QemuPlatform(vm_meta_data, self.__vm_platform),
                            qemu_cdrom=QemuCdRom(self.__os_distr_path, Virtio(self.__project_config).get_win_drivers()),
                            qemu_builtin_kbd_and_mouse_passthrough=qemu_builtin_kbd_and_mouse_passthrough,
                            qemu_ram=self.__ram)
        vm.run()
        stop_event.set()
        tcp_forwarding_thread.join()

    def __exit(self, is_normal_exit):
        if self.__vm_host_mode and is_normal_exit:
            Power.poweroff()
        else:
            self.__grub.restore_from_backup()
            self.__grub.update()
            Power.reboot()

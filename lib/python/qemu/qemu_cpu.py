import psutil

from lib.python.logger import Logger

# fixme utopia Требуется ли? ,kvm=off
# https://www.qemu.org/docs/master/system/i386/hyperv.html
# qemu-system-$(uname -m) -cpu help
class QemuCpu:
    def __init__(self):
        pass

    def get_qemu_parameters(self) -> dict:
        logical_cpu_count = psutil.cpu_count(logical=True)
        if not logical_cpu_count:
            logical_cpu_count = 1
            Logger.instance().warning(f"[Cpu] logic cores count undefined, use {logical_cpu_count} core")
        return {"-cpu": self.__get_cpu_parameter_value(),
                "-smp": {"cpus": logical_cpu_count, "maxcpus": logical_cpu_count}}

    def __get_cpu_parameter_value(self):
        return "host" if Cpu.is_win11_support() else "Icelake-Server"
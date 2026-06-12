
from lib.python.utils import DaemonManagerBase

# https://qemu-project.gitlab.io/qemu/specs/tpm.html
# https://en.opensuse.org/Software_TPM_Emulator_For_QEMU
# https://www.qemu.org/docs/master/system/invocation.html#hxtool-7
# swtpm for qemu-system-aarch64 on x86_64 host: https://share.google/aimode/QIUU02ekQzac1b1ew
class TpmEmulator(DaemonManagerBase):
    PREFIX = "swtpm"
    TPM_CMD = "swtpm"
    TPM_DEVICE_DEFAULT = "tpm-tis"

    class TpmSerializer(ShellSerializer):
        class TpmEscapeLiteral(EscapeLiteral):
            def __init__(self):
                super().__init__(encode_table=[(",", ",,")])

        def __init__(self):
            super().__init__(key_value_separator_table=[
                {"prefix": "", "separator": " "}], quotes_for_string_value="", nested_serializer=ShellSerializer(
                key_value_separator_table=[
                    {"prefix": "",
                     "separator": " "}],
                pair_separator=" ",
                escape_literal=QemuSerializer.QemuEscapeLiteral(),
                nested_serializer=ShellSerializer(
                    quotes_for_string_value="",
                    key_value_separator_table=[
                        {"prefix": "",
                         "separator": "="}],
                    pair_separator=",",
                    escape_literal=QemuSerializer.QemuEscapeLiteral()),
                nested_key_value_separator=" "
            ))

    def __init__(self, vm_meta_data, is_tpm2_0=True, log_level=20):
        super().__init__(label="TpmEmulator", action="Start")
        self.__vm_meta_data = vm_meta_data
        self.__is_tpm2_0 = is_tpm2_0
        self.__log_level = log_level
        self.__serializer = TpmEmulator.TpmSerializer()

    def get_qemu_parameters(self):
        self.__get_tpm_state_dir_path().mkdir(parents=True, exist_ok=True)
        return [{"-chardev": {"socket": {"id": self.__get_tpm_chardev_id(),
                                         "path": self.__get_tpm_chardev_ctrl_unixsocket_path()}}},
                {"-tpmdev": {
                    "emulator": {"id": self.__get_tpm_dev_id(), "chardev": self.__get_tpm_chardev_id()}}},

                {"-device": {
                    self.__get_tpm_dev_model(): {"tpmdev": self.__get_tpm_dev_id()}}}
                ]

    def _start_impl(self):
        self.__get_tpm_state_dir_path().mkdir(parents=True, exist_ok=True)

    def _close_impl(self):
        return

    def _build_command_line(self):
        return f"{self.TPM_CMD} {self.__serializer.serialize(self.__get_command_line_args())}"

    def __get_command_line_args(self):
        return {"socket": [{"--tpmstate": {"dir": self.__get_tpm_state_dir_path()}},
                           {"--ctrl": {"type": "unixio", "path": self.__get_tpm_chardev_ctrl_unixsocket_path()}},
                           "--tpm2" if self.__is_tpm2_0 else "",
                           {"--log": {"level": self.__log_level, "file": self.__get_tpm_log_file_path()}},
                           "--daemon"]}

    def __get_tpm_chardev_id(self):
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-chardev-id"

    def __get_tpm_chardev_ctrl_unixsocket_path(self):
        return self.__get_tpm_state_dir_path() / self.__get_tpm_chardev_ctrl_unixsocket_name()

    def __get_tpm_log_file_path(self):
        return self.__get_tpm_state_dir_path() / f"{self.PREFIX}.log"

    def __get_tpm_state_dir_path(self):
        return self.__vm_meta_data.get_working_dir_path() / self.PREFIX

    def __get_tpm_chardev_ctrl_unixsocket_name(self):
        return f"{self.PREFIX}-sock"

    def __get_tpm_dev_model(self):
        # fixme utopia tpm-tis / tpm-spapr / tpm-tis-device / tpm-tis-i2c
        return self.TPM_DEVICE_DEFAULT

    def __get_tpm_dev_id(self):
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-dev-id"
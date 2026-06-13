from lib.python.qemu import QemuSerializer
from lib.python.types import Path
from lib.python.utils import DaemonManagerBase, EscapeLiteral, ShellSerializer
from lib.python.vm import VmMetaData


# https://qemu-project.gitlab.io/qemu/specs/tpm.html
# https://en.opensuse.org/Software_TPM_Emulator_For_QEMU
# https://www.qemu.org/docs/master/system/invocation.html#hxtool-7
# https://github.com/stefanberger/swtpm
# https://github.com/stefanberger/swtpm/wiki#compile-and-install-on-cygwin
# swtpm for qemu-system-aarch64 on x86_64 host: https://share.google/aimode/QIUU02ekQzac1b1ew
# https://www.google.com/search?q=qemu+on+windows+host+use+tpm&sca_esv=0d0ab61a20469979&biw=1242&bih=554&sxsrf=ANbL-n58uMqfRK04JNMFLRBeqg-kgvBlIQ%3A1781295213783&ei=bWgsauqoL7nPwPAPjYrcoA8&uact=5&sclient=gws-wiz-serp&udm=50&fbs=ADc_l-bs2zYa4_vOddERTHH0rF8CDbOPXIO2Jmt3O1q1mG8sqIBodZU9EysgsK8u7QK6IWDOptN89aOQj40J5PwHNgDxoMwPOlM4YRGOS6sBFB0xNiWcJvUB9-984xVL_FDQJZMzwVuMMVdUmLm4_ytgIX8K0XjgtAjEWZmArpwSN1edSe-6XWT6DtruYUiIxSLLxS14rVxgzyc3HdOoTsnkDnzX6VEiqcb_m1m-eg7T96Y6D1cfe8VzDXcaNtyNN5MUGiSr63j-vxQ43gcbH4i3ctYDR5M88w&aep=10&ntc=1&mstk=AUtExfAF7D4sfAjtyTTma4fLaT5iRQhraeDmARuffXIu0J2jvDG5XrMdb-q3TuWmtIA5l_jt6rJdyrwrAfwut9z0mwQWoJ-XygFY7IfxRkKDZXzkVlWZJb5t5lYVJ5ilYz9i8ghCChWRkGJs0lfuhBZ2vFmBdjYtsRIuziZQvddaeZxx8heTruuLLzfJZB9xMFK_TsjuAYlpKJSt7R25JVRA7ySh7wFaVVvDcObP55kks24m7FKZMj5mpcOkiLIPw6v9I5HmwktcdV7x2gUUwAqQn8Cqsz0BPUeLGu3k6WyBeE8Drh25sg3BgE1W_WWIil_9KcS3CJuCqPT--g&aioh=3&csuir=1&mtid=b2ssau_5NtWswPAPxv6wmQY&lns_mode=cvst
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

    def __init__(self, vm_meta_data: VmMetaData, is_tpm2_0: bool = True, log_level: int = 20):
        super().__init__(label="TpmEmulator", action="Start")
        self.__vm_meta_data = vm_meta_data
        self.__is_tpm2_0 = is_tpm2_0
        self.__log_level = log_level
        self.__serializer = TpmEmulator.TpmSerializer()

    def get_qemu_parameters(self) -> list[dict]:
        self.__get_tpm_state_dir_path().makedirs()
        return [{"-chardev": {"socket": {"id": self.__get_tpm_chardev_id(),
                                         "path": self.__get_tpm_chardev_ctrl_unixsocket_path()}}},
                {"-tpmdev": {
                    "emulator": {"id": self.__get_tpm_dev_id(), "chardev": self.__get_tpm_chardev_id()}}},

                {"-device": {
                    self.__get_tpm_dev_model(): {"tpmdev": self.__get_tpm_dev_id()}}}
                ]

    def _start_impl(self) -> None:
        self.__get_tpm_state_dir_path().makedirs()

    def _close_impl(self) -> None:
        return

    def _build_command_line(self) -> str:
        return f"{self.TPM_CMD} {self.__serializer.serialize(self.__get_command_line_args())}"

    def __get_command_line_args(self) -> dict:
        return {"socket": [{"--tpmstate": {"dir": self.__get_tpm_state_dir_path()}},
                           {"--ctrl": {"type": "unixio", "path": self.__get_tpm_chardev_ctrl_unixsocket_path()}},
                           "--tpm2" if self.__is_tpm2_0 else "",
                           {"--log": {"level": self.__log_level, "file": self.__get_tpm_log_file_path()}},
                           "--daemon"]}

    def __get_tpm_chardev_id(self) -> str:
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-chardev-id"

    def __get_tpm_chardev_ctrl_unixsocket_path(self) -> Path:
        return self.__get_tpm_state_dir_path() / self.__get_tpm_chardev_ctrl_unixsocket_name()

    def __get_tpm_log_file_path(self) -> Path:
        return self.__get_tpm_state_dir_path() / f"{self.PREFIX}.log"

    def __get_tpm_state_dir_path(self) -> Path:
        return self.__vm_meta_data.get_working_dir_path() / self.PREFIX

    def __get_tpm_chardev_ctrl_unixsocket_name(self) -> str:
        return f"{self.PREFIX}-sock"

    def __get_tpm_dev_model(self) -> str:
        # fixme utopia tpm-tis / tpm-spapr / tpm-tis-device / tpm-tis-i2c
        return self.TPM_DEVICE_DEFAULT

    def __get_tpm_dev_id(self) -> str:
        return f"{self.PREFIX}-{self.__vm_meta_data.get_name()}-dev-id"

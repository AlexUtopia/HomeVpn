import pathlib
import requests
import subprocess
import tempfile

from current_os import CurrentOs


class LinuxKernel:
    LIQUORIX_KERNEL_SETUP_SCRIPT_URL = "https://liquorix.net/install-liquorix.sh"

    def __init__(self):
        pass

    # https://liquorix.net/
    # fixme utopia Переписать под asyncio
    #  https://www.google.com/search?q=python+asyncio+download+file+&sca_esv=5c685c3490d49ca4&biw=1242&bih=554&sxsrf=ANbL-n4roDr99TKYrCeCWqLIBBaRna7v0g%3A1774556682905&ei=CpbFaYDrNpqPwPAPl5rIqAg&ved=0ahUKEwiAmN_lsr6TAxWaBxAIHRcNEoUQ4dUDCBE&uact=5&oq=python+asyncio+download+file+&gs_lp=Egxnd3Mtd2l6LXNlcnAiHXB5dGhvbiBhc3luY2lvIGRvd25sb2FkIGZpbGUgMgYQABgWGB4yBRAAGO8FMgUQABjvBUikaVCDEljOUXACeAGQAQCYAW2gAeEMqgEEMTAuN7gBA8gBAPgBAZgCE6ACqA7CAgoQABiwAxjWBBhHwgIKEAAYgAQYQxiKBcICBRAAGIAEwgIHEAAYgAQYCsICCBAAGIAEGMsBmAMAiAYBkAYIkgcEOC4xMaAHoUayBwQ2LjExuAeCDsIHCDAuMS4xMC44yAeXAYAIAA&sclient=gws-wiz-serp
    def download_and_install_liquorix_kernel(self):
        if not CurrentOs.is_linux():
            raise Exception(f"[LinuxKernel] Non Linux OS")

        if CurrentOs.is_debian_or_like() or CurrentOs.is_ubuntu_or_like() or CurrentOs.is_arch_or_like():
            response = requests.get(self.LIQUORIX_KERNEL_SETUP_SCRIPT_URL, stream=True)
            fp = tempfile.NamedTemporaryFile(delete=False)
            try:
                for chunk in response.iter_content(chunk_size=2 ** 16):
                    fp.write(chunk)
                fp.close()
                pathlib.Path(fp.name).chmod(0o777)
                subprocess.check_call(fp.name, shell=True)
            finally:
                fp.close()
                pathlib.Path(fp.name).unlink(missing_ok=True)
        else:
            raise Exception(
                f"[LinuxKernel] Install liquorix kernel NOT SUPPORTED for {CurrentOs.get_linux_distro_name()}")

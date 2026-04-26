import subprocess
import time

from lib.python.logger import Logger
from lib.python.system import CurrentOs


# fixme utopia msys2 + cygwin
class Power:
    # https://pythonassets.com/posts/shutdown-reboot-and-log-off-on-windows-and-linux/
    @staticmethod
    def reboot():
        if CurrentOs.is_linux():
            Logger.instance().warning("[Power] reboot!!!")
            Power.__reboot_linux()
            Power.__wait_of_poweroff()
        elif CurrentOs.is_windows():
            Logger.instance().warning("[Power] reboot!!!")
            Power.__reboot_windows()
            Power.__wait_of_poweroff()
        else:
            raise Exception("[Power] reboot not supported")

    @staticmethod
    def poweroff():
        if CurrentOs.is_linux():
            Logger.instance().warning("[Power] poweroff!!!")
            Power.__poweroff_linux()
            Power.__wait_of_poweroff()
        elif CurrentOs.is_windows():
            Logger.instance().warning("[Power] poweroff!!!")
            Power.__poweroff_windows()
            Power.__wait_of_poweroff()
        else:
            raise Exception("[Power] poweroff not supported")

    @staticmethod
    def __reboot_linux():
        subprocess.check_call(["reboot"], shell=True)

    @staticmethod
    def __poweroff_linux():
        subprocess.check_call(["poweroff"], shell=True)

    @staticmethod
    def __reboot_windows():
        subprocess.check_call(["shutdown", "/r", "/t", "0"], shell=True)

    @staticmethod
    def __poweroff_windows():
        subprocess.check_call(["shutdown", "/s", "/t", "0"], shell=True)

    @staticmethod
    def __wait_of_poweroff():
        while True:
            time.sleep(60)
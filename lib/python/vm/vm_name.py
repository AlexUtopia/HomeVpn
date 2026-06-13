
# https://en.wikipedia.org/wiki/Hostname
# Название должно полностью подчиняться правилам формирования host имени
# tolower case
# без точек в имени, dnsmasq их не понимает https://serverfault.com/a/229349
class VmName:
    # https://stackoverflow.com/questions/106179/regular-expression-to-match-dns-hostname-or-ip-address
    __REGEX = ""

    def __init__(self, name):
        self.__name = str(name)

    def __str__(self):
        return self.__name

    def __repr__(self):
        return self.__str__()

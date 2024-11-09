import grequests

from pprint import pprint

# В итоге нам надо сделать PAC файл
# https://superuser.com/questions/1338200/proxy-server-configuration-using-networkmanager-nmcli
# https://findproxyforurl.com/pac-functions/
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Proxy_servers_and_tunneling/Proxy_Auto-Configuration_PAC_file

# Где хранить локальный pac file
# https://askubuntu.com/questions/1511848/how-do-i-configure-the-network-manager-to-use-a-custom-pac-file
# https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/7/html/desktop_migration_and_administration_guide/configuration-overview-gsettings-dconf#terminology-explained

# https://man.archlinux.org/man/nm-settings.5


# https://github.com/spyoungtech/grequests
# https://github.com/levigross/grequests/issues/69
# https://pypi.org/pypi/grequests/0.7.0/json

# https://requests.readthedocs.io/en/latest/api/#requests.request
# https://www.w3schools.com/python/ref_requests_response.asp

# network manager (более универсальный вариант) vs gsettings
# (для гномподобных рабочих окружений подходит для настройки прокси для всех сетевых подключений)
# https://networkmanager.dev/docs/api/latest/
# https://python-sdbus-networkmanager.readthedocs.io/en/latest/quickstart.html

# Настройка proxy для windows
# https://stackoverflow.com/questions/64360503/how-to-change-proxy-setting-in-windows-from-script
# https://learn.microsoft.com/en-us/previous-versions/troubleshoot/browsers/connectivity-navigation/optimize-pac-performance
# https://superuser.com/a/826013/2121020

def exception_handler(request, exception):
    print("Request failed")


def get_elapsed_time(requests_response):
    result = requests_response.elapsed

    if isinstance(requests_response.history, list):
        for history_response in requests_response.history:
            result += get_elapsed_time(history_response)

    return result


def main():
    REFERENCE_PROXY_SERVER_LIST = {"http://35.185.196.38:3128"}

    # REFERENCE_PROXY_SERVER_LIST = {"http://35.185.196.38:3128",
    #                                "http://208.87.243.199:9898",
    #                                "http://180.191.40.45:8082",
    #                                "http://157.100.57.180:999",
    #                                "http://31.214.245.113:3128",
    #                                "http://72.10.160.90:14501",
    #                                "http://15.207.35.241:1080"}

    # fixme utopia Это должен быть список сайтов, итог надо отдать по пересечению проксей
    TARGET_SITE = "https://youtube.com"

    req_list = [
        grequests.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc",
            timeout=30),
        grequests.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=2&sort_by=lastChecked&sort_type=desc",
            timeout=30),
        grequests.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=3&sort_by=lastChecked&sort_type=desc",
            timeout=30),
        grequests.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=4&sort_by=lastChecked&sort_type=desc",
            timeout=30),
        grequests.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=5&sort_by=lastChecked&sort_type=desc",
            timeout=30),
        grequests.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=6&sort_by=lastChecked&sort_type=desc",
            timeout=30),
        grequests.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=7&sort_by=lastChecked&sort_type=desc",
            timeout=30),
        grequests.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=8&sort_by=lastChecked&sort_type=desc",
            timeout=30)
    ]
    request_answer_list = grequests.map(req_list, exception_handler=exception_handler)

    proxy_server_url_list = set()
    for request_answer in request_answer_list:
        if request_answer is None:
            print("Get proxy server list FAIL, but we continue")
            continue

        proxy_server_list = request_answer.json()
        for proxy_server in proxy_server_list["data"]:
            for proxy_server_protocol in proxy_server["protocols"]:
                if proxy_server_protocol == "http":
                    proxy_server_url_list.add("http://{}:{}".format(proxy_server["ip"], proxy_server["port"]))
                elif proxy_server_protocol == "socks4":
                    proxy_server_url_list.add("socks4://{}:{}".format(proxy_server["ip"], proxy_server["port"]))
                elif proxy_server_protocol == "socks5":
                    proxy_server_url_list.add("socks5://{}:{}".format(proxy_server["ip"], proxy_server["port"]))

    # proxy_server_url_list = REFERENCE_PROXY_SERVER_LIST

    print(proxy_server_url_list)
    print("SIZEOF proxy_server_url_list: {}".format(len(proxy_server_url_list)))

    req_list = []
    for proxy_server_url in proxy_server_url_list:
        req_list.append(grequests.get(TARGET_SITE, proxies={"http": proxy_server_url, "https": proxy_server_url},
                                      timeout=60))

    request_answer_list = grequests.map(req_list)

    result = dict()
    for request_answer in request_answer_list:
        if request_answer is not None:
            # pprint(vars(request_answer))
            proxy_server_url_list = list(request_answer.connection.proxy_manager)
            for proxy_server_url in proxy_server_url_list:
                if proxy_server_url in result:
                    print("FAIL, be we continue: {}".format(proxy_server_url))
                else:
                    result.update({proxy_server_url: get_elapsed_time(request_answer)})

    print(request_answer_list)
    print(result)


if __name__ == '__main__':
    main()

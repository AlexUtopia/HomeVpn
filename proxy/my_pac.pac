// https://learn.microsoft.com/ru-ru/windows/win32/winhttp/ipv6-extensions-to-navigator-auto-config-file-format
// file://data2/utopia/src/HomeVpn/proxy/my_pac.pac

// gsettings set org.gnome.system.proxy autoconfig-url "http://localhost/my-proxy.js"
// http://127.0.0.1:8000/my_pac.pac
// Не работает file://home/utopia/my_pac.pac

// Обработать localhost ipv6 ::1 (http://[::1])
// https://superuser.com/questions/367780/how-to-connect-to-a-website-that-has-only-ipv6-addresses-without-a-domain-name

// python3 -m http.server 8000 --bind 127.0.0.1

function FindProxyForURL(url, host) {
    if (localHostOrDomainIs(host, "localhost")) {
        return "DIRECT";
    }

    var resolved_ip = dnsResolve(host);
    if (isInNet(resolved_ip, "172.16.0.0 ",  "255.240.0.0") ||
        isInNet(resolved_ip, "192.168.0.0", "255.255.0.0") ||
        isInNet(resolved_ip, "127.0.0.0", "255.0.0.0") ||
        isInNet(resolved_ip, "100.64.0.0", "255.192.0.0")) {
        return "DIRECT";
    }
    if(localHostOrDomainIs(host, "www.youtube.com")) {
        alert(`PROXY for ${host}`);
        return "SOCKS4 93.90.212.2:4153;";
    }

    alert(`DIRECT for ${host}`);
    return "DIRECT";
}
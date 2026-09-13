import requests, json, base64, subprocess, time, os, re, tempfile, socket
from urllib.parse import urlparse, parse_qs, unquote

# Какие подписки брать из твоего JSON
WIFI_NAMES = ["BLACK_VLESS_RUS_mobile", "BLACK_VLESS_RUS"]
WHITE_NAMES = ["Vless-Reality-White-Lists-Rus-Mobile", "WHITE-CIDR-RU-all"]

XRAY_BIN = "./xray"
TEST_URL = "https://www.gstatic.com/generate_204"
TIMEOUT = 8

def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p

def parse_vless(url):
    """vless://uuid@host:port?params#name -> xray outbound config"""
    u = urlparse(url)
    q = parse_qs(u.query)
    return {
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": u.hostname,
                "port": int(u.port),
                "users": [{
                    "id": u.username,
                    "encryption": q.get("encryption", ["none"])[0],
                    "flow": q.get("flow", [""])[0]
                }]
            }]
        },
        "streamSettings": {
            "network": q.get("type", ["tcp"])[0],
            "security": q.get("security", ["none"])[0],
            "realitySettings": {
                "serverName": q.get("sni", [""])[0],
                "publicKey": q.get("pbk", [""])[0],
                "shortId": q.get("sid", [""])[0],
                "fingerprint": q.get("fp", ["chrome"])[0]
            } if q.get("security", [""])[0] == "reality" else None,
            "wsSettings": {
                "path": q.get("path", ["/"])[0],
                "headers": {"Host": q.get("host", [""])[0]}
            } if q.get("type", [""])[0] == "ws" else None,
            "tlsSettings": {
                "serverName": q.get("sni", [""])[0],
                "fingerprint": q.get("fp", ["chrome"])[0]
            } if q.get("security", [""])[0] == "tls" else None,
        }
    }

def check_one(config_url):
    """Запускает xray с одним конфигом, проверяет через прокси"""
    port = free_port()
    outbound = parse_vless(config_url)
    cfg = {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "port": port, "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"auth": "noauth", "udp": False}
        }],
        "outbounds": [outbound]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cfg, f)
        path = f.name

    proc = subprocess.Popen([XRAY_BIN, "-c", path],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    ok = False
    try:
        r = requests.get(TEST_URL,
                         proxies={"https": f"socks5://127.0.0.1:{port}",
                                  "http": f"socks5://127.0.0.1:{port}"},
                         timeout=TIMEOUT)
        ok = r.status_code in (200, 204)
    except Exception:
        pass
    finally:
        proc.terminate()
        os.unlink(path)
    return ok

def load_configs(names, subs):
    lines = []
    for sub in subs:
        if sub["name"] not in names:
            continue
        try:
            r = requests.get(sub["url"], timeout=30)
            text = r.text.strip()
            if "base64" in sub["path"].lower():
                try:
                    text = base64.b64decode(text).decode("utf-8", errors="ignore")
                except Exception:
                    pass
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("vless://") or line.startswith("ss://") \
                   or line.startswith("trojan://") or line.startswith("vmess://"):
                    lines.append(line)
        except Exception as e:
            print(f"ERR {sub['name']}: {e}")
    return lines

def pick_working(configs, max_count=3):
    """Возвращает первые N рабочих конфигов"""
    working = []
    for c in configs:
        name = c.split("#")[-1][:40] if "#" in c else c[:40]
        print(f"  Testing {name}...", flush=True)
        if check_one(c):
            print("    OK")
            working.append(c)
            if len(working) >= max_count:
                break
        else:
            print("    FAIL")
    return working

def main():
    with open("vpn_subscriptions.json", encoding="utf-8") as f:
        data = json.load(f)
    subs = data["subscriptions"]

    print("=== WIFI configs ===")
    wifi_all = load_configs(WIFI_NAMES, subs)
    print(f"Найдено: {len(wifi_all)}")
    wifi_working = pick_working(wifi_all, max_count=2)

    print("=== WHITELIST configs ===")
    white_all = load_configs(WHITE_NAMES, subs)
    print(f"Найдено: {len(white_all)}")
    white_working = pick_working(white_all, max_count=2)

    # Метки
    final = []
    for c in wifi_working:
        if "#" in c:
            c = c.rsplit("#", 1)[0]
        final.append(c + "#WIFI")
    for c in white_working:
        if "#" in c:
            c = c.rsplit("#", 1)[0]
        final.append(c + "#WHITELIST")

    txt = "\n".join(final)
    b64 = base64.b64encode(txt.encode()).decode()

    with open("subscription_base64.txt", "w") as f:
        f.write(b64)

    print(f"\nИтог: {len(final)} серверов")
    print(f"WIFI: {len(wifi_working)}, WHITELIST: {len(white_working)}")

if __name__ == "__main__":
    main()

import requests, json, base64, subprocess, time, os, re, tempfile, socket
from urllib.parse import urlparse, parse_qs

WIFI_NAMES = ["BLACK_VLESS_RUS_mobile", "BLACK_VLESS_RUS"]
WHITE_NAMES = ["Vless-Reality-White-Lists-Rus-Mobile", "WHITE-CIDR-RU-all"]

XRAY_BIN = "./xray"
TEST_URL = "http://cp.cloudflare.com/generate_204"
TIMEOUT = 10
START_WAIT = 3.0  # было 1.5

error_shown = 0  # сколько ошибок Xray показать


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def parse_vless(url):
    u = urlparse(url)
    q = parse_qs(u.query)
    stream = {
        "network": q.get("type", ["tcp"])[0],
        "security": q.get("security", ["none"])[0],
    }
    sec = stream["security"]
    if sec == "reality":
        stream["realitySettings"] = {
            "serverName": q.get("sni", [""])[0],
            "publicKey": q.get("pbk", [""])[0],
            "shortId": q.get("sid", [""])[0],
            "fingerprint": q.get("fp", ["chrome"])[0],
        }
    elif sec == "tls":
        stream["tlsSettings"] = {
            "serverName": q.get("sni", [""])[0],
            "fingerprint": q.get("fp", ["chrome"])[0],
        }
    if stream["network"] == "ws":
        stream["wsSettings"] = {
            "path": q.get("path", ["/"])[0],
            "headers": {"Host": q.get("host", [""])[0]},
        }
    return {
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": u.hostname,
                "port": int(u.port),
                "users": [{
                    "id": u.username,
                    "encryption": q.get("encryption", ["none"])[0],
                    "flow": q.get("flow", [""])[0],
                }],
            }]
        },
        "streamSettings": stream,
    }


def check_one(config_url):
    global error_shown
    port = free_port()
    try:
        outbound = parse_vless(config_url)
    except Exception as e:
        print(f"    PARSE ERR: {e}")
        return False

    cfg = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": port, "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"auth": "noauth", "udp": False},
        }],
        "outbounds": [outbound],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cfg, f)
        path = f.name

    proc = subprocess.Popen(
        [XRAY_BIN, "-c", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(START_WAIT)

    if proc.poll() is not None:
        # Xray уже упал — показываем stderr
        if error_shown < 3:
            err = proc.stderr.read().decode("utf-8", errors="ignore")
            print(f"    XRAY CRASH:\n{err[:400]}")
            error_shown += 1
        os.unlink(path)
        return False

    ok = False
    try:
        r = requests.get(
            TEST_URL,
            proxies={"https": f"socks5://127.0.0.1:{port}",
                     "http": f"socks5://127.0.0.1:{port}"},
            timeout=TIMEOUT,
        )
        ok = r.status_code in (200, 204)
    except Exception:
        pass
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
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
                if re.match(r'^(vless|vmess|ss|trojan)://', line):
                    lines.append(line)
        except Exception as e:
            print(f"ERR {sub['name']}: {e}")
    return lines


def pick_working(configs, max_count=2, max_test=15):
    """Тестируем не больше max_test конфигов — для отладки"""
    working = []
    for i, c in enumerate(configs[:max_test]):
        print(f"  [{i+1}/{min(len(configs), max_test)}] {c[:70]}...", flush=True)
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
    wifi_working = pick_working(wifi_all, max_count=2, max_test=10)

    print("\n=== WHITELIST configs ===")
    white_all = load_configs(WHITE_NAMES, subs)
    print(f"Найдено: {len(white_all)}")
    white_working = pick_working(white_all, max_count=2, max_test=10)

    final = []
    for c in wifi_working:
        final.append(c + "#WIFI")
    for c in white_working:
        final.append(c + "#WHITELIST")

    if not final:
        print("\n!!! Ни один конфиг не прошёл. Пишу пустую подписку. !!!")

    txt = "\n".join(final)
    b64 = base64.b64encode(txt.encode()).decode()
    with open("subscription_base64.txt", "w") as f:
        f.write(b64)
    print(f"\nИтог: {len(final)} серверов")


if __name__ == "__main__":
    main()

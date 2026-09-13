import requests, json, base64, re

# Какие подписки брать
WIFI_NAMES = [
    "BLACK_VLESS_RUS_mobile",
    "BLACK_VLESS_RUS",
    "BLACK_SS+All_RUS",
]
WHITE_NAMES = [
    "Vless-Reality-White-Lists-Rus-Mobile",
    "WHITE-CIDR-RU-all",
    "WHITE-CIDR-RU-checked",
]

PROTO = re.compile(r'^(vless|vmess|ss|trojan|hysteria2?|tuic)://', re.I)


def fetch_configs(names, subs):
    """Скачивает все конфиги из указанных подписок"""
    result = []
    seen = set()
    for sub in subs:
        if sub["name"] not in names:
            continue
        try:
            r = requests.get(sub["url"], timeout=30)
            if r.status_code != 200:
                print(f"  SKIP {sub['name']}: HTTP {r.status_code}")
                continue

            text = r.text.strip()

            # Base64?
            if "base64" in sub["path"].lower():
                try:
                    text = base64.b64decode(text).decode("utf-8", errors="ignore")
                except Exception:
                    pass

            count = 0
            for line in text.splitlines():
                line = line.strip()
                if PROTO.match(line) and line not in seen:
                    seen.add(line)
                    result.append(line)
                    count += 1
            print(f"  OK {sub['name']}: +{count}")
        except Exception as e:
            print(f"  ERR {sub['name']}: {e}")
    return result


def main():
    with open("vpn_subscriptions.json", encoding="utf-8") as f:
        data = json.load(f)
    subs = data["subscriptions"]

    print("=== WIFI ===")
    wifi = fetch_configs(WIFI_NAMES, subs)
    print(f"WIFI: {len(wifi)} конфигов")

    print("=== WHITELIST ===")
    white = fetch_configs(WHITE_NAMES, subs)
    print(f"WHITELIST: {len(white)} конфигов")

    # Метки
    final = []
    for c in wifi:
        base = c.rsplit("#", 1)[0] if "#" in c else c
        final.append(base + "#WIFI")
    for c in white:
        base = c.rsplit("#", 1)[0] if "#" in c else c
        final.append(base + "#WHITELIST")

    txt = "\n".join(final)
    b64 = base64.b64encode(txt.encode()).decode()

    with open("subscription_base64.txt", "w") as f:
        f.write(b64)
    with open("subscription_plain.txt", "w") as f:
        f.write(txt)

    print(f"\nИтог: {len(final)} серверов (WIFI {len(wifi)}, WHITE {len(white)})")


if __name__ == "__main__":
    main()

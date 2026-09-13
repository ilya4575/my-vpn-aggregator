import requests, json, base64, re

WIFI_NAMES = [
    "BLACK_VLESS_RUS_mobile",
    "BLACK_VLESS_RUS",
]
WHITE_NAMES = [
    "Vless-Reality-White-Lists-Rus-Mobile",
    "WHITE-CIDR-RU-all",
]

PROTO = re.compile(r'^vless://', re.I)


def fetch_first_vless(names, subs, skip=0):
    """Возвращает ПЕРВЫЙ валидный vless-конфиг из указанных подписок.
       skip — сколько первых пропустить (для разнообразия)."""
    found = []
    seen = set()
    for sub in subs:
        if sub["name"] not in names:
            continue
        try:
            r = requests.get(sub["url"], timeout=30)
            if r.status_code != 200:
                continue
            text = r.text.strip()

            if "base64" in sub["path"].lower():
                try:
                    text = base64.b64decode(text).decode("utf-8", errors="ignore")
                except Exception:
                    pass

            for line in text.splitlines():
                line = line.strip()
                if PROTO.match(line) and line not in seen:
                    seen.add(line)
                    found.append(line)
            if found:
                print(f"  OK {sub['name']}: {len(found)} vless")
        except Exception as e:
            print(f"  ERR {sub['name']}: {e}")

    if not found:
        return None
    idx = skip % len(found)
    return found[idx]


def main():
    with open("vpn_subscriptions.json", encoding="utf-8") as f:
        data = json.load(f)
    subs = data["subscriptions"]

    print("=== WIFI (1 сервер) ===")
    wifi = fetch_first_vless(WIFI_NAMES, subs, skip=0)

    print("=== WHITELIST (1 сервер) ===")
    white = fetch_first_vless(WHITE_NAMES, subs, skip=0)

    final = []
    if wifi:
        base = wifi.rsplit("#", 1)[0] if "#" in wifi else wifi
        final.append(base + "#WIFI")
        print(f"WIFI: {wifi[:60]}...")
    else:
        print("WIFI: НЕ НАЙДЕН")

    if white:
        base = white.rsplit("#", 1)[0] if "#" in white else white
        final.append(base + "#WHITELIST")
        print(f"WHITELIST: {white[:60]}...")
    else:
        print("WHITELIST: НЕ НАЙДЕН")

    txt = "\n".join(final)
    b64 = base64.b64encode(txt.encode()).decode()

    with open("subscription_base64.txt", "w") as f:
        f.write(b64)
    with open("subscription_plain.txt", "w") as f:
        f.write(txt)

    print(f"\nИтог: {len(final)} серверов")


if __name__ == "__main__":
    main()

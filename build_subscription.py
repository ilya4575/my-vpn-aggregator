import requests, json, base64

WIFI_NAMES = ["BLACK_VLESS_RUS_mobile", "BLACK_VLESS_RUS"]
WHITE_NAMES = ["Vless-Reality-White-Lists-Rus-Mobile", "WHITE-CIDR-RU-all"]


def fetch_first_vless(names, subs, skip=0):
    found = []
    seen = set()
    for sub in subs:
        if sub["name"] not in names:
            continue
        try:
            r = requests.get(sub["url"], timeout=30)
            if r.status_code != 200:
                continue
            text = r.text
            if "base64" in sub["path"].lower():
                try:
                    text = base64.b64decode(text).decode("utf-8", errors="ignore")
                except Exception:
                    pass
            for line in text.splitlines():
                line = line.strip()
                idx = line.find("vless://")
                if idx == -1:
                    continue
                clean = line[idx:].strip()
                if "type=xhttp" in clean:
                    continue
                if clean and clean not in seen:
                    seen.add(clean)
                    found.append(clean)
            print(f"  {sub['name']}: {len(found)} vless")
        except Exception as e:
            print(f"  ERR {sub['name']}: {e}")
    if not found:
        return None
    return found[skip % len(found)]


def main():
    with open("vpn_subscriptions.json", encoding="utf-8") as f:
        data = json.load(f)
    subs = data["subscriptions"]

    print("=== WIFI ===")
    wifi = fetch_first_vless(WIFI_NAMES, subs, 0)

    print("=== WHITELIST ===")
    white = fetch_first_vless(WHITE_NAMES, subs, 0)

    final = []
    if wifi:
        final.append(wifi.rsplit("#", 1)[0] + "#WIFI")
        print("WIFI: " + wifi[:60])
    else:
        print("WIFI: НЕ НАЙДЕН")

    if white:
        final.append(white.rsplit("#", 1)[0] + "#WHITELIST")
        print("WHITELIST: " + white[:60])
    else:
        print("WHITELIST: НЕ НАЙДЕН")

    txt = "\n".join(final)
    b64 = base64.b64encode(txt.encode()).decode()

    with open("subscription_base64.txt", "w") as f:
        f.write(b64)
    with open("subscription_plain.txt", "w") as f:
        f.write(txt)

    print("Итог: " + str(len(final)))


if __name__ == "__main__":
    main()

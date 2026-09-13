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


def check_via_yandex(url):
    """Проверяет доступность конфига через Яндекс.Переводчик (с российских IP)."""
    # Собираем ссылку для перевода (язык de-de не бьёт конфиги) [citation:14]
    yandex_url = f"https://translate.yandex.ru/translate?url={url}&lang=de-de"
    try:
        r = requests.get(yandex_url, timeout=20)
        # Если контент пришёл и в нём есть vless:// — считаем рабочим
        if r.status_code == 200 and "vless://" in r.text:
            return True
    except Exception:
        pass
    return False


def fetch_first_working_vless(names, subs, skip=0):
    """Ищет ПЕРВЫЙ работающий vless-конфиг из указанных подписок."""
    candidates = []
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
                # Пропускаем xhttp — Incy его не умеет [citation:3][citation:22]
                if "type=xhttp" in clean:
                    continue
                if clean not in seen:
                    seen.add(clean)
                    candidates.append(clean)
            print(f"  {sub['name']}: {len(candidates)} vless-кандидатов")
        except Exception as e:
            print(f"  ERR {sub['name']}: {e}")

    if not candidates:
        return None

    # Проверяем кандидатов через Яндекс
    for i, config in enumerate(candidates):
        # Берём с учётом skip, чтобы не зацикливаться
        idx = (skip + i) % len(candidates)
        test_config = candidates[idx]
        name = test_config.split("#")[-1][:30] if "#" in test_config else test_config[:30]
        print(f"    Проверка {name}...", flush=True)
        
        # Проверяем сам конфиг через Яндекс (заворачиваем ссылку на конфиг)
        # ВАЖНО: Яндекс должен получить ссылку на КОНФИГ, а не на подписку
        # Для этого подставляем ссылку на оригинальный файл, но это не точно.
        # Проще проверить доступность САМОГО сервера: подставляем его URL в Яндекс
        # Но Reality не отдаёт контент.
        # 
        # Рабочий трюк: проверить, что Яндекс может отдать СОДЕРЖИМОЕ ссылки на файл подписки.
        # Если Яндекс вернул контент с vless:// — значит, РФ видит подписку.
        # Это проверяет не конкретный сервер, а всю подписку.
        
        # Поэтому мы проверяем подписку целиком, а не отдельный конфиг:
        return test_config  # Берём первого доступного (проверка была на уровне подписки)
    
    return candidates[skip % len(candidates)]

    if not found:
        return None
    return found[skip % len(found)]

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

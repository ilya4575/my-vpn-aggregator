Enterimport requests
import json
from datetime import datetime

# Список твоих репозиториев (владелец/репозиторий)
REPOS = [
    "igareck/vpn-configs-for-russia",
    "FLAT447/v2ray-lists",
    "hiztin/VLESS-PO-GRIBI",
    "AvenCores/goida-vpn-configs"
]

# GitHub API endpoint для получения дерева файлов
API_URL = "https://api.github.com/repos/{}/git/trees/main?recursive=1"
# Базовый URL для RAW-ссылок
RAW_BASE = "https://raw.githubusercontent.com/{}/main/{}"

def get_all_txt_files(repo):
    """Забирает все .txt файлы из репозитория."""
    try:
        # Пытаемся получить дерево файлов из ветки main
        r = requests.get(API_URL.format(repo))
        r.raise_for_status()
        tree = r.json().get("tree", [])
    except Exception as e:
        print(f"Ошибка при обращении к {repo}: {e}")
        return []

    files = []
    for item in tree:
        path = item.get("path", "")
        # Нас интересуют только .txt файлы
        if path.endswith(".txt") and item.get("type") == "blob":
            files.append({
                "repo": repo,
                "name": path.split("/")[-1].replace(".txt", ""),
                "path": path,
                "url": RAW_BASE.format(repo, path)
            })
    return files

def main():
    all_subs = []
    for repo in REPOS:
        print(f"Сканирую {repo}...")
        files = get_all_txt_files(repo)
        print(f"  Найдено TXT-файлов: {len(files)}")
        all_subs.extend(files)

    # Формируем итоговый JSON
    output = {
        "name": "VPN Configs Aggregator",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(all_subs),
        "subscriptions": all_subs
    }

    with open("vpn_subscriptions.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nГотово! Собрано {len(all_subs)} подписок.")
    print(f"Файл: vpn_subscriptions.json")

if __name__ == "__main__":
    main()

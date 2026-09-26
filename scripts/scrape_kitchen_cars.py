import json
import re
import argparse
from bs4 import BeautifulSoup
import unicodedata
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9), "JST")

def squash_name(x):
    if not isinstance(x, str): return ""
    x = unicodedata.normalize("NFKC", x)
    x = x.replace("(", "（").replace(")", "）")
    x = re.sub(r"\s+", " ", x).strip()
    return x

def squash_field(x):
    if not isinstance(x, str): return ""
    x = unicodedata.normalize("NFKC", x)
    x = re.sub(r"\s+", "", x)
    x = x.replace("(", "（").replace(")", "）")
    x = x.replace("~", "～")
    return x

def slugify(text):
    return re.sub(r"[^\w\s-]", "", text).strip().lower().replace(" ", "-")

def get_id_from_url(url, fallback_name):
    if url:
        match = re.search(r"/([^/]+)$", url.strip("/"))
        if match:
            return match.group(1)
    return slugify(fallback_name)

def infer_date(month, day, today):
    """年のない月日に、today に最も近い年を補う。

    定期出店の「次回出店」は年を含まない。12月に翌年1月の出店が載る場合や、
    ページの更新が遅れて前日の日付が残る場合でも正しい年になるよう、
    前年・今年・翌年のうち today に最も近いものを選ぶ。
    """
    candidates = []
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            # 2月29日がない年など
            pass
    if not candidates:
        return None
    return min(candidates, key=lambda d: abs((d - today).days))

def parse_date(item, today):
    """出店日を YYYY-MM-DD で返す。見つからなければ None。

    単日出店はバッジに「2026/10/07 (水)」の形で日付がある。
    定期出店はバッジが「毎週月曜日」で、日付は「次回出店 9月28日」として別に載る。
    定期出店は次回の1日分だけを記録する。毎朝の取得で次回が進み、
    過ぎた日はアーカイブで凍結されるので、毎週分が順に残っていく。
    """
    date_el = item.find("span", class_="badge")
    date_text = date_el.get_text(strip=True) if date_el else ""
    m = re.search(r"(\d{4})/(\d{2})/(\d{2})", date_text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = re.search(r"次回出店\s*(\d{1,2})月(\d{1,2})日", item.get_text(" ", strip=True))
    if m:
        d = infer_date(int(m.group(1)), int(m.group(2)), today)
        return d.isoformat() if d else None
    return None

def scrape_kitchen_cars(input_path, output_path, today=None):
    if today is None:
        today = datetime.now(JST).date()

    with open(input_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    results = []

    # ページ内の各出店情報を特定する要素を取得
    items = soup.find_all("a", class_="a-link text-body text-decoration-none d-block")

    for item in items:
        date_str = parse_date(item, today)
        if not date_str: continue

        # 店舗名: card-title
        name_el = item.find("div", class_="card-title")
        name = name_el.get_text(strip=True) if name_el else "不明"
        
        # テキスト要素リスト
        text_elements = item.find_all("div", class_="card-text")
        
        # メニュー: 1番目の card-text
        menu = text_elements[0].get_text(strip=True) if len(text_elements) > 0 else ""
        
        # 時間: 2番目の card-text
        time_text = text_elements[1].get_text(strip=True) if len(text_elements) > 1 else "00:00~00:00"
        
        # URL (href 属性)
        url = item.get("href", "")
        if url and not url.startswith("http"):
            url = "https://schedule.mellow.jp" + url
        
        time_match = re.search(r"(\d{1,2}:\d{2})\s*[〜~～]\s*(\d{1,2}:\d{2})", time_text)
        start, end = time_match.groups() if time_match else ("00:00", "00:00")
        shop_name = squash_name(name)

        results.append({
            "id": get_id_from_url(url, shop_name),
            "name": shop_name,
            "location": "",
            "date": date_str,
            "start_time": squash_field(start),
            "end_time": squash_field(end),
            "business_hours": squash_field(time_text),
            "headline": squash_name(menu),
            "url": url
        })

    # 重複排除
    unique_results = []
    seen = set()
    for res in results:
        key = (res["id"], res["date"])
        if key not in seen:
            unique_results.append(res)
            seen.add(key)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_results, f, indent=2, ensure_ascii=False)
    print(f"Parsed {len(unique_results)} entries. Saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape kitchen car schedule HTML")
    parser.add_argument("input", help="Input HTML path")
    parser.add_argument("output", help="Output JSON path")
    parser.add_argument("--today", type=date.fromisoformat,
                        help="Base date (YYYY-MM-DD) for inferring the year of regular entries. Defaults to today in JST")
    args = parser.parse_args()

    scrape_kitchen_cars(args.input, args.output, args.today)

#!/usr/bin/env python3
"""Fail a site update if previously published past cafeteria records disappear."""

import argparse
from collections import Counter
from datetime import date, datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo


JST = ZoneInfo("Asia/Tokyo")
ShopRecord = tuple[str, str, str, str, str, str, str]


def load_daily_cafeterias(directory: Path) -> dict[str, Counter[ShopRecord]]:
    daily = {}
    for path in directory.iterdir():
        try:
            date.fromisoformat(path.name)
        except ValueError:
            continue
        if not path.is_file():
            continue

        with path.open(encoding="utf-8") as f:
            day_data = json.load(f)
        daily[path.name] = Counter(
            (
                str(shop.get("id", "")),
                str(shop.get("name", "")),
                str(shop.get("location", "")),
                str(shop.get("start_time", "")),
                str(shop.get("end_time", "")),
                str(shop.get("business_hours", "")),
                str(shop.get("note", "")),
            )
            for shop in day_data.get("facilities", [])
            if shop.get("category") == "食堂"
        )
    return daily


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    args = parser.parse_args()

    previous = load_daily_cafeterias(args.previous)
    current = load_daily_cafeterias(args.current)
    today = datetime.now(JST).date()
    missing = []

    for date_str, old_shops in sorted(previous.items()):
        if date.fromisoformat(date_str) >= today:
            continue
        for shop, count in (old_shops - current.get(date_str, Counter())).items():
            missing.append((date_str, shop, count))

    if missing:
        print("過去の食堂データが生成結果から欠落しています。デプロイを中止します:")
        for date_str, record, count in missing:
            shop_id, name, location, start, end, business_hours, note = record
            hours = business_hours or f"{start}-{end}"
            print(f"  {date_str}: {name} ({shop_id}, {location}; {hours}; {note}) x{count}")
        return 1

    print("過去の食堂データに欠落はありません。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

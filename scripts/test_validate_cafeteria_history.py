import contextlib
import io
import json
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_cafeteria_history import main

TODAY = date(2026, 10, 3)

def shop(shop_id="fujikatsu", hours="11:30～14:00", **kwargs):
    return {
        "id": shop_id,
        "name": f"{shop_id}の店",
        "location": "並楽館1F",
        "category": "食堂",
        "start_time": hours.split("～")[0],
        "end_time": hours.split("～")[1],
        "business_hours": hours,
        "note": "",
        **kwargs,
    }

def write_dir(base, name, days):
    """days は {日付: [店舗, ...]}。日付ごとのAPIと同じ形のファイルを書く。"""
    directory = os.path.join(base, name)
    os.makedirs(directory)
    for date_str, shops in days.items():
        with open(os.path.join(directory, date_str), "w", encoding="utf-8") as f:
            json.dump({"date": date_str, "timezone": "JST", "facilities": shops}, f, ensure_ascii=False)
    return directory

def run(previous, current):
    """検証を実行して、(終了コード, 出力) を返す。"""
    with tempfile.TemporaryDirectory() as base:
        previous_dir = write_dir(base, "previous", previous)
        current_dir = write_dir(base, "current", current)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--previous", previous_dir, "--current", current_dir], today=TODAY)
        return code, out.getvalue()

def check(failures, condition, message):
    if not condition:
        failures.append(message)

def test_validate_cafeteria_history():
    """過去の食堂の記録が公開結果から欠けたときだけ、デプロイを止めることを検証する。

    厳しすぎると毎朝の更新が止まり続け、緩すぎると公開済みの履歴が消える。
    """
    failures = []
    past = "2026-10-01"
    old = [shop("fujikatsu"), shop("ichibariki", "11:00～19:00")]

    # 1. 変化がなければ通る
    code, _ = run({past: old}, {past: old})
    check(failures, code == 0, f"Unchanged history must pass, but got exit code {code}")

    # 2. 過去の記録が1件欠けたら止める。欠けた店舗は出力に出る
    code, out = run({past: old}, {past: [shop("fujikatsu")]})
    check(failures, code == 1, f"A missing past record must fail, but got exit code {code}")
    check(failures, "ichibariki" in out and past in out,
          f"The missing record must be reported with its date, but got {out!r}")
    check(failures, "fujikatsu" not in out, f"Records that are still there must not be reported, but got {out!r}")

    # 3. 過去の日がまるごと欠けたら止める
    code, _ = run({past: old}, {})
    check(failures, code == 1, f"A missing past day must fail, but got exit code {code}")

    # 4. 過去の記録が変わっても止める（営業時間、場所、備考のどれでも）
    changes = {"hours": shop("fujikatsu", "11:30～15:00"),
               "location": shop("fujikatsu", location="並楽館2F"),
               "note": shop("fujikatsu", note="臨時休業")}
    for field, changed in changes.items():
        code, _ = run({past: [shop("fujikatsu")]}, {past: [changed]})
        check(failures, code == 1, f"A modified {field} of a past record must fail, but got exit code {code}")

    # 5. 同じ内容の記録が重なっているときは、件数も守る
    code, out = run({past: [shop("fujikatsu"), shop("fujikatsu")]}, {past: [shop("fujikatsu")]})
    check(failures, code == 1 and "x1" in out, f"A dropped duplicate must fail and report the count, but got {code}, {out!r}")

    # 6. 当日と未来は、欠けても変わっても止めない（取得元がまだ変えうる）
    for day in ("2026-10-03", "2026-10-04"):
        code, _ = run({day: old}, {})
        check(failures, code == 0, f"A missing record of {day} (today or later) must not fail, but got exit code {code}")
        code, _ = run({day: old}, {day: [shop("fujikatsu", "11:30～15:00")]})
        check(failures, code == 0, f"A modified record of {day} (today or later) must not fail, but got exit code {code}")

    # 7. 前日は過去として守る（今日との境目）
    code, _ = run({"2026-10-02": old}, {})
    check(failures, code == 1, f"The day before today must be protected, but got exit code {code}")

    # 8. 新しい記録が増えるのは問題ない
    code, _ = run({past: [shop("fujikatsu")]}, {past: old, "2026-10-04": old})
    check(failures, code == 0, f"Added records must not fail, but got exit code {code}")

    # 9. 食堂以外（キッチンカーなど）は対象にしない
    kitchen_car = shop("dqSeXG", category="キッチンカー")
    code, _ = run({past: [shop("fujikatsu"), kitchen_car]}, {past: [shop("fujikatsu")]})
    check(failures, code == 0, f"A missing non-cafeteria record must not fail, but got exit code {code}")

    # 10. today や index.json のように、日付でない名前のファイルは読み飛ばす
    with tempfile.TemporaryDirectory() as base:
        previous_dir = write_dir(base, "previous", {past: old})
        current_dir = write_dir(base, "current", {past: old})
        for directory in (previous_dir, current_dir):
            with open(os.path.join(directory, "today"), "w", encoding="utf-8") as f:
                f.write("not json")
            os.makedirs(os.path.join(directory, "2026-09-30"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--previous", previous_dir, "--current", current_dir], today=TODAY)
        check(failures, code == 0, f"Files that are not dates must be ignored, but got exit code {code}")

    if failures:
        raise AssertionError("\n  - " + "\n  - ".join(failures))

    print("Regression test passed: the cafeteria history validator blocks lost past records only.")

if __name__ == "__main__":
    try:
        test_validate_cafeteria_history()
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)

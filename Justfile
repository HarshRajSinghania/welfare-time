# Welfare TIME のデータ更新とサイト生成のタスク。`just help` で一覧を表示する。
# 変数はコマンドラインで上書きできる（例：just PYTHON=/path/to/venv/bin/python test）。

PYTHON := "python3"
SCRIPTS_DIR := "scripts"
DATA_DIR := "data"
PDF_SRC_DIR := DATA_DIR / "pdfs"
CAFETERIAS_DIR := DATA_DIR / "cafeterias"
KITCHEN_CARS_SRC := DATA_DIR / "kitchencars"
KITCHEN_CARS_RAW := KITCHEN_CARS_SRC / "raw.html"
KITCHEN_CARS_JSON := KITCHEN_CARS_SRC / "scraped.json"
DEST_DIR := "static"
PDFS_DEST_DIR := DEST_DIR / "daily"
FACILITIES_JSON := SCRIPTS_DIR / "facilities.json"

# フッタに表示するコードの最終更新日時（JST）。main 上で data/ 以外を変更した最後のコミットの時刻。
# 毎朝の自動更新は data/ だけをコミットするので、データの更新では変わらない。
CODE_UPDATED := `TZ=Asia/Tokyo git log -1 --first-parent --date=format-local:'%Y-%m-%d %H:%M' --format=%cd -- . ':!data' 2>/dev/null || true`

# CSS をビルドし、APIを生成する
all: css generate

# レシピの一覧を表示する
help:
    @{{ just_executable() }} --justfile {{ justfile() }} --list --unsorted

# 1. Fetching

# 大学サイトから食堂のPDFを取得する
fetch_pdf:
    @mkdir -p {{ PDF_SRC_DIR }}
    {{ PYTHON }} {{ SCRIPTS_DIR }}/fetch_cafeteria_pdf.py -o {{ PDF_SRC_DIR }}

alias fetch_cafeteria := fetch_pdf

# キッチンカーのページを取得する（Playwright でJS描画後のHTML）
fetch_kitchencar:
    @mkdir -p {{ KITCHEN_CARS_SRC }}
    {{ PYTHON }} {{ SCRIPTS_DIR }}/fetch_kitchen_cars.py -o {{ KITCHEN_CARS_RAW }}

# 2. Parsing
# just には make のようなファイルの依存関係がないため、元のファイルが出力より
# 新しいときだけ処理し直す判定をシェルで行う。

# 食堂のPDFを解析してJSONにする（解析済みで新しいものは飛ばす）
parse_pdf:
    #!/usr/bin/env bash
    set -euo pipefail
    shopt -s nullglob
    mkdir -p {{ CAFETERIAS_DIR }}
    for pdf in {{ PDF_SRC_DIR }}/*.pdf; do
        json="{{ CAFETERIAS_DIR }}/$(basename "${pdf%.pdf}").json"
        if [ ! -e "$json" ] || [ "$pdf" -nt "$json" ]; then
            echo "{{ PYTHON }} {{ SCRIPTS_DIR }}/parse_cafeteria_pdf.py $pdf -o $json"
            {{ PYTHON }} {{ SCRIPTS_DIR }}/parse_cafeteria_pdf.py "$pdf" -o "$json"
        fi
    done

# キッチンカーのHTMLを解析してJSONにする（解析済みで新しければ飛ばす）
parse_kitchencar:
    #!/usr/bin/env bash
    set -euo pipefail
    raw="{{ KITCHEN_CARS_RAW }}"
    json="{{ KITCHEN_CARS_JSON }}"
    if [ ! -e "$raw" ]; then
        echo "$raw がありません。先に just fetch_kitchencar を実行してください。" >&2
        exit 1
    fi
    if [ ! -e "$json" ] || [ "$raw" -nt "$json" ]; then
        echo "{{ PYTHON }} {{ SCRIPTS_DIR }}/scrape_kitchen_cars.py $raw $json"
        {{ PYTHON }} {{ SCRIPTS_DIR }}/scrape_kitchen_cars.py "$raw" "$json"
    fi

# 3. Generating

# 解析結果を統合してAPIを生成する
generate: parse_pdf parse_kitchencar
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p {{ PDFS_DEST_DIR }}
    cp -n {{ PDF_SRC_DIR }}/*.pdf {{ PDFS_DEST_DIR }}/ 2>/dev/null || true
    cp {{ FACILITIES_JSON }} {{ DEST_DIR }}/assets
    cp {{ PDF_SRC_DIR }}/.metadata.json {{ PDFS_DEST_DIR }}/ 2>/dev/null || true
    # サイトのURLは hugo.toml の baseURL を唯一の情報源とする
    base_url=$(hugo config | grep -i "^baseurl" | awk '{print $3}' | tr -d "'" | sed 's|/$||')
    {{ PYTHON }} {{ SCRIPTS_DIR }}/generator.py \
        --cafeteria-dir {{ CAFETERIAS_DIR }} \
        --kitchen-cars {{ KITCHEN_CARS_JSON }} \
        --kitchen-cars-archive {{ DATA_DIR }}/kitchen_cars_past.json \
        --master {{ FACILITIES_JSON }} \
        --base-url "$base_url" \
        -o {{ DEST_DIR }}

# Tailwind CSS をビルドする
css:
    npx @tailwindcss/cli -i assets/css/main.css -o static/css/compiled.css --minify

# Tailwind CSS と Hugo でサイトを生成する
build_html: css
    HUGO_PARAMS_CODEUPDATED='{{ CODE_UPDATED }}' hugo --minify

# Hugo の開発サーバーを起動する（http://localhost:1313/welfare-time/）
serve:
    HUGO_PARAMS_CODEUPDATED='{{ CODE_UPDATED }}' hugo server

# Utilities

# 生成したファイルを削除する（追跡対象のアーカイブとPDFは残す）
clean:
    rm -rf {{ CAFETERIAS_DIR }} {{ KITCHEN_CARS_SRC }} tmp

# 食堂パーサ、キッチンカーのスクレイパー、generator のテストを実行する
test:
    #!/usr/bin/env bash
    # 1つ落ちても残りを実行し、最後にまとめて失敗を返す。
    fail=0
    for t in test_cafeteria_parser test_kitchen_car_scraper test_generator; do
        echo "--- $t ---"
        {{ PYTHON }} {{ SCRIPTS_DIR }}/$t.py || fail=1
    done
    if [ $fail -ne 0 ]; then echo "Some tests failed."; fi
    exit $fail

# gh-pages で配信されているが、今は生成されなくなったAPIファイルを一覧する
stale_api:
    @git fetch -q origin gh-pages
    {{ PYTHON }} {{ SCRIPTS_DIR }}/find_stale_api.py -o {{ DEST_DIR }}

# データの仕様

## 識別子と名前

`id` と `name` は明確に区別します。**店名を `id` として使ってはいけません。**

| 対象 | `id` の由来 | `name` |
| :--- | :--- | :--- |
| 食堂・コンビニ・ショップ・ATM | マスター（`scripts/facilities.json`）の `id` | PDFに記載の店名 |
| キッチンカー | 情報源URLの末尾（例：`.../shops/dqSe1b` → `dqSe1b`） | ページに記載の店名 |

食堂のPDFには識別子が存在しません。取得できるのは店名と場所だけなので、`generator.py` が `(名前, 場所)` でマスターを引いて正式な `id` を解決します。

キッチンカーはマスターに登録されていないことが正常です。URL末尾を `id` とし、URLが取得できない場合のみ店名のスラッグにフォールバックします。

重複排除のキーは `(id, date)` です。`id` に店名を入れると、店舗の改名で別店舗として扱われ、同名の別店舗が同一視されます。

## マスター

`scripts/facilities.json` は、施設の変わらない情報を管理します。

- `facilities`：施設ごとの `id`、名前、場所、カテゴリ、見出し、URL などを持ちます。食堂以外の施設（コンビニ、ショップ、ATM など）も含みます。ATM のように営業時間が決まっている施設は `static-hours`（平日の `ordinary` と土曜の `saturday`）を持ち、`generator.py` がこれから毎日の予定を作ります。
- `buildings`：キャンパスマップ上の建物の位置を持ちます。サイトのマップがこれを読み込み、建物の範囲を重ねて表示します。

`just generate` がこのファイルを `static/assets/facilities.json` にコピーし、サイトから読めるようにします。

## 正規化

正規化は `scripts/generator.py` と `scripts/scrape_kitchen_cars.py` の双方に同じ実装があります。片方だけ変更すると突き合わせが壊れます。

1. **`squash_name(x)`**：名前（Name）と備考（Note）に使います。
   - NFKC で正規化します（全角英数を半角にします）。
   - 括弧を全角に変換します（`(` → `（`、`)` → `）`）。
   - 連続する空白を1つに畳み、前後の空白を取り除きます。
2. **`squash_field(x)`**：場所（Location）、時刻（Time）、営業時間（Business Hours）に使います。
   - NFKC で正規化します。
   - 空白をすべて取り除きます。
   - 括弧を全角に変換します。
   - チルダ `~` を全角の `～` に変換します。

## 臨時店舗

公認ではない店舗や、臨時に営業する店舗は、`data/extra/*.json` に置いて載せます。このディレクトリは追跡対象で、置いた JSON は次の毎朝の更新（または `workflow_dispatch` による手動実行）で公開されます。

JSON は1日分のエントリの配列です。複数日に営業する店舗は、日ごとにエントリを書きます。

```json
[
  {
    "id": "popup-curry",
    "name": "臨時カレー販売",
    "date": "2026-10-15",
    "location": "並楽館前",
    "category": "キッチンカー",
    "headline": "学園祭の準備期間限定",
    "url": "https://example.com/",
    "start_time": "11:00",
    "end_time": "14:00",
    "business_hours": "11:00～14:00",
    "note": "売り切れ次第終了"
  }
]
```

| 項目 | 必須 | 内容 |
| :--- | :--- | :--- |
| `id` | 必須 | 半角英小文字・数字・ハイフンだけ。店名にしません（「識別子と名前」のとおり）。 |
| `name` | 必須 | 店名 |
| `date` | 必須 | `YYYY-MM-DD` |
| `location` | 必須 | 場所。建物名で始めると、マップのその建物と連動します（例：`並楽館前`）。学外など、該当する建物がなければ、マップ外として扱います。 |
| `start_time`、`end_time` | 必須 | `HH:MM` |
| `category` | 任意 | 既存のカテゴリ。省略すると `ショップ` |
| `headline`、`url`、`note` | 任意 | `url` は `http://` または `https://` で始めます。 |
| `business_hours` | 任意 | 省略すると `start_time～end_time` |

- ファイルは名前順に読み、同じ `(id, date)` は後のものが先のものを置き換えます。公式の店舗と同じ `id` と日付を書くと、その日のエントリを置き換えます。
- 出力には `temporary: true` が付き、サイトのカードに「臨時」と表示します。
- カードは HTML として組み立てるため、`<` と `>` を含む項目は受け付けません。
- 過去の日付のファイルも消さずに残します。その日に何が営業していたかの記録になります。

## データパイプライン

すべて `just` から実行します。単体のスクリプトを直接呼ぶ想定ではありません。

| スクリプト | 入力 | 出力 |
| :--- | :--- | :--- |
| `scripts/fetch_cafeteria_pdf.py` | 大学サイト | `data/pdfs/YYYY_MM.pdf`、`data/pdfs/.metadata.json` |
| `scripts/parse_cafeteria_pdf.py` | `data/pdfs/YYYY_MM.pdf` | `data/cafeterias/YYYY_MM.json` |
| `scripts/fetch_kitchen_cars.py` | SHOP STOP のページ | `data/kitchencars/raw.html` |
| `scripts/scrape_kitchen_cars.py` | `data/kitchencars/raw.html` | `data/kitchencars/scraped.json` |
| `scripts/generator.py` | 上記の2つ、アーカイブ、マスター、`data/extra/*.json` | `static/api/` |

`generator.py` の必須引数は6つあります。`--cafeteria-dir`、`--kitchen-cars`、`--kitchen-cars-archive`、`--master`、`--base-url`、出力先の `-o` です。臨時店舗のディレクトリは任意の引数 `--extra-dir` で渡し、`just generate` は `data/extra` を渡します。`data/cafeterias/` と `data/kitchencars/` は追跡対象外の中間生成物です。`just` の解析のレシピは、入力（PDFやHTML）が出力より新しいときだけ解析し直します。作り直したいときは `just clean` で削除します。CI は毎回リポジトリを取得し直すため、毎朝すべてを解析します。

生成後、Hugo が `static/` を `public/` へコピーし、`public/` を gh-pages ブランチとして公開します。

### キッチンカーの出店の読み取り

SHOP STOP のページには、出店が2つの形式で載っています。

- **単日出店**：日付のバッジに `2026/10/07 (水)` の形で日付があります。
- **定期出店**：バッジは `毎週月曜日` で、日付は「次回出店 9月28日」として年なしで載ります。次回出店の1日分だけを記録し、年は基準日（JST の今日）に最も近い年を補います。毎朝の取得で次回出店が翌週に進み、過ぎた日はアーカイブで凍結されるので、毎週分が順に記録されます。

## 不変条件

### キッチンカーのアーカイブ

`data/kitchen_cars_past.json` は、その日に何が出店していたかの**唯一の記録**です。情報源は過去の出店情報をすぐ削除するため、失うと復元できません。

- 過去（`date < today`、JST）のエントリは凍結し、削除も変更もしません。
- 当日以降はスクレイプ結果を正とし、出店の取りやめや時間変更を反映します。
- スクレイプ結果が0件のときはフェッチ失敗の可能性があるため、アーカイブに手を加えません。
- 更新のたびに main ブランチへコミットします。CIは毎回リポジトリを取得し直すため、コミットしないと蓄積が失われます。

### ベースURL

サイトのURLは `hugo.toml` の `baseURL` を唯一の情報源とします。`Justfile` は `hugo config` から導出し、フロントエンドは `layouts/_default/baseof.html` が `relURL` で解決した値を `window.BASE_PATH` として渡します。**どこにもハードコードしないでください。**

サブパス（`/welfare-time/`）で配信しているため、ルート絶対パス（`/foo.png`）は常に誤りになります。

## 異常時の扱い

毎朝の更新は、1か所の異常で全体を止めないようにしています。

| 状況 | 扱い |
| :--- | :--- |
| キッチンカーのスクレイプ結果が0件 | アーカイブに手を加えず、当日以降の予定も前回のまま残します。夏期休暇中はこれが正常です。 |
| マスターに登録されていない食堂 | `missing-` で始まる `id` で公開してデータを残し、ログの `!!! MAJOR ERROR` と GitHub Actions の警告（`::warning`）でまとめて知らせます。更新は止めません。 |
| `data/extra/*.json` の不備（JSON として読めない、必須項目がない、形式が違う） | そのファイルまたはエントリだけを読み飛ばし、ログと GitHub Actions の警告（`::warning`）で知らせます。更新は止めません。 |
| 取得や解析のスクリプトが失敗 | ワークフローが失敗し、GitHub の標準の通知（メールなど）で知らせます。通知の受け取り方は、各自の GitHub の設定に従います。 |

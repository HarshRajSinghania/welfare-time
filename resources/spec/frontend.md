# サイトの仕様

## 技術構成

| 項目 | 使うもの |
| :--- | :--- |
| サイト生成 | Hugo（CI では 0.119.0 extended） |
| CSS | Tailwind CSS v4。`assets/css/main.css` に設定を書き、Tailwind CLI でビルド時に `static/css/compiled.css` へコンパイルします。CDN は使いません。 |
| JavaScript | フレームワークを使わない素の JavaScript（ES6 以降） |
| 日付の選択 | Flatpickr |

## コンテンツとテンプレート

- コンテンツ（Markdown）と見た目（レイアウト、CSS、JS）を分けます。
- `content/` 配下の Markdown には、HTMLタグを書かずに標準的な Markdown で書きます。ページの設定は Front Matter に書きます。
- レイアウトの処理は `layouts/` 配下（`_default/baseof.html`、`partials/`、`shortcodes/`）にまとめます。
- ヘルプの変更履歴のページは、リポジトリ直下の `CHANGELOG.md` をショートコード（`layouts/shortcodes/changelog.html`）でそのまま表示します。

## 画面の要件

### 共通のヘッダー

- ナビゲーション（カード、マップ、GitHub、ヘルプ）を置きます。メニューは `hugo.toml` の `menus.main` で定義します。
- 再読み込み、表示フィルタ、並び替え、情報（取得元の表示）、テーマの切り替えのボタンを置きます。
- ヘッダーはスクロールしても画面の上部に固定します。

### 日付ナビゲーション

- 前日・今日・翌日のボタンと、日付を選ぶカレンダー（Flatpickr）を置きます。
- 今日を表示しているときは「今日」ボタンを押せなくします。
- データの提供範囲と最終更新時刻を表示します。

### 店舗のカード

- 表示中の日付に営業予定がある施設だけを、カードで一覧します。
- 現在時刻から「営業中」「準備中」「営業終了」を判定して表示します。未来の日付は準備中、過去の日付は営業終了として扱います。
- 場所と営業時間は横に並べて表示します。

### マップ

- `#map-wrapper` にキャンパスマップの画像を置き、その上に建物の範囲（`.building-area`）を重ねます。建物の位置はマスターの `buildings` から読みます。
- カードと建物は連動します。カードにカーソルを合わせると建物を強調し、建物にカーソルを合わせると、その建物の施設を強調して一覧の先頭に移します。
- キッチンカー（場所が「大学内指定場所」）は、ピロティ（`pilotis`）の建物に対応づけます。
- マップの外にある店舗にカーソルを合わせたときは、マップ全体を暗くし、「この店舗はマップ外です」と重ねて表示します。

### フッタ

- `package.json` の `version` と、コードの最終更新日時を表示します。最終更新日時はビルド時に Justfile が `HUGO_PARAMS_CODEUPDATED` で渡します。
- バージョン番号から、ヘルプの変更履歴のページを開けます。

## JavaScript の規約

- **モジュールに分けます。** 処理は機能ごとに `static/js/` 配下に置きます。
  - `filter.js`：絞り込みの状態と判定
  - `sort.js`：並び替え
  - `main.js`：データの読み込み、描画、全体の制御
  - `modal.js`：モーダルの開閉。開くボタンに `data-modal-open="モーダルのid"`、閉じるボタンに `data-modal-close` を付けます。
- **パスは `window.BASE_PATH` から作ります。** サブパス（`/welfare-time/`）で配信しているため、リソースやAPIのパスはすべて `BASE_PATH` を前置します。`BASE_PATH` は `baseof.html` が `relURL` で求めて渡します。
- **データで動かします。** 建物の座標などはマスター（`assets/facilities.json`）を非同期に読み込み、JavaScript にハードコードしません。
- **イベントは委譲します。** 店舗の一覧（`#shop-grid`）にイベントリスナーを一度だけ登録し、`mouseover` や `mouseout` でカードへの操作を検知します。要素ごとに `onmouseenter` などを設定しません。
- **描画の完了を保証します。** `render()` はDOMを作り終えてから、引数で受け取ったコールバックを同期的に実行します。マップの操作の初期化は、このコールバックの中で行います。
- **テンプレートにスクリプトを書きません。** `layouts/` 配下のHTMLにインラインの JavaScript や `onclick` などのイベント属性を残しません。ただし、`baseof.html` でのスクリプトの読み込みと `BASE_PATH` の設定、Google Analytics の計測タグ（`partials/google_analytics.html`）は除きます。

## CSS の規約

- スタイルはほぼすべて、HTML 上の Tailwind のユーティリティクラス（`flex`、`grid`、`rounded`、`dark:...` など）で書きます。
- `static/assets/style.css` には、Tailwind では書きにくいものだけを置きます（マップの建物の範囲、横スクロールのバーを隠す指定、Flatpickr のダークモードの上書きなど）。
- HTML や JavaScript にインラインの CSS を書きません。
- Tailwind のクラスと `style.css` が競合した場合は Tailwind を優先し、`style.css` の不要な定義を削除します。
- マップのホバーが反応しないときは、重ねた層の `pointer-events` と、建物の範囲の `z-index` を確認します。

## 未対応の課題

上の規約のうち、まだコードが追いついていないものです。それぞれ issue で管理しています。直したら、この一覧からも削除します。

| issue | 内容 |
| :--- | :--- |
| [#58](https://github.com/tamadalab/welfare-time/issues/58) | `main.js` が、建物の範囲とカードに `onmouseenter` と `onmouseleave` を1つずつ設定しています。`#shop-grid` へのイベント委譲に移す必要があります。 |
| [#59](https://github.com/tamadalab/welfare-time/issues/59) | `render()` が描画完了のコールバックを受け取らず、マップの操作の初期化を直接呼んでいます。 |
| [#60](https://github.com/tamadalab/welfare-time/issues/60) | `main.js` が、カードやマップの画像の `style.opacity` を直接書き換えています。Tailwind のクラスの付け外しに移す必要があります。 |
| [#61](https://github.com/tamadalab/welfare-time/issues/61) | マップのページに、使われていない `#tooltip` の要素が残っています。`layouts/_default/map.html` はファイル全体が使われていません。 |
| [#63](https://github.com/tamadalab/welfare-time/issues/63) | `static/assets/style.css` の先頭のコメントに、旧名の「Shikaku」が残っています。 |

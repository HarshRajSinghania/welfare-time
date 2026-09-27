# 開発の進め方

## 開発環境

バージョンは、毎朝の更新のワークフロー（`.github/workflows/daily_update.yml`）で使っているものに合わせます。

| ツール | 用途 |
| :--- | :--- |
| Python 3.11 | データの取得、解析、API の生成 |
| Hugo 0.119.0（extended） | サイトの生成。`just generate` がベースURLの取得にも使います。 |
| Node 26 | Tailwind CSS のビルド |
| [just](https://github.com/casey/just) | タスクの実行 |

セットアップの手順と、主なコマンドの一覧はリポジトリ直下の [README.md](../../README.md) にあります。`just help` でもレシピの一覧を表示できます。

## 作業のルール

- **削除操作：** 生成物の削除は許容します。`just clean` は `data/` 配下の生成物（`data/cafeterias/` と `data/kitchencars/`）と `tmp/` を、デプロイ時は `public/api/` を削除して作り直します。追跡対象のファイルやデータを消す変更は、事前に確認を取ってください。特に `data/kitchen_cars_past.json` は復元できません。
- **入力のパス：** スクリプト内にハードコードせず、CLI引数（`argparse`）で受け取ります。
- **出力のパス：** 既定は標準出力とし、ファイルへの出力は `-o` / `--output` で指定します。
- **正規化：** [data.md](data.md) の `squash_name` / `squash_field` を必ず適用します。
- **状態管理：** PDFの取得状況は `data/pdfs/.metadata.json` で追跡します。`just generate` がこれを `static/daily/` へコピーし、`generator.py` が出力先から読みます。
- **ブランチ：** main に直接コミットせず、ブランチを作って PR を出します。main へ直接コミットするのは、毎朝の更新によるアーカイブのコミットだけです。

## テスト

解析や生成の処理を変更したら `just test` を実行します。食堂のパーサ、キッチンカーのスクレイパー、`generator.py` のテストが対象です。

`just test` は `PYTHON` 変数が指すインタプリタで動きます。依存関係を入れた環境を指定してください。

```bash
just PYTHON=/path/to/venv/bin/python test
```

夏期休暇中は情報源の出店が0件になるため、実データでスクレイパーを動かしても、出店を処理する部分を一度も通りません。**この期間、実データでの動作確認は不具合の検出にほとんど役立ちません。** `testdata/kitchen_cars_sample.html` を使う `just test` で確認してください。

取得元のページの形式が変わったときは、実際のページと同じ構造の出店を `testdata/` のフィクスチャに加えて、テストで固定します。

## CI

| ワークフロー | 実行のタイミング | 内容 |
| :--- | :--- | :--- |
| `daily_update.yml` | 毎日 UTC 22時（JST 7時）と手動 | データの取得、API とサイトの生成、アーカイブの main へのコミット、gh-pages へのデプロイ |
| `test.yml` | PR と main への push | `just test` |
| `copilot-setup-steps.yml` | このファイルの変更時と手動 | Copilot coding agent の作業環境の構築 |

- `copilot-setup-steps.yml` のジョブ名は `copilot-setup-steps` でなければなりません。Copilot は main にあるこのファイルを使うため、変更は main にマージしてから有効になります。
- マスターに未登録の店舗があっても、毎朝の更新は失敗させず、警告だけを出します（[data.md](data.md) の「異常時の扱い」）。

## バージョン管理

- 機能と変更点は [CHANGELOG.md](../../CHANGELOG.md) にまとめます。バージョン番号の上げ方もそこに書いています。
- バージョン番号は `package.json` の `version` だけで管理します。`package-lock.json` のルートのバージョンも合わせます。
- 毎朝の自動更新によるデータのコミットは、バージョンの対象に含めません。

リリースするときは次の手順で行います。

1. `CHANGELOG.md` に新しいバージョンの変更点を追記します。
2. `package.json` の `version` を上げます。
3. main にマージしたあと、`v0.4.0` のようにタグを打ちます。

# Welfare TIME 仕様書

Welfare TIME の仕様と、コードを変更するときに守る規約をまとめています。利用者向けの概要とセットアップ手順はリポジトリ直下の [README.md](../../README.md) にあります。

## 文書の一覧

| 文書 | 内容 |
| :--- | :--- |
| [overview.md](overview.md) | プロジェクトの目的、システム構成、データソース、更新のタイミング、免責事項 |
| [data.md](data.md) | 識別子と名前、正規化、データパイプライン、キッチンカーのアーカイブ、異常時の扱い |
| [api.md](api.md) | 公開APIの設計方針と、APIリファレンスの置き場所 |
| [frontend.md](frontend.md) | サイトの技術構成、画面の要件、JavaScript と CSS の規約、未対応の課題 |
| [development.md](development.md) | 開発環境、作業のルール、テスト、CI、バージョン管理 |

## 文書の扱い

- 仕様を変えるコードを書いたら、同じ PR でこの文書も更新します。
- 公開APIの項目の定義は、サイトの [APIリファレンス](../../content/help/api.md) を正とします。ここには同じ内容を書かず、設計方針だけを書きます。
- 機能と変更点の履歴は [CHANGELOG.md](../../CHANGELOG.md) にまとめます。

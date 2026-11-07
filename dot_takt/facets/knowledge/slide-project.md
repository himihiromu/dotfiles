# プロジェクトに合わせたスライド制作

- 作業先の README、指示ファイル、既存の原稿、package.json 等のビルド定義、CI、設定ファイルを確認する。ワークフローを配布する dotfiles ではなく、実際の発表資料リポジトリを編集する。
- 原稿の形式はプロジェクトに合わせる。Pandoc Markdown、Marp、Slidev 等は互換ではない。既存の変換処理が Markdown として読む場合は、MDX/JSX を混ぜない。
- docs/slides/<slug>/brief.md に制作条件に加え、source_path（原稿パス）、support_dir（docs/slides/<slug>）、必要な frontmatter、見出しとページ区切り、生成物のパス、build_command、preview_command、presentation_url、navigation（送り・戻りの操作）を記録する。
- 原稿パスは依頼で指定されていれば実構成と照合する。省略時は既存原稿とビルド設定から判断し、根拠を brief.md に記録する。一意に判断できなければ BLOCKED。ビルド対象の外に作って完了したことにしない。
- コマンド・URL・ポート・ベースパスは作業先の定義から確認する。npm、Pandoc、固定の URL を他のプロジェクトへ無条件で適用しない。必要なツール・依存関係を確認し、既存 lockfile に対応するインストール方法を使う。
- ブラウザ表示向けの資料には既存のビルド・プレビューを使用する。ビルド不要の構成では、その根拠と実際の表示方法を明記し、ビルドを「対象外」としてよい。表示方法そのものが不明、または必要なブラウザ環境がなければ BLOCKED。
- ブラウザで全ページの文字・コード・図のはみ出しを確認し、既存エンジンの送り・戻り操作を確認する。縦方向がある場合は縦方向も確認。headless でもよい。HTTP 200 やファイル生成だけで表示確認済みにしない。
- 起動したプレビューは停止する。他の作業者のサーバーは停止しない。生成物を原稿として直接編集しない。

## lt-slide-warehouse の場合（構成を再確認して使う例）

- 原稿は src/slides/<slug>.md。title を持つ YAML frontmatter が必要。
- src/integrations/pandoc-builder.ts が --slide-level 2 で reveal.js 向けに変換し、src/content/slides/ を生成する。H1/H2 の横・縦構造を実際の表示で確認する。
- package.json と README の環境要件を満たし、npm ci、npm run build で検証。npm run preview で /lt-slide-warehouse/slides/<slug>/ を確認する。
- 上記は適用例であり、他のリポジトリの保存先・コマンド・URLの既定値ではない。

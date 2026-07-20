# TAKT Video Workflows

技術系VOICEVOX動画の制作・改善・振り返り・Asset制作を行うTAKTワークフロー群です。
`video-production`、`video-improvement`、`video-retrospective`、`video-assets` の4つのワークフローが
相互に連携し、Knowledge LayerとAsset Libraryを継続的に成長させます。

## 配置

このディレクトリの `dot_takt/` を、対象Remotionリポジトリのルートへ `.takt/` としてコピーしてください。

```bash
cp -R dot_takt /path/to/remotion-repository/.takt
cd /path/to/remotion-repository
```

既に `.takt/` がある場合は、ディレクトリ単位で上書きせず、各ファイルをマージしてください。

## 検証

TAKTの現行バージョンで定義を検証します。

```bash
takt workflow doctor
```

## 実行

```bash
takt
```

ワークフロー選択で対象を選び、必要な情報を伝えて `/go` します。

キューへ追加した場合:

```bash
takt run
```

## ワークフロー一覧

### video-production
技術系VOICEVOX動画を新規制作するワークフロー。

企画 → 調査 → 台本 → 3観点レビュー → VOICEVOX調整 →
Remotion絵コンテ → Remotion実装 → 最終レビュー

### video-improvement
既存動画の品質を改善するワークフロー。

Content Analysis → 4観点Review → Review統合 → 修正計画 →
Script修正 → Storyboard修正 → Producer Review

### video-retrospective
制作プロセスを振り返り、Knowledge Layerを改善するワークフロー。

制作要約 → プロセス分析 → 知識抽出 → テンプレート更新提案 → Retrospective Review

### video-assets
再利用可能なRemotion Componentを制作・レビュー・管理するワークフロー。

Asset Plan → Asset Design → Technical Validation → Implementation → Review → Catalog Update

動画専用ではなく、Asset Libraryとして長期的に育てることを目的とします。
ターミナル、コードエディタ、ダイアグラム、アニメーション、比較表等の共通Componentを対象とします。

## 主な成果物

```text
video/production/
├── topic-plan.md
├── research.md
├── script.md
├── script-revision-log.md
├── voicevox-script.md
├── storyboard.md
├── storyboard-revision-log.md
├── remotion-implementation.md
└── remotion-revision.md
```

Remotionコードの実際の配置先は、既存リポジトリ構造を調査して決定します。

## 判定トークン

遷移の誤検出を避けるため、各Output Contractは最終行に固定トークンを一つだけ出します。
自然文の条件ではなく、次の固定トークンを遷移条件に利用しています。

- STEP_COMPLETE / NEEDS_INPUT / STEP_BLOCKED
- REVIEW_APPROVED / REVIEW_NEEDS_FIX / REVIEW_BLOCKED
- PRODUCER_APPROVE
- PRODUCER_REVISE_SCRIPT
- PRODUCER_REVISE_STORYBOARD
- PRODUCER_REVISE_IMPLEMENTATION
- PRODUCER_BLOCKED
- ASSET_IMPLEMENTED / ASSET_NEEDS_REWORK

## 注意

- 各ワークフローの `max_steps` は、レビュー修正ループを含む上限です。
- Webアクセス可否は使用プロバイダと権限に依存します。
- 実際のTAKTバージョンで `takt workflow doctor` を必ず実行してください。

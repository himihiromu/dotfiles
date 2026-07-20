# TAKT Video Production Workflow

技術系VOICEVOX動画を、企画 → 調査 → 台本 → 3観点レビュー → VOICEVOX調整 →
Remotion絵コンテ → Remotion実装 → 最終レビューの順で制作するTAKTワークフローです。

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

ワークフロー選択で `video-production` を選び、作りたい動画のテーマ、対象視聴者、
想定尺、参考資料、既存Remotion動画のパスなどを伝えて `/go` します。

キューへ追加した場合:

```bash
takt run
```

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

## 注意

- `max_steps: 40` は、レビュー修正ループを含む上限です。
- Webアクセス可否は使用プロバイダと権限に依存します。
- 実際のTAKTバージョンで `takt workflow doctor` を必ず実行してください。

# Remotion リポジトリ構成

## ディレクトリ構成
```text
src/
├── components/     # 共通UIコンポーネント
├── videos/          # 動画固有のエントリポイント
│   └── <video-id>/
│       ├── index.ts        # Composition登録
│       ├── scenes/         # シーンコンポーネント
│       └── data/           # 台本・タイミングデータ
├── assets/         # 音声・画像等の静的アセット
├── hooks/          # カスタムReact Hooks
├── types/          # 型定義
└── utils/          # ユーティリティ関数
```

## 各ディレクトリの責務

### components/
- 複数動画で再利用するUIコンポーネント
- 字幕、キャラクター表示、コード表示、図解等

### videos/
- 動画ごとのエントリポイントと固有リソース
- 動画間で独立した構造

### assets/
- VOICEVOX音声ファイル
- 画像、ロゴ、スクリーンショット
- BGM、SE

### hooks/
- useCurrentFrame等を活用したカスタムHooks
- アニメーションやタイミング計算の共通化

### types/
- 台本データの型定義
- コンポーネントPropsの型定義
- 共通のユーティリティ型

### utils/
- フレーム計算のヘルパー
- テキスト処理
- 色やスタイルの定数

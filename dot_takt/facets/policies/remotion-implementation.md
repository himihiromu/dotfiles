# Remotion Implementation Policy
- 既存の package.json、tsconfig、Remotion構成、命名規則を優先する。
- 存在しない依存関係やアセットを存在するものとして扱わない。
- ネットワークアクセスをレンダリング時の必須条件にしない。
- 型エラーやビルドエラーを隠さない。
- 実行できなかった検証は未実施として報告する。

# Remotion Best Practices
- フレーム情報は `useCurrentFrame()` と `useVideoConfig()` から取得する。
- アニメーションは `interpolate()` または `spring()` を使用する。
- タイミング制御は `Sequence` コンポーネントを使用する。
- レンダリング関数内に `Math.random()` や副作用を含めない。
- 同じ入力からは常に同じ出力が得られるよう決定論的であること。
- `AbsoluteFill` やレイアウトヘルパーを適切に使用する。

# mise タスク

このディレクトリには、`~/ghq/github.com/himihiromu/my-nix-package-control` にある
ローカルリポジトリ向けの mise タスクを定義しています。chezmoi でこの設定を適用すると、
どのディレクトリからでも実行できます。

| コマンド | 動作 |
| --- | --- |
| `mise develop <environment> [options...]` | 指定した flake 環境の `nix develop` を起動し、追加引数を渡します。 |
| `mise home-manager <action> [options...]` | ローカル options input と `#myHomeConfig` を使い、指定した Home Manager の操作を実行します。 |
| `mise nis-darwin <action> [options...]` | ローカル options input と `#mac-config` を使い、指定した nix-darwin の操作を実行します。 |
| `mise nixos <action> [host] [options...]` | ローカル options input を使い、指定したホストの flake 構成に対して `nixos-rebuild` を実行します。ホスト省略時は従来の flake 指定です。 |
| `mise nix update [options...]` | ローカルリポジトリに対して `nix flake update` を実行します。 |
| `mise nix gc [options...]` | `nix-store --gc` を実行します。 |
| `mise nix <nix arguments...>` | 管理リポジトリ内で、その他の引数を `nix` にそのまま渡します。 |

`nixos` のホスト名は `flake.nix` の `nixosConfigurations` のキーを指定します。ホストを省略してオプションを渡す場合は、操作名の直後から `-` で始まる引数を指定します。
`nis-darwin` と `nixos` は従来どおり `sudo` を使います。
`mise nix gc` は、Nix store から不要なパスを削除します。

## Nix 管理コマンド

以下はすべて `~/ghq/github.com/himihiromu/my-nix-package-control` 内で実行します。
呼び出し元の cwd に依存せず、相対パスの追加引数も管理リポジトリ基準で解釈されます。

```sh
mise home-manager switch
mise nis-darwin switch
mise nixos switch
mise nixos switch macbook-air --show-trace
mise nix update
mise nix update nixpkgs home-manager
mise nix gc
```

`home-manager` は既存の `nix run nixpkgs#home-manager --`、`nis-darwin` は
`sudo nix run nix-darwin --`、`nixos` は `sudo nixos-rebuild` を使います。
`nis-darwin` は意図した呼び出し名です。flake の `#myHomeConfig` / `#mac-config`、
Home Manager の `--show-trace`、各切替コマンドの
`--override-input local-options "path:$HOME/.config/nix/local-input/default.nix"` は維持しています。
端末固有の options ファイルは既存セットアップで用意する前提です。
`nixos` のホスト省略時は既存どおり flake パスのみを渡し、選択は nixos-rebuild に任せます。
PC に対応する構成を明示する場合は `macbook-air` などのホストを指定してください。

`nix update` は管理リポジトリ内で `nix flake update` を実行します。
[現行 Nix の位置引数は入力名](https://nix.dev/manual/nix/latest/command-ref/new-cli/nix3-flake-update.html)
なので、リポジトリパスを位置引数として渡しません。
追加の入力名やオプションはそのまま渡します。
`nix gc` は同じ cwd で `nix-store --gc` を実行しますが、GC の対象は
リポジトリ専用ではなく、従来どおり Nix store の不要なパスです。
汎用の `mise nix <arguments...>` も管理リポジトリ内で実行します。

各管理タスクは追加引数とコマンドの終了コードを引き継ぎます。
リポジトリが存在しなければ mise がエラーで終了し、管理コマンドは起動しません。
`develop` は開発中のディレクトリを保つため、引き続き呼び出し元 cwd で実行します。

## Nix 開発環境を開く

前提は Bash、mise、flakes を利用できる Nix と、
`~/ghq/github.com/himihiromu/my-nix-package-control` のチェックアウトです。
既存の chezmoi 運用で `dot_config/mise/config.toml` を
`~/.config/mise/config.toml` に配置して利用します。Windows は既存の
`.chezmoiignore` でこの設定の配布対象外です。

```sh
cd ~/projects/example
mise develop js
# nix develop "$HOME/ghq/github.com/himihiromu/my-nix-package-control#js"

mise develop python
mise develop js --command node --version
# 明示的なタスク呼び出しも同じ動作
mise run develop js
```

`dir = "{{cwd}}"` で呼び出し元のディレクトリを保持し、`raw = true` で
対話シェルへ標準入出力を直接渡します（[mise タスク設定](https://mise.jdx.dev/tasks/task-configuration.html)）。
環境名は固定リストで制限せず、最初の引数を flake の `#` 以降へ渡します。
残りの引数は空白や空文字を含めてそのまま Nix に渡します。
環境名の省略・空文字は usage を表示して終了コード 2 で終了します。
未定義の環境名、未取得のリポジトリ、Nix 側のエラーは Nix に任せ、終了コードを引き継ぎます。

2026-10-17 にローカルの `flake.nix` を読み取り、`default`（`zai` の別名）、
`zai`、`python`、`js`、`java21`、`java8`、`go`、`kotlin`、`csharp` を確認しました。
これは定義の確認であり、各 OS での評価・起動成功を保証する一覧ではありません。
`zai` / `default` は shellHook で認証情報を要求する場合があります。

ghq のカスタムルートや複数ルートの自動検索は行わず、既存タスクと同じ
`$HOME/ghq` の配置を使います。プロジェクト側に同名の `develop` タスクがあれば
そちらが優先されます（[mise タスク探索](https://mise.jdx.dev/tasks/task-discovery.html)）。

## 変更の検証

リポジトリルートで Python 3 と mise を使って実行します。

```sh
python3 -m unittest discover -s tests -v
```

テストは一時 HOME とグローバル mise 設定を作り、実際の mise CLI から
記録用の偽 `nix` / `sudo` / `nixos-rebuild` / `nix-store` を起動します。
実際の環境適用、Nix 評価、システム切替、秘密情報の読み取りは行いません。

2026-10-17、Linux / mise 2026.10.3 / Python 3.14.7 で11テスト成功。
ホーム内外の cwd、任意の環境名、空白・特殊文字・空文字を含む追加引数、
環境名の省略・空文字、Nix の失敗コード、PTY の標準入出力、既存タスク7パターンを検証しました。
変更前の設定では cwd の比較3件と空文字の拒否1件が失敗することも確認しました。
管理タスクはホーム内外の cwd から switch / build、ホスト指定と省略、
追加引数（空白・空文字・特殊文字）、終了コード 0 / 42 を40ケースで検証しました。
管理タスク4種の PTY 引き渡し、要求された5コマンドの追加引数なし実行、
入力名を指定した update、
操作名の省略、チェックアウト欠落時の未起動も確認しています。
Nix 2.34.8 の `nix flake update --help` で位置引数が入力名であることを確認しました。
chezmoi 2.73.0 の `managed`（一時設定・一時 destination を指定）でも、
`.config/mise/config.toml` が管理対象で `tests/` が除外されることを確認しました。

実際の chezmoi 適用、各 devShell の起動、管理コマンドの実行（switch / update / gc）、
実 sudo による昇格、対話シェルのジョブ制御、macOS、
別バージョンの mise は未検証です。カスタム ghq ルートを対象にするかは別途判断が必要です。

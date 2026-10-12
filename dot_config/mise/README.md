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
| `mise nix <nix arguments...>` | その他の引数を `nix` にそのまま渡します。 |

`nixos` のホスト名は `flake.nix` の `nixosConfigurations` のキーを指定します。ホストを省略してオプションを渡す場合は、操作名の直後から `-` で始まる引数を指定します。
`nis-darwin` と `nixos` は従来どおり `sudo` を使います。
`mise nix gc` は、Nix store から不要なパスを削除します。

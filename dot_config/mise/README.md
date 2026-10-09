# mise タスク

このディレクトリには、`~/ghq/github.com/himihiromu/my-nix-package-control` にある
ローカルリポジトリ向けの mise タスクを定義しています。chezmoi でこの設定を適用すると、
どのディレクトリからでも実行できます。

| コマンド | 動作 |
| --- | --- |
| `mise develop <environment>` | 指定した flake 環境の `nix develop` を起動します。 |
| `mise home-manager switch` | ローカル options input を使い、`#myHomeConfig` に対して Home Manager を実行します。 |
| `mise nis-darwin switch` | ローカル options input を使い、`#mac-config` に対して nix-darwin を実行します。 |
| `mise nixos switch` | ローカルリポジトリの flake に対して `nixos-rebuild switch` を実行します。 |
| `mise nix update` | ローカルリポジトリに対して `nix flake update` を実行します。 |
| `mise nix gc` | `nix-store --gc` を実行します。 |

`home-manager`、`nis-darwin`、`nixos` の各 switch タスクは、必要に応じて `sudo` を使います。
`mise nix gc` は、Nix store から不要なパスを削除します。

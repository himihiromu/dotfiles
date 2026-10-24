# dotfiles

chezmoi を利用して、複数 OS / 複数端末にまたがる設定を管理するためのリポジトリです。

## セットアップ

chezmoiをセットアップの入口としてdotfilesを適用します。

NixOSでは、汎用Linux向けのchezmoiバイナリを直接実行できないため、
Nixpkgsのchezmoiを利用します。

```shell
nix run nixpkgs#chezmoi -- init --apply himihiromu
```

NixOS以外では、chezmoiの公式インストーラーから初期化します。

```shell
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply himihiromu
```

ユーザー名、Git設定、デスクトップ環境かどうかなどの端末固有値は、
`.chezmoi.toml.tmpl`から質問され、chezmoiのローカル設定へ保存されます。

Linuxでは初回の`chezmoi apply`に続いて、`/etc/os-release`からディストリビューションを判定し、
環境に応じたNix構成を適用します。

- NixOSではNixOS configurationをリビルド
- それ以外のLinuxでは単体Home Manager configurationを適用

NixOS/Home Managerからchezmoiを呼び戻さない一方向の構成にしています。

## 目的

このリポジトリは、長期的に維持したい設定を整理し、環境差分を吸収しながら再利用しやすく管理するための受け皿です。

主に以下を扱います。

- シェル設定 (`bash`, `zsh`, `fish` など)
- `~/.config` 配下の永続的に使う設定
- OS 別セットアップスクリプト
- テンプレート化しやすい個人設定
- chezmoi で継続運用しやすい dotfiles 群

## 現在の構成

### ルート直下
- `dot_bashrc`
- `dot_zshrc`
- `dot_config/`

通常の dotfiles 本体を置く領域です。

`mise develop js` などで ghq 配下の Nix 開発環境を起動できます。
`mise home-manager switch`、`mise nis-darwin switch`、`mise nixos switch`、
`mise nix update`、`mise nix gc` は同じ管理リポジトリ内で実行します。
前提と使い方、検証方法は [mise タスク](dot_config/mise/README.md) を参照してください。

Bash の abbr・Ctrl+R 履歴検索・Ctrl+U ghq 検索の操作、既存シェルとの比較と検証方法は
[Bash シェル設定](docs/bash-shell.md) を参照してください。
略語展開には [Nix 側 PR #68](https://github.com/himihiromu/my-nix-package-control/pull/68) の
Home Manager 設定で配置する `bash-abbrev-alias` が必要です。

### `.chezmoiscripts/`
- `darwin/`
- `linux/`
- `windows/`

OS ごとのセットアップや初期化処理を分けるための領域です。

### テンプレート系
- `.chezmoi.toml.tmpl`
- `scoop.json.tmpl`

環境差分や端末差分を吸収するためのテンプレート置き場です。

## このリポジトリに集約したいもの

- 複数環境で再利用したい設定
- 長期的に維持したい dotfiles
- chezmoi のテンプレートや OS 分岐で管理しやすい設定
- 再セットアップ時に継続利用したい構成

## 配置ルールの考え方

### 1. 長期運用する設定を優先する
恒久的に使う設定は、可能な限りこのリポジトリへ集約します。

### 2. OS 差分は script / template で吸収する
配置先を分ける前に、chezmoi のテンプレートや `.chezmoiscripts/` で吸収できないかを優先的に検討します。

### 3. 一時的なものはすぐ入れない
試験的な設定や一時的なセットアップ断片は、内容が固まってから取り込む前提にします。

### 4. 秘密情報はそのまま置かない
シークレットや端末固有の値は、そのまま commit するのではなく、テンプレート化やローカル分離で扱う前提にします。

## 今後の方向性

今後は関連する設定群を棚卸ししながら、以下を順に進める想定です。

- `dotfiles` へ統合しやすい設定の分類
- テンプレート化できる内容の切り出し
- OS 別セットアップの整理
- chezmoi 管理対象とローカル専用設定の境界整理

このリポジトリは、設定の最終配置先として分かりやすく保ち、継続的に育てる前提で管理します。

## Nix環境の選択

`chezmoi init` の入力は、次の独立した2項目で環境を選ぶ。

- `is_desktop`: GUIアプリをインストールするか。Nixの `local-options.isDesktop` に渡す。
- `is_wsl`: WSL環境か。Linuxでのみ質問し、初回NixOS適用のホスト選択に使う。

初回導入はNixOSなら `is_wsl = true` で `#nixos-wsl`、falseで `#nixos` を適用する。
NixOS以外のLinuxでは、WSL上のUbuntu等でもHome Manager単体の `#myHomeConfig` を使う。
`is_desktop` によって適用先やNixコマンドを切り替えることはない。
既存設定に `is_wsl` がない場合はfalseとして扱う。既存のWSL環境では
`chezmoi init` で設定を追加するか、chezmoiの設定ファイルの `[data]` に `is_wsl = true` を追加する。

この変更は導入スクリプトの選択に使う。run-onceスクリプトは内容が変わると再実行されるため、
既存のWSL環境は適用前に `is_wsl` を設定する。
スクリプトを実行せずに設定だけ反映する場合は `chezmoi apply --exclude scripts` を使い、
必要なホストを明示して適用する。

```sh
# NixOS-WSL
mise nixos switch nixos-wsl
# 実機のGUI環境では is_desktop をtrueにする
mise nixos switch nixos
```

WSLで共通CLI環境を導入し、GUI選択を反映するには
[Nix設定側のPR #83](https://github.com/himihiromu/my-nix-package-control/pull/83) の変更が必要。
設定確認とテストは `python3 tests/test_nix_bootstrap.py` で行う（chezmoiが必要）。
テストではNixコマンドをスタブ化し、OS設定の適用は行わない。

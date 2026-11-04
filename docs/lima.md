# Lima の共通 Docker 設定

macOS の Lima で rootless Docker を使うための設定。
chezmoi は `dot_lima/_config/override.yaml` を `~/.lima/_config/override.yaml` に配置する。
Linux / Windows では `.lima` を管理対象から除外する。
`LIMA_HOME` を変えている場合は、そのディレクトリの `_config` へ別途配置する必要がある。

## 優先順位と移行

Lima は起動・再起動のたびに、次の優先順位で設定を読む。

1. `$LIMA_HOME/_config/override.yaml`
2. インスタンスの `lima.yaml`（使用したテンプレートの設定を含む）
3. `$LIMA_HOME/_config/default.yaml`
4. Lima 組み込みの既定値

`default.yaml` は未指定項目の補完用なので、インスタンスが明示した
`containerd.user: true` や `mounts[].writable: false` などを上書きできない。
このリポジトリの Docker 設定は `override.yaml` に置く。

配列は原則として override → インスタンス → default の順で結合される。
`images` は該当アーキテクチャの先頭候補、`portForwards` は最初に一致するルールが優先される。
`mounts` は同じ `location` の設定が統合され、override の `writable` が優先される。
`provision` / `probes` はインスタンス側の項目も残るため、Docker のプロビジョニングを
別途含む `template:docker` と重ねず、通常の Ubuntu テンプレートから作成する。

既存の `default.yaml` はコメントだけの管理ファイルとして残している。
chezmoi の適用で旧内容を空にし、旧ファイルと override の両方から
同じ provision / probes / portForwards が読み込まれることを防ぐ。
移行前にローカル独自の設定があれば退避し、`chezmoi diff` で差分を確認する。
**両方のファイルを一緒に適用する**。

## 維持する設定

- x86_64 / aarch64 の Ubuntu イメージ。旧 Ubuntu 21.04 から Docker が対応する Ubuntu 24.04 LTS に更新。
- `/tmp/lima` と `~/Documents` の書き込み可能マウント。
- SSH のホストポート `60006`、`~/.ssh/*.pub` の読み込み。
- Lima が管理する system / user containerd の無効化。
- Docker のインストール、rootful Docker の service / socket 停止、rootless Docker の初期化。
- Docker CLI と rootlesskit の readiness probe。
- ゲストの `/run/user/{{.UID}}/docker.sock` からホストの `{{.Dir}}/sock/docker.sock` への転送。

これは同じ `LIMA_HOME` の**全インスタンス**に適用される。
固定 SSH ポート `60006` を維持するため、同時起動は1台にする。
異なる用途や複数台を使う場合は、別の `LIMA_HOME` に分離する。

## 適用と確認

```sh
chezmoi diff ~/.lima/_config/default.yaml ~/.lima/_config/override.yaml
chezmoi apply ~/.lima/_config/default.yaml ~/.lima/_config/override.yaml

# 新規作成。Docker のインストールと rootless 化は override 側で行う
limactl start --name=docker template:ubuntu
export DOCKER_HOST="$(limactl list docker --format 'unix://{{.Dir}}/sock/docker.sock')"
docker run --rm hello-world
limactl shell docker touch "$HOME/Documents/.lima-write-check"
limactl shell docker rm "$HOME/Documents/.lima-write-check"
```

既存インスタンスは停止してから `limactl start <名前>` で再起動すると override が読み込まれる。
ただし `images` の変更では既存ディスクの OS はアップグレードされない。
旧 Ubuntu 21.04 の VM は必要なデータを退避して新規作成する。
すでに Docker 専用の provision を持つ VM は、先に `lima.yaml` の重複を確認する。

## 自動検証

```sh
python3 tests/test_lima.py
```

chezmoi と `limactl`（検証時: 2.2.1）が必要。
一時ディレクトリで旧 default の移行と OS 別の配布を検査し、
競合するインスタンス設定を Lima 自身の `validate --fill` で読み込んで優先順位を検査する。
VM 起動、Docker インストール、実際の macOS マウント・ソケット接続は行わない。
macOS での実動作は上記コマンドで確認する。

## 出典

確認日: 2026-11-05。

- [Lima: グローバル設定の優先順位と配列のマージ](https://github.com/lima-vm/lima/blob/v2.2.1/templates/default.yaml)
- [Lima: 設定読み込み実装](https://github.com/lima-vm/lima/blob/v2.2.1/pkg/limayaml/load.go)
- [Lima: 公式 Docker 設定](https://github.com/lima-vm/lima/blob/v2.2.1/templates/docker.yaml)
- [Lima: Ubuntu 24.04 イメージ](https://github.com/lima-vm/lima/blob/v2.2.1/templates/_images/ubuntu-24.04.yaml)
- [Docker: Ubuntu の対応バージョン](https://docs.docker.com/engine/install/ubuntu/#os-requirements)
- [chezmoi: ignore はターゲットの相対パスに適用](https://www.chezmoi.io/reference/special-files/chezmoiignore/)

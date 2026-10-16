# Bash の abbr と検索キー

## 調査結果と根拠

対象は Linux に chezmoi が配置する `dot_bashrc`（`.chezmoiignore` は Linux 以外の `.bashrc` を除外）。
要件正本は knowledge-base の `05-todo/development/dotfiles-bash-shell.md`。
Nix 側は `my-nix-package-control` の commit `3212261c687fa96a471ec6a766fb1f0f8dca3506` を読み取り調査した。

| abbr | 展開先 | 定義の根拠 |
| --- | --- | --- |
| `la` | `ls -a` | `dot_zshrc` 末尾、`dot_config/private_fish/config.fish.tmpl:59`、Nix `home-manager/shell/zsh.nix:28` |
| `ll` | `ls -l` | 同 fish `:60`、Nix `:29` |
| `lal` | `ls -al` | 同 fish `:61`、Nix `:30` |

Nix の `programs.zsh.zsh-abbr.abbreviations` と dotfiles の定義は同じ3件。
Bash にはこれらの alias が既にあったが、入力欄で展開する機能はなかった。
既存 alias（`l`、色付き `ls` 等を含む）は維持した。

| 操作 | zsh | fish | 今回の Bash |
| --- | --- | --- | --- |
| Ctrl+R | `dot_zshrc:10–16`: 履歴を fzf、左側入力で絞り込み、選択結果を編集欄へ入れる | `config.fish.tmpl:8–15`: 同様の意図。ただし `--query` が行途中で分断された既存構文不良あり | 履歴を新しい順に fzf、現在の入力全文で絞り込み、選択を編集欄へ挿入。自動実行しない |
| Ctrl+U の候補 | `dot_zshrc:20–31`: `zoxide query -i` の訪問履歴 | `config.fish.tmpl:22–28`: `zoxide query -i` の訪問履歴 | 要件を優先し `ghq list --full-path` を fzf で検索 |
| Ctrl+U 選択後 | `cd <destination>` を入力欄に作り、即実行。入力欄は置き換わる | `cd $result` で即移動、入力欄の明示的な消去なし | `builtin cd -- "$selected"` で即移動し入力欄を消去 |

候補ソースは意図的に zsh/fish と異なる（coordinator 確認済み）。
選択後すぐ移動する点は共通だが、fish の入力欄保持とは異なり、Bash の既存動作である入力欄消去を維持する。
Bash はパスをシェルコードとして評価せず、空白や `$`、`;` もパス文字として扱う。
キャンセル・空選択・ghq 失敗・移動失敗時は入力欄、カーソル、作業ディレクトリを変更しない。
zoxide 初期化は従来通り残り、プロンプトの既存フックによる訪問履歴追跡を妨げない。
Nix `home-manager/shell/bash.nix:8` は `.bashrc` の生成を無効化しているため、その所有関係も変更しない。

## キーと対応範囲

- Bash の標準 Emacs キーマップ向け。vi キーマップには新規キーを設定しない。
- 行頭の単純な `la` / `ll` / `lal` は Space または Enter で展開する。先頭の空白、カーソル後方の入力は保持する。
- 引数、引用符付き文字列、パイプ後のコマンド、複雑なシェル構文内は展開対象外。シェル構文の再解析や `eval` は行わない。
- Enter は展開後に既存の Ctrl+J（accept-line）へ渡す。Ctrl+J 直接入力では表示上の展開を行わず、既存 alias が使える。内部展開キーとして Ctrl+X A を使用する。
- fzf があれば Ctrl+R、fzf と ghq があれば Ctrl+U を設定する。不在なら標準履歴検索・行削除を残す。
- Ctrl+U を検索へ割り当てる場合、元の `unix-line-discard`（カーソルから行頭まで削除）は **Ctrl+X Ctrl+U** へ移す。
- この場合のみ Readline の `bind-tty-special-chars` を off にする。on のままだと、端末の kill 文字が Ctrl+U のとき初回プロンプトでキー設定が上書きされる。端末由来の特殊文字設定を自動反映せず、Readline の設定を使うため、独自の stty 特殊文字を使う人は確認が必要。
- 非対話 Bash は既存の早期 return のまま。セットアップ・依存パッケージ追加・実環境への適用は行わない。
- fzf は1行単位で選択する。複数行コマンドの一括復元や改行を含むリポジトリ名は対象外。

## 検証

```sh
bash -n dot_bashrc
python3 tests/test_bash_shell.py
```

Linux、Bash 5.3.15 で PTY を使用し9テスト成功。HOME/PATH/INPUTRC/履歴を隔離し、fzf/ghq はテスト用コマンドに置換する。
実際の Readline に Space、Enter、Ctrl+R、Ctrl+U、Ctrl+X Ctrl+U、カーソル移動を送信するので、関数の直接呼び出しだけでは検出できない初回キー上書きも検証する。
abbr 3件・展開済み履歴・引数非展開・途中カーソル・検索 query・履歴の非即時実行・記号付きパスへの即時移動・キャンセル・空選択・ghq/移動失敗・依存不在・既存 alias・非対話シェル・日本語入力と履歴カーソルを確認する。

未実施: 実際の個人履歴/ghq リポジトリを使う操作、chezmoi apply、Home Manager/Nix の適用、macOS/Bash 3.2、vi モードでの新機能、zsh/fish の既存不具合修正。
`docs` と `tests` は chezmoi の配置対象外。

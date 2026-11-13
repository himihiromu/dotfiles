# OBS設定をchezmoiで管理する

確認日: 2026-11-13。Linuxデスクトップのみ配布。
Nix/OBS GUIの設定は [Nix側手順](https://github.com/himihiromu/my-nix-package-control/blob/main/docs/obs-recording.md) を参照。

## 現在の状態

実際にOBS 32系が生成した `global.ini` を取り込み、ホームへの絶対パスのみテンプレート化した。
OBSの書込可能な通常ファイルとして配置する。設定内容・ファイル形式は創作していない。

既存プロファイル `無題/basic.ini` は名前だけで、シーンは映像ソース未設定だった。
録画プロファイル・エンコーダー・ゲームシーンはGUIで生成してから取り込む。
その作業が完了するまではMKV/AV1/60fps/300秒の設定は反映されない。
`global.ini` だけのapplyで録画環境の準備が完了したとは扱わない。

## 除外

`.chezmoiignore` と `.gitignore` で以下を除外する。

- `plugin_config/` 全体: `obs-websocket/config.json` のパスワード・認証設定、
  browserのCookie/ストレージ、配信サービス情報を含み得る。
- `plugin_manager/`、ログ、profiler_data、クラッシュ、cache、updates、一時ファイルとbackup。
- プロファイルの `service.json`（配信認証）、`user.ini`（UI位置・端末ローカルの選択状態）。

Git側は `global.ini`、`basic/profiles/*/{basic.ini,recordEncoder.json}`、
`basic/scenes/*.json` とそのテンプレートだけを許可する。
新しいOBSバージョンで設定ファイルが増えた場合、内容を確認してから個別に許可する。
ignoreは既に追跡済みのファイルには効かず、`git add -f` で迂回できるので、秘密検査は別に行う。

## GUIで変更した設定を取り込む

OBSと録画・リプレイを終了してから作業する。同時にapplyするとOBS終了時に上書きされ得る。
以下では実際のsourceを明示する。既定sourceは別の `~/.local/share/chezmoi` だったため、
`chezmoi source-path` を確認し、レビューしたブランチのソースを明示して使う。

```sh
cd ~/ghq/github.com/himihiromu/dotfiles
obs_config="${XDG_CONFIG_HOME:-$HOME/.config}/obs-studio"
obs_profile="$obs_config/basic/profiles/GameRecording"
obs_scene="$obs_config/basic/scenes/GameRecording.json"

# GUIで生成されたことを確認。実際のプロファイル/シーン名に合わせる。
ls "$obs_profile" "$obs_scene"
python3 scripts/check-obs-config.py \
  "$obs_config/global.ini" "$obs_profile/basic.ini" \
  "$obs_profile/recordEncoder.json" "$obs_scene"
```

`recordEncoder.json` がない場合は、詳細モードで録画エンコーダーを選択・保存・終了したか確認する。
存在しないファイルを雛形で補わない。エンコーダー保存先が変わった場合はOBS実出力を調査する。

検査がNGの場合は値をログやチャットに貼らず、ファイル内で確認する。
Portalソースの `restore_token` も端末ローカルの権限情報として扱い、共有しない。
必要ならOBS終了中にローカルシーンのソース設定から `restore_token` の値だけを空文字にし、
再検査する（その端末でも次回はPortalで対象を再選択する）。
機器固有IDも共有前に確認し、復元先で再選択する。
ブラウザソースや独自スクリプトはURL・設定の中に認証がある場合があるため取り込まない。
検査は既知の機密フィールドと認証付きURLの検出に限る。目視レビューも必須。

検査が成功した明示的なファイルだけを `chezmoi add` する。

```sh
chezmoi -S "$PWD" add --mode=file --secrets=error \
  "$obs_profile/basic.ini" "$obs_profile/recordEncoder.json" "$obs_scene"
chezmoi -S "$PWD" add --mode=file --secrets=error --template --autotemplate \
  "$obs_config/global.ini"
```

保存先を別ユーザーでも再現するため、プロファイルの `basic.ini` をテンプレートにする。
`chezmoi -S "$PWD" add --mode=file --template --autotemplate "$obs_profile/basic.ini"` の後、
生成された `.tmpl` のパス部分を確認する。必要なら保存先を
`{{ .chezmoi.homeDir }}/Videos/Recordings` とする。
**autotemplateは `true` などを `.is_desktop` へ置換する場合もある**ため、
パス以外の意図しない変換を元のリテラルへ戻す。JSON内のパスのテンプレート化では
`{{ joinPath .chezmoi.homeDir "..." | toJson }}` などでJSON文字列のエスケープも維持する。

```sh
python3 scripts/check-obs-config.py \
  dot_config/obs-studio/global.ini.tmpl \
  dot_config/obs-studio/basic/profiles/GameRecording/basic.ini.tmpl \
  dot_config/obs-studio/basic/profiles/GameRecording/recordEncoder.json \
  dot_config/obs-studio/basic/scenes/GameRecording.json
chezmoi -S "$PWD" diff ~/.config/obs-studio
# 新規ファイルはgit diffだけでは見えないため、ファイル本体も確認する。
git status --short
git diff -- dot_config/obs-studio .chezmoiignore .gitignore
# 機密がないことを確認してから対象を限定してステージする。
git add -- dot_config/obs-studio .chezmoiignore .gitignore
# この差分には新規ファイルも含まれる。認証情報や端末固有値がないか確認。
git diff --cached -- dot_config/obs-studio .chezmoiignore .gitignore
# レビュー完了後、ユーザー自身でコミットする。
```

`chezmoi add ~/.config/obs-studio` のような全体再帰取り込みは使わない。
`--mode=symlink`、`symlink_`、Home Managerの `xdg.configFile` との二重管理もしない。

## 別環境で復元する

1. Nix側のOBS/Portal/PipeWire/VAAPI構成を適用してから、OBSを終了する。
2. ローカルのOBS設定を必要に応じて権限を制限した場所へバックアップする。
3. 以下でOBS設定だけの差分を確認してapplyする。
   リポジトリ全体の初期化は既存のOS設定スクリプトを実行し得るため、ここでは対象を限定する。

   ```sh
   cd ~/ghq/github.com/himihiromu/dotfiles
   mkdir -p ~/Videos/Recordings
   chezmoi -S "$PWD" diff ~/.config/obs-studio
   chezmoi -S "$PWD" apply --parent-dirs --exclude=scripts --mode=file ~/.config/obs-studio
   find ~/.config/obs-studio -type l -print
   test -f ~/.config/obs-studio/global.ini
   test ! -L ~/.config/obs-studio/global.ini
   test -w ~/.config/obs-studio/global.ini
   ```

4. OBS起動後、復元したプロファイルとシーンコレクションを選択する。
   `user.ini` はローカルなので自動選択されるとは限らない。
   GPUデバイス、ゲームのPortal選択、マイク、アプリ音声を再選択する。
5. OBS標準WebSocketのパスワードは復元しない。GUIで端末ごとに認証を設定・保存し、
   ファイル権限を600にする（Nix側手順参照）。`obs-control status` を確認する。
6. OBSで設定変更・終了後に書き換えられることと、ゲームだけの短いテスト録画を確認する。

chezmoiは設定の履歴を保持する。OBSを更新した際は起動後の設定差分を確認する。
古いプロファイルの上書き適用で新しい設定が戻る場合があるので、起動中にapplyしない。
録画・リプレイ動画自体はdotfilesに含めない。

## 出典と検証範囲

2026-11-13の依頼、ローカルでOBSが生成した設定、固定nixpkgsのOBS 32.2.2を参照。
[OBS側の構成・一次資料リンクと実機チェックリスト](https://github.com/himihiromu/my-nix-package-control/blob/main/docs/obs-recording.md) を参照。
実ファイルに対するapply・ゲームキャプチャ・AV1エンコード・別端末復元は未実施。

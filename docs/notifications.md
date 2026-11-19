# デスクトップ通知

Nix側でSwayNotificationCenter（swaync）をインストールし、利用者設定は
chezmoiの `dot_config/swaync/config.json` から配置する。
Linuxデスクトップ環境だけを対象にする。

通常・低優先度・緊急のポップアップ表示時間を3秒、消える際のアニメーションを
200ミリ秒に設定する。自動非表示になった通知は通知センターに残り、
Waybarの通知件数をクリックして確認できる。
アプリがtransient（履歴に残さない）として送った通知は、この保持の対象外。

```sh
chezmoi apply --parent-dirs --exclude scripts ~/.config/swaync
swaync-client --reload-config
```

swaync 0.12.6は起動時に選んだ設定ファイルの参照先を保持する。
初めてユーザー設定を追加した場合、`--reload-config` だけでは標準設定から
切り替わらないため、次回ログイン時に有効になる。即時反映にはswayncの再起動が
必要だが、再起動すると現在の通知履歴が失われる。
すでにユーザー設定を読んで起動している場合は、上記の再読み込みで反映できる。

初回追加時に履歴を維持しつつ緊急通知の無期限表示だけを止めるには、
現在のプロセスに一時設定を適用できる。

```sh
busctl --user call org.erikreider.swaync /org/erikreider/swaync/cc \
  org.erikreider.swaync.cc ChangeConfigValue svbs timeout-critical i 3 false ''
```

この一時設定は再読み込みで解除される。また、このAPIは変更のたびに元の設定を
読み直すため、複数項目を順番に変更しても最後の項目しか維持されない。

設定変更前から残っているポップアップだけを隠すには、次を実行する。
履歴も削除する `--close-all` とは動作が異なる。

```sh
swaync-client --hide-all
```

## 表示時間の例外

swaync 0.12.6では、マウスが通知上にある間はタイマーが止まり、離すと再開する。
また、アプリが正の表示時間を明示すると、その時間が設定より優先される。
この設定の3秒は、アプリが表示時間を省略した場合や0を指定した場合に適用される。
全アプリの表示時間を強制的に上書きする設定は、このバージョンにはない。

## 確認日と出典

- 2026-11-20: 右上の通知を2〜3秒で消し、Waybarから履歴を確認したいという依頼に対応。
- [SwayNC 0.12.6の標準設定](https://github.com/ErikReider/SwayNotificationCenter/blob/v0.12.6/src/config.json.in): 通常10秒・低優先度5秒・緊急0（自動非表示なし）。
- [表示時間とマウス操作の実装](https://github.com/ErikReider/SwayNotificationCenter/blob/v0.12.6/src/notification/notification.vala)
- [設定の再読み込みと一時変更の実装](https://github.com/ErikReider/SwayNotificationCenter/blob/v0.12.6/src/configModel/configModel.vala)
- [表示時間の上書き機能の要望 #257](https://github.com/ErikReider/SwayNotificationCenter/issues/257)

#!/usr/bin/env bash
# bash 設定 (dot_bashrc) の観測テスト。
#
# リポジトリの dot_bashrc を --rcfile で読み込んだ対話 bash を起動し、
# alias 定義と readline のキーバインド (bind -X) を観測する。
# キーバインドは readline を持つ bash ビルドでしか観測できないため、
# bind が使える bash を実行時に探して使う。HOME は毎回隔離する。

TEST_FILE_NAME="bash_shell_test.sh"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

DOT_BASHRC="$REPO_ROOT/dot_bashrc"
ISO_BASE="$(mktemp -d "${TMPDIR:-/tmp}/bash-shell-test-XXXXXXXX")"
mkdir -p "$ISO_BASE/home"
mkdir -p "$ISO_BASE/stubbin"
cleanup_env() { rm -rf "$ISO_BASE"; }
trap cleanup_env EXIT

cat > "$ISO_BASE/stubbin/fzf" <<'EOF'
#!/usr/bin/env bash
if [ -n "${FZF_SELECTION:-}" ]; then
  cat >/dev/null
  printf '%s\n' "$FZF_SELECTION"
else
  head -n 1
fi
EOF
cat > "$ISO_BASE/stubbin/ghq" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$GHQ_REPOSITORY"
EOF
cat > "$ISO_BASE/stubbin/zoxide" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$ZOXIDE_LOG"
printf 'z() { :; }\n'
EOF
chmod +x "$ISO_BASE/stubbin/fzf" "$ISO_BASE/stubbin/ghq" "$ISO_BASE/stubbin/zoxide"

# bind (readline) を持つ bash を探す。環境によってはビルド方針のため
# readline 非搭載の bash が PATH 上に来る
find_bash_with_bind() {
  local candidate
  for candidate in bash /bin/bash /usr/bin/bash /run/current-system/sw/bin/bash; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -i -c 'type -t bind >/dev/null' >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

BASH_WITH_BIND="$(find_bash_with_bind || true)"
ANY_BASH="$(command -v bash)"

# 対話 bash で dot_bashrc を読み込んだ状態で code を実行する
run_ibash() { # $1=HOME $2=bash へ渡すコード
  env HOME="$1" PATH="$ISO_BASE/stubbin:$PATH" "$ANY_BASH" --noprofile --rcfile "$DOT_BASHRC" -i -c "$2" 2>/dev/null
}

# ---- テスト ---------------------------------------------------------------

bashrc_has_valid_syntax() {
  if bash -n "$DOT_BASHRC" 2>/dev/null; then
    pass "dot_bashrc が構文的に妥当である"
  else
    fail "dot_bashrc が構文的に妥当である" "bash -n が失敗した"
  fi
}

interactive_bash_sources_bashrc_successfully() {
  local out rc
  out="$(run_ibash "$ISO_BASE/home" 'true')"
  rc=$?
  assert_exit_zero "対話 bash が dot_bashrc を読み込んで起動する" "$rc" "$out"
}

non_interactive_shell_stops_at_interactive_guard() {
  local out
  out="$(env HOME="$ISO_BASE/home" "$ANY_BASH" -c "source '$DOT_BASHRC' && echo GUARD_OK" 2>/dev/null)"
  assert_contains "非対話シェルでは対話判定以降を実行しない" "GUARD_OK" "$out"
}

bash_abbreviations_match_zsh_and_fish_values() {
  local la_out ll_out lal_out
  la_out="$(run_ibash "$ISO_BASE/home" 'alias la' || true)"
  ll_out="$(run_ibash "$ISO_BASE/home" 'alias ll' || true)"
  lal_out="$(run_ibash "$ISO_BASE/home" 'alias lal' || true)"
  assert_eq "la が zsh・fish と同じ値を持つ" "alias la='ls -a'" "$la_out"
  assert_eq "ll が zsh・fish と同じ値を持つ" "alias ll='ls -l'" "$ll_out"
  assert_eq "lal が zsh・fish と同じ値を持つ" "alias lal='ls -al'" "$lal_out"
}

existing_ls_alias_l_is_kept() {
  local l_out
  l_out="$(run_ibash "$ISO_BASE/home" 'alias l' || true)"
  assert_eq "既存の l エイリアスが維持される" "alias l='ls -CF'" "$l_out"
}

# bind -X の出力から指定キーに割り当てられたコマンドを取り出す。
# 割り当てが関数名のときはその関数本体を返す (コマンドをインラインで書いた
# 場合と関数にした場合のどちらの実装でも観測できるようにする)
bound_widget_text() { # $1=HOME $2=bash のキー表記 (例: \C-r)
  env BIND_KEY="$2" HOME="$1" "$BASH_WITH_BIND" --noprofile --rcfile "$DOT_BASHRC" -i -c '
    line=$(bind -X | grep -F -- "\"$BIND_KEY\"" | head -n 1)
    cmd=${line#*\" \"}
    cmd=${cmd%\"}
    if declare -f "$cmd" >/dev/null 2>&1; then declare -f "$cmd"; else printf "%s\n" "$cmd"; fi
  ' 2>/dev/null
}

ctrl_r_binds_fzf_history_search() {
  if [ -z "$BASH_WITH_BIND" ]; then
    skip_test "Ctrl+R の履歴検索キーバインド" "readline (bind) を持つ bash が無い環境"
    return 0
  fi
  local text
  text="$(bound_widget_text "$ISO_BASE/home" '\C-r')"
  assert_contains "Ctrl+R に widget が割り当てられている" "\\C-r" "$(env HOME="$ISO_BASE/home" "$BASH_WITH_BIND" --noprofile --rcfile "$DOT_BASHRC" -i -c 'bind -X' 2>/dev/null)"
  assert_contains "Ctrl+R の widget が fzf を使う" "fzf" "$text"
  case "$text" in
    *history*|*"fc "*)
      pass "Ctrl+R の widget が履歴を対象にする"
      ;;
    *)
      fail "Ctrl+R の widget が履歴を対象にする" "widget=[${text:0:200}]"
      ;;
  esac
}

ctrl_u_binds_ghq_repository_search() {
  if [ -z "$BASH_WITH_BIND" ]; then
    skip_test "Ctrl+U の ghq リポジトリ検索キーバインド" "readline (bind) を持つ bash が無い環境"
    return 0
  fi
  local text
  text="$(bound_widget_text "$ISO_BASE/home" '\C-u')"
  assert_contains "Ctrl+U の widget が ghq を使う" "ghq" "$text"
  assert_contains "Ctrl+U の widget が fzf を使う" "fzf" "$text"
  assert_contains "Ctrl+U の widget が選択先へ cd する" "cd" "$text"
}

zoxide_is_initialized_for_bash() {
  local log="$ISO_BASE/zoxide.log" out
  out="$(env HOME="$ISO_BASE/home" PATH="$ISO_BASE/stubbin:$PATH" ZOXIDE_LOG="$log" \
    "$ANY_BASH" --noprofile --rcfile "$DOT_BASHRC" -i -c 'type z >/dev/null && echo ZOXIDE_READY' 2>/dev/null)"
  assert_contains "対話 bash が zoxide init bash を評価する" "init bash" "$(cat "$log")"
  assert_contains "対話 bash で zoxide の z 関数が利用可能になる" "ZOXIDE_READY" "$out"
}

fzf_history_widget_loads_selected_command() {
  local out
  out="$(env HOME="$ISO_BASE/home" PATH="$ISO_BASE/stubbin:$PATH" FZF_SELECTION='git status' \
    "$ANY_BASH" --noprofile --rcfile "$DOT_BASHRC" -i -c '__fzf_history_search; printf "LINE=%s POINT=%s\\n" "$READLINE_LINE" "$READLINE_POINT"' 2>/dev/null)"
  assert_contains "履歴検索 widget が fzf の選択を入力行へ設定する" "LINE=git status POINT=10" "$out"
}

ghq_widget_changes_to_selected_repository() {
  local selected="$ISO_BASE/repository" out
  mkdir -p "$selected"
  out="$(env HOME="$ISO_BASE/home" PATH="$ISO_BASE/stubbin:$PATH" GHQ_REPOSITORY="$selected" \
    "$ANY_BASH" --noprofile --rcfile "$DOT_BASHRC" -i -c '__fzf_ghq_search; printf "PWD=%s\\n" "$PWD"' 2>/dev/null)"
  assert_contains "ghq 検索 widget が選択したリポジトリへ移動する" "PWD=$selected" "$out"
}

bashrc_sources_single_user_nix_profile_when_daemon_profile_is_absent() {
  if [ -e /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]; then
    skip_test "bash が nix プロファイルを読み込む" "マルチユーザ nix 環境では単一ユーザ経路を観測できない"
    return 0
  fi
  local m3_home out
  m3_home="$ISO_BASE/m3home"
  mkdir -p "$m3_home/.nix-profile/etc/profile.d" "$m3_home/.nix-profile/bin"
  cat > "$m3_home/.nix-profile/etc/profile.d/nix.sh" <<'EOF'
export NIX_PROFILE_SOURCED_MARKER=yes
EOF
  out="$(run_ibash "$m3_home" 'printf "MARKER=%s\n" "${NIX_PROFILE_SOURCED_MARKER:-unset}"')"
  assert_eq "対話 bash が単一ユーザ nix プロファイルを読み込む" "MARKER=yes" "$out"
}

bashrc_starts_even_without_any_nix_profile() {
  local out rc
  mkdir -p "$ISO_BASE/no-nix-home"
  out="$(run_ibash "$ISO_BASE/no-nix-home" 'true')"
  rc=$?
  assert_exit_zero "nix プロファイルが無い環境でも dot_bashrc の読み込みが失敗しない" "$rc" "$out"
}

bashrc_has_valid_syntax
interactive_bash_sources_bashrc_successfully
non_interactive_shell_stops_at_interactive_guard
bash_abbreviations_match_zsh_and_fish_values
existing_ls_alias_l_is_kept
ctrl_r_binds_fzf_history_search
ctrl_u_binds_ghq_repository_search
zoxide_is_initialized_for_bash
fzf_history_widget_loads_selected_command
ghq_widget_changes_to_selected_repository
bashrc_sources_single_user_nix_profile_when_daemon_profile_is_absent
bashrc_starts_even_without_any_nix_profile

finish

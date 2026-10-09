# dotfiles テスト共通ライブラリ。
#
# 各 *_test.sh は本ファイルを source し、assert_* で観測可能な契約を検査する。
# テストに必要な外部ツール (mise / readline 付き bash / chezmoi) が用意できない
# 環境では該当テストを SKIP にする。SKIP は PASS/FAIL のどちらにも数えず、
# 実行環境の能力の限界として報告する。

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TESTS_DIR/.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '  PASS %s\n' "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '  FAIL %s\n' "$1"
  printf '       %s\n' "$2"
}

skip_test() {
  SKIP_COUNT=$((SKIP_COUNT + 1))
  printf '  SKIP %s (%s)\n' "$1" "$2"
}

assert_eq() { # 説明 期待値 実測値
  if [ "$2" = "$3" ]; then
    pass "$1"
  else
    fail "$1" "expected=[$2] actual=[$3]"
  fi
}

assert_contains() { # 説明 部分文字列 対象文字列
  case "$3" in
    *"$2"*) pass "$1" ;;
    *) fail "$1" "[$3] に [$2] が含まれない" ;;
  esac
}

assert_not_contains() { # 説明 禁止値 抽出済み観測単位
  case "$3" in
    *"$2"*) fail "$1" "[$3] に禁止値 [$2] が含まれる" ;;
    *) pass "$1" ;;
  esac
}

assert_has_line() { # 説明 行(完全一致) 複数行の対象
  if printf '%s\n' "$3" | grep -Fxq -- "$2"; then
    pass "$1"
  else
    fail "$1" "行 [$2] が存在しない。対象=[$(printf '%s' "$3" | tr '\n' '|' | head -c 300)]"
  fi
}

assert_exit_zero() { # 説明 終了コード 出力
  if [ "$2" -eq 0 ]; then
    pass "$1"
  else
    fail "$1" "exit=$2 out=[$(printf '%s' "$3" | head -c 400)]"
  fi
}

assert_exit_nonzero() { # 説明 終了コード 出力
  if [ "$2" -ne 0 ]; then
    pass "$1"
  else
    fail "$1" "失敗が期待される入力で exit=0 になった out=[$(printf '%s' "$3" | head -c 400)]"
  fi
}

finish() { # テストファイルの末尾で呼ぶ。FAIL があれば非ゼロで返る
  printf '%s: pass=%d fail=%d skip=%d\n' \
    "${TEST_FILE_NAME:-$(basename "${BASH_SOURCE[1]}")}" "$PASS_COUNT" "$FAIL_COUNT" "$SKIP_COUNT"
  [ "$FAIL_COUNT" -eq 0 ]
}

# ---- コマンドスタブ ------------------------------------------------------

# 引数と実行時の cwd を記録するコマンドスタブを bin_dir/name に作る
write_recording_stub() { # $1=bin_dir $2=name $3=log_path $4=exit_code (省略時 0)
  local exit_code="${4:-0}"
  cat > "$1/$2" <<EOF
#!/usr/bin/env bash
printf 'CMD=$2\n' >> '$3'
printf 'ARGS=%s\n' "\$*" >> '$3'
printf 'CWD=%s\n' "\$PWD" >> '$3'
exit $exit_code
EOF
  chmod +x "$1/$2"
}

# sudo スタブ: 呼び出しを記録してから残りのコマンドを exec する。
# sudo 経由の内部コマンド (nix / nixos-rebuild) も同じログで観測できる
write_sudo_stub() { # $1=bin_dir $2=log_path
  cat > "$1/sudo" <<EOF
#!/usr/bin/env bash
printf 'CMD=sudo\n' >> '$2'
printf 'ARGS=%s\n' "\$*" >> '$2'
printf 'CWD=%s\n' "\$PWD" >> '$2'
exec "\$@"
EOF
  chmod +x "$1/sudo"
}

stub_args_all() { # $1=log $2=cmd → そのコマンドの全呼び出しの ARGS 値
  local line current_cmd=""
  while IFS= read -r line; do
    case "$line" in
      CMD=*) current_cmd="${line#CMD=}" ;;
      ARGS=*) [ "$current_cmd" = "$2" ] && printf '%s\n' "${line#ARGS=}" ;;
    esac
  done < "$1"
  return 0
}

stub_args_last() { # $1=log $2=cmd → 最後の呼び出しの ARGS 値
  stub_args_all "$1" "$2" | tail -n 1
}

stub_cwd_last() { # $1=log $2=cmd → 最後の呼び出し時の cwd
  local line current_cmd="" last_cwd=""
  while IFS= read -r line; do
    case "$line" in
      CMD=*) current_cmd="${line#CMD=}" ;;
      CWD=*) [ "$current_cmd" = "$2" ] && last_cwd="${line#CWD=}" ;;
    esac
  done < "$1"
  printf '%s' "$last_cwd"
}

stub_call_count() { # $1=log $2=cmd
  stub_args_all "$1" "$2" | wc -l | tr -d ' '
}

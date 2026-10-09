#!/usr/bin/env bash
# mise グローバルタスクの観測テスト。
#
# 実際の mise にリポジトリの dot_config/mise/config.toml を読み込ませてタスクを
# 実行し、タスクから呼ばれる nix 系コマンドを PATH 先頭の記録用スタブで観測する。
# HOME は隔離し、ghq 管理下のリポジトリ配置だけを実環境と同じ構造で用意する
# (order.md の「対象リポジトリは ~/ghq/github.com/himihiromu/my-nix-package-control」)。
# すべてのシナリオは対象リポジトリ外のカレントディレクトリから実行する。

TEST_FILE_NAME="mise_tasks_test.sh"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

# ---- 実行環境の能力確認 ---------------------------------------------------

MISE_MODE=""
MISE_BIN="$(command -v mise 2>/dev/null || true)"
REAL_NIX="$(command -v nix 2>/dev/null || true)"
if [ -n "$MISE_BIN" ]; then
  MISE_MODE="local"
elif [ -n "$REAL_NIX" ]; then
  MISE_MODE="nix-shell"
else
  skip_test "mise タスク系テスト全体" "mise も nix も利用できない環境"
  finish
  exit $?
fi

if [ ! -f "$REPO_ROOT/dot_config/mise/config.toml" ]; then
  fail "setup" "dot_config/mise/config.toml が存在しないため mise タスク系のテストを実行できない (未実装)"
  finish
  exit $?
fi

# ---- 共有しないテスト環境の用意 --------------------------------------------

REPO_PATH_IN_HOME="ghq/github.com/himihiromu/my-nix-package-control"
TEST_HOME=""
STUB_LOG=""

cleanup_env() {
  if [ -n "$TEST_HOME" ] && [ -d "$TEST_HOME" ]; then
    rm -rf "$TEST_HOME"
  fi
}
trap cleanup_env EXIT

begin_env() {
  cleanup_env
  TEST_HOME="$(mktemp -d "${TMPDIR:-/tmp}/mise-tasks-test-XXXXXXXX")"
  mkdir -p \
    "$TEST_HOME/.config/mise" \
    "$TEST_HOME/$REPO_PATH_IN_HOME" \
    "$TEST_HOME/work" \
    "$TEST_HOME/stubbin"
  cp "$REPO_ROOT/dot_config/mise/config.toml" "$TEST_HOME/.config/mise/config.toml"
  STUB_LOG="$TEST_HOME/stub.log"
  : > "$STUB_LOG"
  local s
  for s in nix nix-store nixos-rebuild; do
    write_recording_stub "$TEST_HOME/stubbin" "$s" "$STUB_LOG"
  done
  write_sudo_stub "$TEST_HOME/stubbin" "$STUB_LOG"
}

# 任意のカレントディレクトリから mise を実行する (開発環境に mise が無ければ
# nix shell で取得した mise を使う)
run_mise() { # $1=cwd 残り=mise への引数
  local cwd="$1"
  shift
  local cmd
  if [ "$MISE_MODE" = "local" ]; then
    cmd=(env HOME="$TEST_HOME" PATH="$TEST_HOME/stubbin:$PATH" "$MISE_BIN")
  else
    cmd=(env HOME="$TEST_HOME" PATH="$TEST_HOME/stubbin:$PATH" "$REAL_NIX" shell nixpkgs#mise -c mise)
  fi
  MISE_OUT="$(cd "$cwd" && "${cmd[@]}" "$@" 2>&1)"
  MISE_RC=$?
}

MISE_RC=0
MISE_OUT=""

# ---- テスト ---------------------------------------------------------------

config_loads_into_mise() {
  begin_env
  run_mise "$TEST_HOME/work" tasks ls
  assert_exit_zero "dot_config/mise/config.toml が mise に読み込まれる" "$MISE_RC" "$MISE_OUT"
  local task_name
  for task_name in develop home-manager nis-darwin nixos nix; do
    assert_contains "タスク $task_name が mise から見えている" "$task_name" "$MISE_OUT"
  done
}

develop_launches_nix_develop_for_named_environment() {
  begin_env
  run_mise "$TEST_HOME/work" develop rust
  assert_exit_zero "mise develop rust が成功する" "$MISE_RC" "$MISE_OUT"
  assert_eq "ghq 管理下リポジトリの指定環境の nix develop が起動する" \
    "develop $TEST_HOME/$REPO_PATH_IN_HOME#rust" \
    "$(stub_args_last "$STUB_LOG" nix)"
}

develop_without_environment_name_does_not_start_nix() {
  begin_env
  run_mise "$TEST_HOME/work" develop
  assert_exit_nonzero "環境名が無い develop は失敗する" "$MISE_RC" "$MISE_OUT"
  assert_eq "環境名が空の属性で nix develop を起動しない" \
    "" \
    "$(stub_args_all "$STUB_LOG" nix)"
}

home_manager_switch_uses_local_repository_from_any_directory() {
  begin_env
  run_mise "$TEST_HOME/work" home-manager switch
  assert_exit_zero "mise home-manager switch が成功する" "$MISE_RC" "$MISE_OUT"
  assert_eq "既存コマンドと同じ形でローカルリポジトリの myHomeConfig を switch する" \
    "run nixpkgs#home-manager -- switch --flake $TEST_HOME/$REPO_PATH_IN_HOME#myHomeConfig --show-trace --override-input local-options path:$TEST_HOME/.config/nix/local-input/default.nix" \
    "$(stub_args_last "$STUB_LOG" nix)"
}

home_manager_switch_propagates_nix_failure() {
  begin_env
  write_recording_stub "$TEST_HOME/stubbin" nix "$STUB_LOG" 23
  run_mise "$TEST_HOME/work" home-manager switch
  assert_exit_nonzero "nix が失敗した mise home-manager switch も失敗する" "$MISE_RC" "$MISE_OUT"
  assert_eq "失敗時も home-manager が nix を実行する" "1" "$(stub_call_count "$STUB_LOG" nix)"
}

nis_darwin_switch_matches_documented_command() {
  begin_env
  run_mise "$TEST_HOME/work" nis-darwin switch
  assert_exit_zero "mise nis-darwin switch が成功する" "$MISE_RC" "$MISE_OUT"
  assert_eq "sudo 経由で nix-darwin が実行される" \
    "nix run nix-darwin -- switch --flake $TEST_HOME/$REPO_PATH_IN_HOME#mac-config --override-input local-options path:$TEST_HOME/.config/nix/local-input/default.nix" \
    "$(stub_args_last "$STUB_LOG" sudo)"
  assert_eq "sudo の内側で nix run nix-darwin が同じ引数で実行される" \
    "run nix-darwin -- switch --flake $TEST_HOME/$REPO_PATH_IN_HOME#mac-config --override-input local-options path:$TEST_HOME/.config/nix/local-input/default.nix" \
    "$(stub_args_last "$STUB_LOG" nix)"
}

nis_darwin_switch_propagates_nix_failure() {
  begin_env
  write_recording_stub "$TEST_HOME/stubbin" nix "$STUB_LOG" 23
  run_mise "$TEST_HOME/work" nis-darwin switch
  assert_exit_nonzero "sudo 経由の nix が失敗した mise nis-darwin switch も失敗する" "$MISE_RC" "$MISE_OUT"
  assert_eq "失敗時も nis-darwin が sudo を実行する" "1" "$(stub_call_count "$STUB_LOG" sudo)"
  assert_eq "sudo の内側で nix が失敗終了する" "1" "$(stub_call_count "$STUB_LOG" nix)"
}

nixos_switch_targets_local_repository() {
  begin_env
  run_mise "$TEST_HOME/work" nixos switch
  assert_exit_zero "mise nixos switch が成功する" "$MISE_RC" "$MISE_OUT"
  local sudo_args rebuild_args flake_value
  sudo_args="$(stub_args_last "$STUB_LOG" sudo)"
  rebuild_args="$(stub_args_last "$STUB_LOG" nixos-rebuild)"
  assert_contains "nixos-rebuild switch が sudo 経由で実行される" "nixos-rebuild switch" "$sudo_args"
  assert_eq "nixos-rebuild の先頭引数は switch" "switch" "${rebuild_args%% *}"
  flake_value="$(printf '%s\n' "$rebuild_args" | sed -n 's/^switch --flake //p')"
  case "$flake_value" in
    "$TEST_HOME/$REPO_PATH_IN_HOME"|"$TEST_HOME/$REPO_PATH_IN_HOME"#*)
      pass "ローカルリポジトリの flake を対象に switch する"
      ;;
    *)
      fail "ローカルリポジトリの flake を対象に switch する" "--flake の値=[$flake_value]"
      ;;
  esac
}

nixos_switch_propagates_rebuild_failure() {
  begin_env
  write_recording_stub "$TEST_HOME/stubbin" nixos-rebuild "$STUB_LOG" 23
  run_mise "$TEST_HOME/work" nixos switch
  assert_exit_nonzero "nixos-rebuild が失敗した mise nixos switch も失敗する" "$MISE_RC" "$MISE_OUT"
  assert_eq "失敗時も nixos switch が sudo を実行する" "1" "$(stub_call_count "$STUB_LOG" sudo)"
  assert_eq "sudo の内側で nixos-rebuild が失敗終了する" "1" "$(stub_call_count "$STUB_LOG" nixos-rebuild)"
}

nix_update_runs_flake_update_for_local_repository() {
  begin_env
  run_mise "$TEST_HOME/work" nix update
  assert_exit_zero "mise nix update が成功する" "$MISE_RC" "$MISE_OUT"
  local nix_args nix_cwd
  nix_args="$(stub_args_last "$STUB_LOG" nix)"
  nix_cwd="$(stub_cwd_last "$STUB_LOG" nix)"
  if [ "$nix_args" = "flake update $TEST_HOME/$REPO_PATH_IN_HOME" ] \
    || { [ "$nix_args" = "flake update" ] && [ "$nix_cwd" = "$TEST_HOME/$REPO_PATH_IN_HOME" ]; }; then
    pass "ローカルリポジトリに対して nix flake update が実行される"
  else
    fail "ローカルリポジトリに対して nix flake update が実行される" \
      "args=[$nix_args] cwd=[$nix_cwd]"
  fi
}

nix_update_propagates_nix_failure() {
  begin_env
  write_recording_stub "$TEST_HOME/stubbin" nix "$STUB_LOG" 23
  run_mise "$TEST_HOME/work" nix update
  assert_exit_nonzero "nix flake update が失敗した mise nix update も失敗する" "$MISE_RC" "$MISE_OUT"
  assert_eq "失敗時も nix update が nix を実行する" "1" "$(stub_call_count "$STUB_LOG" nix)"
}

nix_gc_runs_nix_store_gc() {
  begin_env
  run_mise "$TEST_HOME/work" nix gc
  assert_exit_zero "mise nix gc が成功する" "$MISE_RC" "$MISE_OUT"
  assert_eq "nix-store --gc が実行される" "--gc" "$(stub_args_last "$STUB_LOG" nix-store)"
}

nix_gc_propagates_nix_store_failure() {
  begin_env
  write_recording_stub "$TEST_HOME/stubbin" nix-store "$STUB_LOG" 23
  run_mise "$TEST_HOME/work" nix gc
  assert_exit_nonzero "nix-store --gc が失敗した mise nix gc も失敗する" "$MISE_RC" "$MISE_OUT"
  assert_eq "失敗時も nix gc が nix-store を実行する" "1" "$(stub_call_count "$STUB_LOG" nix-store)"
}

nix_with_unknown_subcommand_runs_nothing() {
  begin_env
  run_mise "$TEST_HOME/work" nix foo
  assert_exit_nonzero "未定義のサブコマンドは失敗する" "$MISE_RC" "$MISE_OUT"
  assert_eq "nix-store は実行されない" "0" "$(stub_call_count "$STUB_LOG" nix-store)"
  assert_not_contains "nix flake update は実行されない" "flake update" "$(stub_args_all "$STUB_LOG" nix)"
  assert_not_contains "nix-store --gc は実行されない" "--gc" "$(stub_args_all "$STUB_LOG" nix)"
}

nix_without_subcommand_runs_nothing() {
  begin_env
  run_mise "$TEST_HOME/work" nix
  assert_exit_nonzero "サブコマンドが無い nix は失敗する" "$MISE_RC" "$MISE_OUT"
  assert_eq "nix-store は実行されない" "0" "$(stub_call_count "$STUB_LOG" nix-store)"
  assert_not_contains "nix flake update は実行されない" "flake update" "$(stub_args_all "$STUB_LOG" nix)"
  assert_not_contains "nix-store --gc は実行されない" "--gc" "$(stub_args_all "$STUB_LOG" nix)"
}

config_loads_into_mise
develop_launches_nix_develop_for_named_environment
develop_without_environment_name_does_not_start_nix
home_manager_switch_uses_local_repository_from_any_directory
home_manager_switch_propagates_nix_failure
nis_darwin_switch_matches_documented_command
nis_darwin_switch_propagates_nix_failure
nixos_switch_targets_local_repository
nixos_switch_propagates_rebuild_failure
nix_update_runs_flake_update_for_local_repository
nix_update_propagates_nix_failure
nix_gc_runs_nix_store_gc
nix_gc_propagates_nix_store_failure
nix_with_unknown_subcommand_runs_nothing
nix_without_subcommand_runs_nothing

finish

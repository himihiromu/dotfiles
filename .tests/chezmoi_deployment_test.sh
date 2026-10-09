#!/usr/bin/env bash
# chezmoi 配備契約 (.chezmoiignore) の観測テスト。
#
# chezmoi 本体を使って、テンプレートが評価できること、Windows 向け除外ブロックに
# mise 設定が含まれること、このマシン (Linux) の管理対象一覧に bash と mise の
# 設定が載ることを観測する。chezmoi が無い環境では SKIP する。

TEST_FILE_NAME="chezmoi_deployment_test.sh"
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

CHEZMOI="$(command -v chezmoi 2>/dev/null || true)"
IGNORE_FILE="$REPO_ROOT/.chezmoiignore"

windows_ignore_block() {
  # CR を除いて論理行だけを比較する (.chezmoiignore は CRLF 改行で管理されている)
  awk '
    index($0, "{{ if eq .chezmoi.os \"windows\" }}") == 1 { in_block = 1; next }
    in_block && index($0, "{{ end }}") == 1 { in_block = 0; next }
    in_block { print }
  ' "$IGNORE_FILE" | tr -d '\r'
}

# ---- テスト ---------------------------------------------------------------

chezmoi_ignore_template_evaluates() {
  if [ -z "$CHEZMOI" ]; then
    skip_test ".chezmoiignore のテンプレート評価" "chezmoi が無い環境"
    return 0
  fi
  local out rc
  out="$("$CHEZMOI" execute-template < "$IGNORE_FILE" 2>&1)"
  rc=$?
  assert_exit_zero ".chezmoiignore が chezmoi テンプレートとして評価できる" "$rc" "$out"
}

windows_block_excludes_mise_config() {
  if [ ! -f "$IGNORE_FILE" ]; then
    fail "windows 除外ブロックに .config/mise がある" ".chezmoiignore が存在しない"
    return 0
  fi
  assert_has_line "windows 除外ブロックに .config/mise がある" ".config/mise" "$(windows_ignore_block)"
}

managed_targets_include_bash_and_mise_configs() {
  if [ -z "$CHEZMOI" ]; then
    skip_test "管理対象一覧に bash と mise の設定がある" "chezmoi が無い環境"
    return 0
  fi
  local managed
  managed="$("$CHEZMOI" managed --source "$REPO_ROOT" 2>/dev/null)"
  assert_has_line ".bashrc が管理対象に含まれる" ".bashrc" "$managed"
  assert_has_line ".config/mise/config.toml が管理対象に含まれる" ".config/mise/config.toml" "$managed"
}

chezmoi_ignore_template_evaluates
windows_block_excludes_mise_config
managed_targets_include_bash_and_mise_configs

finish

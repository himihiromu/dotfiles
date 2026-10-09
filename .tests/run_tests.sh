#!/usr/bin/env bash
# dotfiles テストランナー。
#
# 使い方: .tests/run_tests.sh
#
# .tests/*_test.sh をそれぞれ独立した bash プロセスで実行し、
# 1 つでも FAIL があれば非ゼロで終了する。各テストファイルは自分の
# PASS/FAIL/SKIP を行単位で出力し、末尾に集計行を出す。

set -u

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

shopt -s nullglob
test_files=("$TESTS_DIR"/*_test.sh)
shopt -u nullglob

if [ "${#test_files[@]}" -eq 0 ]; then
  printf 'no test files found in %s\n' "$TESTS_DIR" >&2
  exit 1
fi

overall=0
for test_file in "${test_files[@]}"; do
  printf '== %s ==\n' "$(basename "$test_file")"
  if ! bash "$test_file"; then
    overall=1
  fi
  printf '\n'
done

if [ "$overall" -eq 0 ]; then
  printf 'RESULT: OK\n'
else
  printf 'RESULT: FAILURE\n'
fi
exit "$overall"

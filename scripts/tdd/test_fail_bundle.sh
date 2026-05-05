#!/bin/sh
set -eu

test -f Makefile
test -x scripts/test_all.sh

TMP_DIR="tmp"
FAIL_DIR="$TMP_DIR/fail"

rm -rf "$FAIL_DIR"
mkdir -p "$FAIL_DIR"

# Идея: добавить в test_all.sh поддержку FORCE_BAD_EXP=1, чтобы ломать expected (только для этого теста).
# Пока этого нет — тест будет красным, это и есть TDD.
FORCE_BAD_EXP=1 scripts/test_all.sh >/dev/null 2>&1 && {
  echo "ERROR: expected failure but test_all succeeded" >&2
  exit 1
}

# После реализации ожидаем, что появится хотя бы один fail bundle
test -d "$FAIL_DIR"
# Должен быть хотя бы один подкаталог
find "$FAIL_DIR" -mindepth 1 -maxdepth 1 -type d | grep -q .
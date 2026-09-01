#!/usr/bin/env bash
set -euo pipefail

REPO='https://github.com/dugushengyu/CMDO-Reproducibility.git'
BRANCH='codex/github-native-submission-20260901'
ROOT="$(mktemp -d "${TMPDIR:-/tmp}/CMDO_REVIEWER_E2E_XXXXXX")"

printf '%s\n' '============================================================'
printf '%s\n' ' CMDO FRESH-CLONE REVIEWER PORTABILITY TEST (macOS/Linux)'
printf '%s\n' '============================================================'
printf 'Clone target: %s\n' "$ROOT"

git clone --branch "$BRANCH" --single-branch "$REPO" "$ROOT"

MATLAB_BIN="${MATLAB_BIN:-matlab}"
if ! command -v "$MATLAB_BIN" >/dev/null 2>&1 && [[ ! -x "$MATLAB_BIN" ]]; then
  echo 'MATLAB not found. Put matlab on PATH or set MATLAB_BIN to the MATLAB executable.' >&2
  exit 2
fi

MATLAB_ROOT_ESCAPED=${ROOT//\'/\'\'}
"$MATLAB_BIN" -batch "cd('$MATLAB_ROOT_ESCAPED'); RUN_REVIEWER_END_TO_END('Strict',true,'RunStressReplay',true)"

if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  git -C "$ROOT" status --short
  echo 'Fresh clone became Git-dirty.' >&2
  exit 3
fi

printf '\n%s\n' '============================================================'
printf '%s\n' ' FRESH GITHUB CLONE + END-TO-END AUDIT: PASS'
printf '%s\n' ' Git clean: PASS'
printf '%s\n' '============================================================'
printf 'Clone retained for inspection: %s\n' "$ROOT"

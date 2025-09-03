#!/usr/bin/env bash
set -euo pipefail

# ===== config =====
SRC_DIR="source code"
SUMMARY_TARGET="docs/latest-sp800-summary.md"
BRANCH="chore/sp800-summary-$(date +%Y%m%d-%H%M)"
BASE="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@origin/@@' || echo main)"
KEEP_OPEN="true"   # set to "false" if you don't want the "Press Enter" pause

# Pause on exit so your terminal doesn't close immediately
trap 'ret=$?; if [[ $ret -ne 0 ]]; then echo; echo "❌ Script failed (exit $ret). See output above."; fi; 
      if [[ "${KEEP_OPEN}" == "true" ]]; then echo; read -rp "Press Enter to close... "; fi; exit $ret' EXIT

echo "Base branch: $BASE"
echo "New branch : $BRANCH"

# ===== auth =====
if ! gh auth status >/dev/null 2>&1; then
  gh auth login -s repo -w
fi

# ===== 1) run pipeline =====
echo "==> Running Python steps"
pushd "$SRC_DIR" >/dev/null
python source.py
python filter.py
python summary.py
popd >/dev/null

# ===== 2) collect outputs =====
echo "==> Collecting outputs"
mkdir -p "$(dirname "$SUMMARY_TARGET")"

# If a summary already exists in docs/, keep it; else take the first summary-like file from $SRC_DIR
if compgen -G "docs/*summary*.md" >/dev/null; then
  CUR_DOC="$(ls docs/*summary*.md | head -n1)"
  # Only copy if different path than target
  if [[ "$CUR_DOC" != "$SUMMARY_TARGET" ]]; then
    cp "$CUR_DOC" "$SUMMARY_TARGET"
  fi
else
  FOUND="$(find "$SRC_DIR" -maxdepth 1 -type f \( -iname '*summary*.md' -o -iname '*sp800*.md' \) | head -n1 || true)"
  if [[ -n "${FOUND}" ]]; then
    cp "$FOUND" "$SUMMARY_TARGET"
  else
    echo "❌ No summary markdown found. Did summary.py create a file?"
    exit 1
  fi
fi

echo "Summary at: $SUMMARY_TARGET"
ls -lh "$SUMMARY_TARGET" || true
[ -f "$SRC_DIR/step1_nist_sp800_raw.json" ] && ls -lh "$SRC_DIR/step1_nist_sp800_raw.json"
[ -f "$SRC_DIR/step2_filtered.json" ]      && ls -lh "$SRC_DIR/step2_filtered.json"

# ===== 3) branch + commit =====
echo "==> Creating branch and committing"
git fetch origin "$BASE" --quiet || true
git checkout -b "$BRANCH"

# Stage changes if any
git add "$SUMMARY_TARGET" || true
[ -f "$SRC_DIR/step1_nist_sp800_raw.json" ] && git add "$SRC_DIR/step1_nist_sp800_raw.json"
[ -f "$SRC_DIR/step2_filtered.json" ]      && git add "$SRC_DIR/step2_filtered.json"

if git diff --cached --quiet; then
  echo "ℹ️  No changes to commit; nothing to publish."
  exit 0
fi

git commit -m "NIST SP 800: latest summary (automated) [$(date -u +%F)]" \
            -m "Includes filtered artifacts for traceability."
git push -u origin "$BRANCH"

# ===== 4) open PR =====
echo "==> Opening PR"
gh pr create \
  --base "$BASE" \
  --head "$BRANCH" \
  --title "NIST SP 800: latest summary" \
  --body  "Automated summary update from Codespaces (software/DevOps/SDLC focus) with filtered artifacts."

echo "==> Done. Opening PR page…"
gh pr view --web || true

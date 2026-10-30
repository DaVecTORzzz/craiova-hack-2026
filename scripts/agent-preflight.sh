#!/usr/bin/env bash
set -euo pipefail

# Sincronizează cele două repo-uri SafeSight înainte de un task.
# Merge și din repo-ul public, și din cel privat; sibling-ul este opțional.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN="${SAFETARMAC_MAIN_DIR:-$ROOT/../craiova-hack-2026}"
DOCS="${SAFETARMAC_DOCS_DIR:-$ROOT/../safetarmac-docs}"

status=0

sync_repo() {
  local name="$1" path="$2" required="$3"

  if [[ ! -d "$path/.git" ]]; then
    if [[ "$required" == "1" ]]; then
      echo "✗ $name lipsește: $path" >&2
      status=1
    else
      echo "• $name nu e clonat lângă repo: $path (sar peste)"
    fi
    return 0
  fi

  echo "== $name ($path)"

  if ! git -C "$path" fetch --prune origin; then
    echo "✗ $name: fetch a eșuat" >&2
    status=1
    return 0
  fi

  local branch dirty behind
  branch="$(git -C "$path" rev-parse --abbrev-ref HEAD)"
  dirty="$(git -C "$path" status --porcelain)"

  if [[ -n "$dirty" ]]; then
    echo "  ! modificări locale; nu fac pull. Rezolvă sau fă stash înainte de task."
    status=1
  elif [[ "$branch" == "main" ]]; then
    if ! git -C "$path" pull --ff-only origin main; then
      echo "✗ $name: pull --ff-only a eșuat; istoric divergent." >&2
      status=1
    fi
  else
    echo "  • pe branch-ul $branch; am făcut doar fetch (nu schimb branch-ul)."
  fi

  behind="$(git -C "$path" rev-list --count "HEAD..@{u}" 2>/dev/null || echo "?")"
  echo "  → $(git -C "$path" rev-parse --short HEAD) pe $branch, în urma origin: $behind commituri"
}

if [[ -f "$ROOT/docs/contract.md" ]]; then
  sync_repo "main" "$ROOT" "1"
  sync_repo "docs" "$DOCS" "0"
elif [[ -f "$ROOT/lib/theme.typ" ]]; then
  sync_repo "docs" "$ROOT" "1"
  sync_repo "main" "$MAIN" "0"
else
  echo "✗ nu recunosc repo-ul: $ROOT" >&2
  exit 1
fi

if [[ "$status" -ne 0 ]]; then
  echo ""
  echo "Preflight: ATENȚIE. Nu începe taskul până nu rezolvi ce e mai sus."
  exit 1
fi

echo ""
echo "Preflight OK: ambele repo-uri sunt sincronizate."

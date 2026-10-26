#!/bin/bash
set -e

# CI Gate Script for Prompt Architect RC
# Enforces quality and security standards without false positives.

echo "🔒 Running CI Gates..."

FAILURES=0
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 1. Check for print() statements in backend/app/
echo "🔍 Checking for active 'print()' statements..."
if grep -rn "print(" backend/app --include='*.py' | grep -vE "^\s*#" | grep -vE "#.*print\(" | grep -v "tests/" | grep -v "scripts/"; then
    echo "❌ FAIL: Found active 'print()' statements. Use logger instead."
    FAILURES=$((FAILURES+1))
else
    echo "✅ PASS: No active 'print()' statements found."
fi

# 2. Check for weak default keys
echo "🔍 Checking for hardcoded weak keys..."
if grep -rnE "default_dev_key|default_key_safe_for_local|['\"]dev_key['\"]|['\"]default_key['\"]" backend/app backend/entry.py --include='*.py' \
  | grep -v "tests/"; then
    echo "❌ FAIL: Found hardcoded weak/default keys."
    FAILURES=$((FAILURES+1))
else
    echo "✅ PASS: No hardcoded weak default keys found."
fi

# 3. Check for Empty CSP in Tauri (whitespace/null variants included)
echo "🔍 Checking Tauri CSP..."
if grep -qE '"csp":\s*(""|null)' frontend/src-tauri/tauri.conf.json; then
    echo "❌ FAIL: CSP is empty in tauri.conf.json."
    FAILURES=$((FAILURES+1))
else
    echo "✅ PASS: CSP is configured."
fi

# 4. Hardcoded absolute machine paths in hot path
echo "🔍 Checking for hardcoded /home/carlos paths in app code..."
if grep -rn "/home/carlos" backend/app --include='*.py'; then
    echo "❌ FAIL: Hardcoded absolute home paths found."
    FAILURES=$((FAILURES+1))
else
    echo "✅ PASS: No hardcoded home paths in backend/app."
fi

# 5. Frontend must not hardcode localhost:8000 in components/stores
echo "🔍 Checking frontend for hardcoded localhost:8000..."
if grep -rn "localhost:8000" frontend/src/lib/components frontend/src/lib/stores frontend/src/routes 2>/dev/null; then
    echo "❌ FAIL: Hardcoded localhost:8000 remains in UI sources."
    FAILURES=$((FAILURES+1))
else
    echo "✅ PASS: UI sources use shared backend URL helper."
fi

# 6. Pipeline must not import microvm on module load (source scan)
echo "🔍 Checking kayab_pipeline does not import microvm/tribunal..."
if grep -E "microvm_manager|TribunalEngine|firecracker" backend/app/kayab_pipeline.py; then
    echo "❌ FAIL: Hot-path pipeline still references MicroVM/tribunal."
    FAILURES=$((FAILURES+1))
else
    echo "✅ PASS: Hot-path pipeline is MicroVM-free."
fi

if [ $FAILURES -gt 0 ]; then
    echo "⛔ GATES FAILED with $FAILURES errors."
    exit 1
else
    echo "🎉 ALL GATES PASSED."
    exit 0
fi

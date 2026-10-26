# Changelog — Prompt Architect RC

## 1.0.2-rc.1 — 2026-10-26 (release engineering + full re-verification)

### Release engineering
- Initialized **git** repository; history starts at the pre-cleanup snapshot; tagged `v1.0.2-rc.1`.
- Repaired `ci/pack-test.sh` (was guaranteed-fail): root `pa-backend.spec` path, onefile `dist/pa-backend` path, **dynamic-port discovery via `PA_PORT`** (same protocol as Tauri), `/health` expects `healthy`, venv-aware PyInstaller.
- Repaired `ci/rc-pipeline.yml`: current version string, `pytest-cov` installed, coverage uploaded as artifact, added **frontend job** (`svelte-check` + build), `workflow_dispatch` trigger.
- Live re-verification on freshly built binary: `/health`, `/status`, `/models`, `POST /generate` (`qwen2.5:0.5b` → 200, `success: true`, signature), authenticated graceful shutdown (`x-shutdown-key`) → process exit.
- AppImage formally deferred to post-1.0 (deb is the supported Linux target).

### Hygiene
- Deleted unreferenced `backend/app/prompt_library.json.bak`; removed stale root logs.
- Moved `test-backend.sh` → `backend/scripts/legacy/`; moved personal `backup_tools.py` out of the repo (contained an embedded secret; scrubbed from history).
- Gitignored experimental trees (`firecracker_images/`, `buildroot_config/`, `philosohy addon/`, `*_dist/`) — kept locally, not tracked.

### Not verified yet
- Human UI click-through (generate in window) — protocol in RELEASE_CHECKLIST.

---

## 1.0.2-rc.1 — 2026-07-24 (verification + packaging)

### Verification completed
- Live `POST /generate` with Ollama `qwen2.5:0.5b` (success + signature).
- Frontend production build (`npm run build`) OK.
- Sidecar lifecycle: start → health → authenticated shutdown → process exit.
- Desktop release binary launches sidecar (`PA_PORT` + `/health`).
- Tauri **deb** package built; AppImage skipped (linuxdeploy failure).
- Aligned `@tauri-apps/api` to 2.10.x with Rust `tauri` 2.10.x.
- Bundle identifier set to `com.promptarchitect.desktop` (avoid `.app` suffix).

### Follow-up after post-RC audit
- **Generate honesty:** response includes `success`, `reason`, `iterations`, `integrity_signature`; empty hard-fail → HTTP **422**; partial soft-fail → 200 + `success: false`.
- **UI:** InputPanel surfaces partial failures; SystemVitals shows real CPU/RAM/GPU/tier (no fake entropy mapping).
- **Tribunal flag:** `KAYAB_ENABLE_TRIBUNAL` no longer implies enablement; clear warning that tribunal is **not wired** into `/generate`.
- **Legacy scripts:** moved broken root tests to `backend/scripts/legacy/` + smoke helper for `/generate`.
- **Sidecar:** rebuilt `pa-backend-x86_64-unknown-linux-gnu` (PyInstaller) with RC modules + rules data.

---

## 1.0.2-rc.1 — 2026-07-22

### Critical fixes
- Restored **prompt refinement** as the primary `/generate` pipeline (Mask → Linter/AutoFix → LLM → Mask → Sign).
- Removed Firecracker/Tribunal construction from the hot path (optional via `KAYAB_ENABLE_TRIBUNAL`, default off).
- Implemented **OllamaArchitect** for local models (base Architect no longer used for generate).
- Fixed Ollama model listing for modern SDK objects (`.model` field).
- Fixed MaskService / SpecValidator call contracts used by the pipeline.
- Unified frontend backend URL resolution (Tauri dynamic port); removed hardcoded `localhost:8000` from UI components.
- Prefer HTTP sidecar connection over Gemini/MCP in desktop mode.
- Hardened signing keys to use `settings.SYSTEM_KEY` / `PA_SYSTEM_KEY` (no weak default literals).
- Extended CI gates (weak keys, absolute paths, MicroVM-free pipeline, frontend URL policy).
- Full unit/integration suite green (35 tests), including real pipeline contract tests with mocked Architect.

### Versioning
- Aligned versions to `1.0.2-rc.1` (backend, frontend package, Tauri config, Cargo, UI header).

### Status
- **Release Candidate** — not a final stable claim. See README and RELEASE_CHECKLIST.

# Changelog — Prompt Architect RC

## 1.0.2-rc.1 — 2026-10-26 (model enablement M1–M4 + PID-lock fix)

### Critical fix — desktop launch after machine restart
- `backend/entry.py`: `check_pid_lock` treated **any live PID** as "backend running". After a machine restart the OS reuses PIDs, so a recycled PID from an unrelated process permanently blocked app launch (the reported click-through failure). Now `_looks_like_our_backend(pid)` verifies `/proc/<pid>/cmdline` actually belongs to Prompt Architect (`pa-backend`/`entry.py`) before treating the lock as live; dead/recycled/garbage lockfiles are reclaimed. Regression suite: `backend/tests/test_pid_lock.py` (5 tests).

### M1 — per-model behavior layer
- New `app/model_profiles.py`: `ModelProfileService` resolves a concrete model ID to a `ModelProfile` via **exact model entry → family pattern → generic defaults**.
- `Architect.generate(context, *, system, options)` interface across base/Ollama/Groq: optional system message and provider sampling options.
- Pipeline (`kayab_pipeline.py`): system text composed per profile (base template + governance + family directives + quirks + experimental note). `use_system_role=False` families (DeepSeek-R1, official guidance) get everything embedded in the user message.

### M2 — researched profile data
- `backend/model_profiles.yml` rewritten from official model cards, covering all 15 installed Ollama models + 4 legacy external models:
  - DeepSeek-R1 (incl. distills): temp 0.6 / top_p 0.95, no system role, think-then-answer directive.
  - Qwen2.5-Coder: temp 0.7 / top_p 0.8 / top_k 20 + official "You are Qwen…" identity.
  - Qwen3: `/no_think` switch + non-thinking sampling recs.
  - SmolLM2-1.7B: temp 0.2 (official card), English-only quirk.
  - Community/unknown fine-tunes (`bonsai`, `fable`, `synapse-*`): `experimental: true` → caution directive + audit tag.

### M3 — Groq catalog refresh
- `GROQ_MODELS` updated to current production list (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`); 5 retired IDs removed (they 404 on the API). Groq detection prefixes extended (`openai/`, `qwen/`, `moonshotai/`).

### M4 — governance rules wired in
- `RuleLoader.load_rules(flavor)` injected into `run_refinement` → pipeline: CRITICAL/HIGH rule descriptions surfaced as "Governance rules" guidance; regex rules evaluated on model output (CRITICAL → blocking error + iterate, others → advisory for next pass); `rules_<n>` audit tag.
- `technical.toml` R100 (no subjective adjectives) downgraded CRITICAL→HIGH: blocking on prose style caused non-convergence soft-fails on well-formed output.
- `KAYAB_MODEL_PRIMARY` fixed to installed `qwen2.5-coder:7b`; `OllamaArchitect` default to `qwen2.5:0.5b`.

### Tests
- Suite: **53 passing** (37 original + 5 PID + 11 model profiles). `./ci/gates.sh` green.

### Not verified yet
- Human UI click-through — first attempt failed due to the PID-reuse bug above (backend falsely seen as running); re-verify on rebuilt binary.

---

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

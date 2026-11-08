# Changelog — Prompt Architect RC

## hardening P2 — 2026-11-08 (RC closure cycle, prioridades 1–2 del audit externo)

### Input limits
- `GenerateRequest.user_input`, `RefineLoopRequest.user_input`, `OptimizeRequest.prompt`/`intent` limitados a `USER_INPUT_MAX_LENGTH` (100.000 caracteres). Se rechazan con 422 en validación (antes del pipeline); tests de límite, frontera y entrada en blanco.

### Groq key backend-side (antes: store Tauri en texto plano + round-trip por request)
- La clave ahora se guarda en `DATA_DIR/.groq_key` con permisos 0600 (mismo modelo de confianza que `.system_key`); `GROQ_API_KEY` por env sigue teniendo precedencia.
- Nuevos endpoints `POST/GET/DELETE /settings/groq`: nunca loggean ni devuelven la clave — la respuesta es solo `{groq_configured, source}`.
- La UI ya no lee el store de Tauri ni reenvía la clave en cada generación: Settings la empuja una vez al backend y el InputPanel no la toca. Claves antiguas del store se migran una vez y se borran.
- `/vital-signs.groq_configured` refleja la clave backend-side.

### Semántica de la firma de integridad (punto 3.3 del audit)
- Nuevo `POST /verify`: recalcula HMAC+hash con la clave local del sistema y reporta si el texto es bit-idéntico al firmado por esta instalación. Semántica explícita: **tamper-evidencia local, no acreditación de autoría** (documentado en código y en la UI).
- `OutputPanel` muestra estado firmado/verificado (tri-estado) con re-verificación con un clic.

### Tests
- Suite: **75 passing** (58 previos + 17 nuevos de hardening). `./ci/gates.sh` green. `npm run build` green.

---

## 1.0.2-rc.1 — 2026-10-26 (full technical + codebase audit)

Scope: hot-path backend review (main/api_router/mcp_adapter/kayab_pipeline/prompt_refinement/services/db/config/entry/hal/models/architects/forge/telemetry), frontend + Tauri deep-dive, dependencies/CI/packaging audit, live model smokes on all four profile families.

### Critical / High (all fixed)
- **`entry.py` NameError on PID reclaim** — `logger` was never defined; crashed exactly on the post-restart recycled-PID path when the stale PID was signal-able. Defined logger + signal-able-PID regression test.
- **Unscoped `shell:allow-execute` capability** (Tauri) — webview → arbitrary local command execution. Removed (nothing used it); added the minimal actually-needed perms (`store:default`, clipboard write, window controls — the Groq-key storage path was failing closed at runtime).
- **Tauri v2 detection bug** — `window.__TAURI__` is never injected without `withGlobalTauri`; 8 call sites (port discovery, backend-error listener, Groq-key store, window buttons, clipboard, preferHttpOnly) were dead in the packaged app → the UI hit baked-in `localhost:8000` → "Could not load profiles: Load failed". Root cause of the failed click-through (co-cause with the PID bug). Fixed via `isTauriRuntime()` (`__TAURI_INTERNALS__`).
- **System-key leak fallback** (Rust `shutdown_backend`) — POSTed the system key to hardcoded port 8000 when no sidecar port was known. Removed.
- **Unclosed think blocks leak output** — MaskService only stripped paired ` Holden…  Holden`; R1 truncated mid-think (realistic under num_predict caps) leaked reasoning. Added trailing-block strip + tests.

### Medium (fixed)
- **7B-class models unloadable on this 6 GB-RAM machine** (Ollama 500 "unable to load model", proven independent of options): added RAM-aware `num_ctx`/`num_predict` clamps to ModelProfileService (≤8 GB → 2048/1024, ≤16 GB → 4096/2048); `MODEL_PRIMARY` → `qwen2.5-coder:3b`; YAML default `num_ctx` 4096.
- **Persona/flavor mismatch** — 9 persona keys + UI intents mapped into `flavor`, but only technical/creative flavors exist → silently base-rules-only. Added `_resolve_flavor` mapping.
- **`groq_architect.list_models()`** returned retired model IDs — synced with `GROQ_MODELS`.
- **CI never ran** — `rc-pipeline.yml` wasn't under `.github/workflows/`. Moved.
- **Gates hardening** — removed `# allowed` weak-key escape hatch; CSP empty-check covers null/whitespace variants; weak-key scan includes `entry.py`.
- **requirements.txt was a raw 68-line `pip freeze`** shipping the unused langchain/langgraph stack, rouge_score/nltk/numpy, and dev tooling — curated to 24 runtime pins; `requirements-dev.txt` added.
- **`pa-backend.spec`** referenced the deleted `prompt_library.json.bak` (PyInstaller silently drops missing datas — verified — but the entry was stale); removed.

### Low / Info (documented, deferred)
- svelte 4.2.12 npm-audit advisories (fix = svelte 5 major; no XSS sinks exist in the app — text-interpolation only — so practical risk is low; migrate post-1.0).
- No auto-updater plugin configured; deb-only target, manual updates for now.
- GROQ key stored in plaintext plugin-store file (OS keyring recommended post-1.0).
- HAL: multi-GPU `nvidia-smi` parsing assumes single line; rocm-smi VRAM is a hardcoded 8.0 placeholder.
- `GenerateRequest.user_input` has no length cap (local-only endpoint; add limit post-RC).
- Dead code retained but unbundled: `mcp_server.py`, `forge.py`, `sqlog/`, microvm/tribunal modules, `models.py` unused request types.
- Actions pinned to moving tags (no remote yet — pin to SHAs when one is added).
- pack-test: kill targets the `timeout` wrapper; backend may briefly outlive it (PID lock makes a re-run fail-closed, not flaky-fail).

### Verified clean
- No SQL injection (parameterized everywhere), no XSS sinks in frontend (no `{@html}`/`innerHTML`/eval), no secrets in tracked files or git history, system key 0600, loopback-only bind, no known-vulnerable pins among used Python deps, spec bundles profiles.yml + model_profiles.yml + rules correctly, PyInstaller bundle excludes dead subsystems.

### Live smokes (2026-10-26, all HTTP 200 / success / signed / 1 iteration)
- `qwen2.5:0.5b` (regression), `smollm2-1.7b` (temp 0.2 profile), `deepseek-r1:1.5b` (R1 no-system-role path), `qwen2.5-coder:3b` (coder family).
- 7B-class models documented unloadable on this hardware (6 GB RAM); use Groq cloud for large models.

### Tests
- Suite: **58 passing** (37 original + 6 PID + 15 model profiles/mask/flavor). `./ci/gates.sh` green. `npm run build` green.

---

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

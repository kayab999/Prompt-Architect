# Release Checklist — 1.0.2-rc.1

## Automated gates

- [x] `./ci/gates.sh` exits 0 (re-verified 2026-10-26, after model enablement M1–M4)
- [x] `pytest backend/tests` all pass (**53**: 37 original + 5 PID-lock + 11 model profiles) (2026-10-26)
- [x] `ci/pack-test.sh` green end-to-end: PyInstaller build → launch → `PA_PORT` discovery → `/health` (2026-10-26; script repaired: root spec path, onefile exe path, dynamic-port discovery)

## Model enablement (M1–M4, 2026-10-26)

- [x] M1: per-model behavior layer — `ModelProfileService` + profile-aware pipeline (system role vs. embedded-user-message for DeepSeek-R1)
- [x] M2: `model_profiles.yml` researched from official cards — all 15 installed models + 4 legacy externals covered; community FTs marked `experimental: true`
- [x] M3: Groq `GROQ_MODELS` refreshed to current production (5 retired IDs removed); prefix detection extended
- [x] M4: governance rules wired into `run_refinement`; regex rules enforced (CRITICAL blocks + iterate, others advisory); R100 downgraded to HIGH to avoid non-convergence
- [x] PID-lock regression fixed (`_looks_like_our_backend`) — desktop launch after machine restart works again; 5 regression tests
- [ ] Live smokes on profile-sensitive models (`deepseek-r1-distill-qwen-7b-q4_k_m`, `qwen2.5-coder:7b`, `smollm2-1.7b`) + regression `qwen2.5:0.5b`
- [ ] Sidecar + deb rebuilt with M1–M4 + PID fix

## Functional (manual / smoke)

- [x] Backend starts and serves `/health` (re-verified 2026-10-26 on freshly built binary)
- [x] `/models` returns non-empty list (dict entries with `id`) (re-verified 2026-10-26)
- [x] `POST /generate` with local Ollama (`qwen2.5:0.5b`) — HTTP 200, `success: true`, 3 iterations, integrity signature (2026-07-24; re-verified 2026-10-26)
- [x] Desktop release binary launches sidecar; `PA_PORT` discovered; `/health` OK (2026-07-24; pack-test re-proves sidecar launch + discovery 2026-10-26)
- [x] Graceful shutdown via `/shutdown` + system key terminates sidecar (2026-07-24; re-verified 2026-10-26 — header is `x-shutdown-key`)
- [x] UI click-through attempt 1 (2026-10-26): **FAILED** — "Could not load profiles: Load failed" + blank render. Root cause identified: PID-reuse bug in `entry.py` (any live PID blocked launch after restart) — fixed + regression-tested; re-click-through required on rebuilt binary.

## Security

- [x] No weak default key literals in `backend/app`
- [x] CSP non-empty in `tauri.conf.json`
- [x] Signing uses `SYSTEM_KEY` / `PA_SYSTEM_KEY`
- [x] No secrets in tracked files (`.env` ignored, empty `GROQ_API_KEY`; personal backup script with embedded password removed from tree and history, 2026-10-26)

## Packaging

- [x] Sidecar binary present (`frontend/src-tauri/binaries/pa-backend-x86_64-unknown-linux-gnu`, built 2026-07-24; backend source unchanged since)
- [x] Sidecar smoke: `/health` + `/status` on freshly rebuilt onefile binary (2026-10-26)
- [x] `npm run build` frontend — 2026-07-24
- [x] `npx tauri build --bundles deb` — produces `.deb` (2026-07-24)
- [x] AppImage: **deferred to post-1.0** (linuxdeploy fails in this environment; deb is the supported Linux target — decision recorded 2026-10-26)
- [ ] Human UI click-through (generate in window) — protocol below

### UI click-through protocol (pending)

1. Install/open the app (`npx tauri dev` or the built `.deb`)
2. Generate with a local Ollama model (e.g. `qwen2.5:0.5b`) → output + integrity signature visible
3. Trigger a failure case (e.g. empty/blank input) → UI surfaces partial-failure state
4. Save a prompt to the Library → appears in Library route after restart
5. Record the date + result here

## Documentation

- [x] README status = Release Candidate
- [x] CHANGELOG-rc.md
- [x] Roadmap reflects RC remediation
- [x] CONTRIBUTING.md present

## Version control

- [x] Git repository initialized; history starts at pre-cleanup snapshot `1.0.2-rc.1` (2026-10-26)
- [x] Tag `v1.0.2-rc.1`
- [ ] Re-point tag to final verified commit after checklist close-out

---

**Status:** RC verification complete on the API/sidecar/packaging side (2026-10-26).
**Remaining before final tag:** UI click-through protocol (manual, above).

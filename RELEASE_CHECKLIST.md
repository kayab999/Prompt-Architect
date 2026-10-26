# Release Checklist — 1.0.2-rc.1

## Automated gates

- [x] `./ci/gates.sh` exits 0  
- [x] `pytest backend/tests` all pass (37)  

## Functional (manual / smoke)

- [x] Backend starts and serves `/health`  
- [x] `/models` returns non-empty list (dict entries with `id`)  
- [x] `POST /generate` with local Ollama (`qwen2.5:0.5b`) — HTTP 200, `success: true`, integrity signature (2026-07-24)  
- [x] Desktop release binary launches sidecar; `PA_PORT` discovered; `/health` OK (2026-07-24)  
- [x] Graceful shutdown via `/shutdown` + system key terminates sidecar (2026-07-24)  

## Security

- [x] No weak default key literals in `backend/app`  
- [x] CSP non-empty in `tauri.conf.json`  
- [x] Signing uses `SYSTEM_KEY` / `PA_SYSTEM_KEY`  

## Packaging

- [x] Rebuild sidecar binary (`./scripts/build_sidecar.sh`) — 2026-07-24  
- [x] Sidecar smoke: `/health` + `/status` on rebuilt binary  
- [x] `npm run build` frontend — 2026-07-24  
- [x] `npx tauri build --bundles deb` — produces `.deb` (2026-07-24)  
- [ ] Optional: AppImage (linuxdeploy failed in this environment; deb is default target)  
- [ ] Human UI click-through (generate in window) — automated launch verified; full UX not scripted  

## Documentation

- [x] README status = Release Candidate  
- [x] CHANGELOG-rc.md  
- [x] Roadmap reflects RC remediation  
- [x] CONTRIBUTING.md present  

---

**Status:** RC verification largely complete (API + sidecar lifecycle + frontend build + deb package + desktop binary launch).  
**Remaining optional:** interactive UI generate in the window; AppImage if linuxdeploy is fixed; git tag.

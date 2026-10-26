# Prompt Architect

A local-first, privacy-focused prompt engineering environment. Refine, test, and manage prompts for any LLM with rule-based governance and optional cloud providers.

**Status:** Release Candidate **v1.0.2-rc.1** (2026-07-22)

## Overview

Prompt Architect runs a FastAPI backend as a Tauri sidecar and a SvelteKit UI. The core product path is:

1. User enters a draft prompt  
2. Input is sanitized (think-tags, PII redaction)  
3. Static linter + deterministic autofixer run  
4. Local (Ollama) or cloud (Groq) model refines the prompt  
5. Output is re-sanitized and integrity-signed  

Experimental Firecracker “tribunal” code remains in the tree but is **disabled by default** and is not on the generate hot path.

## Core features

- **Local-first:** processing stays on your machine by default  
- **Dynamic sidecar port** discovery from Tauri  
- **Mask Machine:** PII redaction, think-tag strip, integrity HMAC  
- **PromptLinter / AutoFixer:** static rules (filler, unclosed tags, structure)  
- **Ollama + Groq** model backends  
- **SQLite** prompt library under the OS data directory  
- **Hardware vitals** for tier display  

## Prerequisites

- Node.js (frontend / Tauri)  
- Python 3.10+  
- Optional: [Ollama](https://ollama.com/) for local models  
- Optional: Groq API key for cloud models  

## Installation

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# Frontend
cd frontend
npm install
cd ..
```

## Running

### Desktop (Tauri)

```bash
cd frontend
npm run tauri dev
```

Tauri spawns the `pa-backend` sidecar, reads `PA_PORT=…`, and the UI connects to that port.

### Backend only (API smoke)

```bash
cd backend
source venv/bin/activate
python entry.py --port 8000
# GET http://127.0.0.1:8000/health
# POST http://127.0.0.1:8000/generate
```

### Frontend only (against a running backend)

```bash
export VITE_API_URL=http://127.0.0.1:8000
cd frontend && npm run dev
```

## Configuration

| Item | Location |
|------|----------|
| Data directory | `~/.local/share/prompt_architect` (Linux) |
| System key | `PA_SYSTEM_KEY` env or `.system_key` in data dir |
| Groq key | Settings UI (Tauri store) or `GROQ_API_KEY` |
| Tribunal (experimental) | `KAYAB_ENABLE_TRIBUNAL=1` (off by default) |
| Profiles | `backend/app/profiles.yml` |

## Quality gates

```bash
./ci/gates.sh
cd backend && source venv/bin/activate && export PYTHONPATH=. && pytest tests -v
```

### Rebuild desktop sidecar

```bash
./scripts/build_sidecar.sh
# outputs: frontend/src-tauri/binaries/pa-backend-<triple>
```

### Desktop package (Linux deb)

```bash
cd frontend
npm install
npx tauri build --bundles deb
# artifact: src-tauri/target/release/bundle/deb/Prompt Architect_1.0.2-rc.1_amd64.deb
```

AppImage is not the default target (linuxdeploy may fail on some hosts).

### Manual generate smoke (backend must be running)

```bash
cd backend && source venv/bin/activate
python scripts/legacy/smoke_generate.py --base http://127.0.0.1:8000 --model qwen2.5:0.5b
```

## Project layout

```
backend/app/          FastAPI app, pipeline, linter, mask, architects
frontend/src/         SvelteKit UI
frontend/src-tauri/   Tauri shell + sidecar lifecycle
ci/                   gates.sh, RC pipeline YAML
docs/                 design notes
```

## Contributing

See `CONTRIBUTING.md` and `COLLABORATOR_MANIFESTO.md`. Update tests and the roadmap when changing behavior.

## License / issues

Report bugs with OS, version (`1.0.2-rc.1`), and steps to reproduce.

# Contributing to Prompt Architect

## Principles

1. Prefer small, testable changes.  
2. Do not put Firecracker/MicroVM on the prompt generate hot path.  
3. Every behavior change needs a test or an explicit checklist update.  
4. Keep docs honest about RC vs stable.  

## Setup

```bash
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest tests -v
cd ../frontend && npm install
```

## Before you push

```bash
./ci/gates.sh
cd backend && source venv/bin/activate && pytest tests -v
```

## Architecture notes

- Primary pipeline: `PromptRefinementPipeline` in `backend/app/kayab_pipeline.py`  
- Adapter: `backend/app/mcp_adapter.py`  
- Frontend base URL: `frontend/src/lib/services/backendUrl.ts`  

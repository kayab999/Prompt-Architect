# Legacy / manual scripts (quarantined)

These scripts are **not** part of the RC pytest suite (`backend/tests/`).

| Script | Issue |
|--------|--------|
| `test_mask_machine.py` | Calls removed `/mask_machine` endpoint |
| `test_sovereign_integrity.py` | Same |
| `test_kayab_pipeline.py` | Wrong import path `backend.app.*` |
| `test_sqlog.py` | Wrong import path |
| `test_groq_connection.py` | Wrong import path; needs live Groq key |

**Canonical tests:** run from `backend/`:

```bash
source venv/bin/activate
export PYTHONPATH=.
pytest tests -v
```

To revive a script, rewrite imports to `from app....` and target current endpoints
(`/generate`, `/optimize`, unit APIs).

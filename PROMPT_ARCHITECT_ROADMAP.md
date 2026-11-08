# Prompt Architect Development Roadmap

## Phase 2: Stability & Persistence (COMPLETED)

- Unified storage via `platformdirs`  
- Structured logging, HAL hardware detection  
- CSP / CORS / system key  
- Sidecar lifecycle + dynamic port + single-instance  

## Phase 3: Sovereign Governor (PARTIAL)

**Completed for RC:**

- RuleLoader + flavors  
- MaskService PII + think-tag strip + integrity signing  
- PromptLinter + AutoFixer  
- Prompt refinement pipeline on `/generate`  
- Ollama + Groq architects  

**Experimental / not RC-critical:**

- Firecracker Tribunal / MicroVM (feature-flagged off)  
- SQLog quest machine  
- ConstitutionForge  

## RC Remediation (1.0.2-rc.1 — 2026-07-22)

- [x] Restore prompt pipeline contracts  
- [x] Decouple tribunal from hot path  
- [x] OllamaArchitect + model list fix  

## Model Enablement (M1–M4 — 2026-10-26, COMPLETE)

Per-model behavior sourced from official model cards; community fine-tunes marked experimental.

- [x] M1: `ModelProfileService` (exact model → family pattern → generic); profile-aware `Architect.generate(context, *, system, options)`; R1-family instructions embedded in user message (no system role)
- [x] M2: `model_profiles.yml` — DeepSeek-R1 (0.6/0.95, no system role), Qwen2.5-Coder (0.7/0.8/k20 + Qwen identity), Qwen3 (`/no_think`), SmolLM2 (0.2), experimental flags for bonsai/fable/synapse
- [x] M3: Groq catalog refreshed to current production; prefix detection extended (`openai/`, `qwen/`, `moonshotai/`)
- [x] M4: governance rules wired into the pipeline (regex enforcement: CRITICAL blocks, others advisory); R100 downgraded to HIGH (non-convergence fix)
- [x] PID-lock regression fix (desktop launch after machine restart)
- [ ] Live smokes on profile-sensitive models → then UI click-through → 1.0.2 final
- [x] Frontend single backend URL  
- [x] Weak key removal + gate expansion  
- [x] Test suite 100% green with pipeline contracts  
- [x] Docs honesty (RC, not false “stable”)  

## RC Closure — Hardening P2 (2026-11-08, tras audit externo)

- [x] Límite `user_input`/`prompt`/`intent` (100k chars, 422 pre-pipeline) + tests de límite/frontera/blanco
- [x] Clave Groq backend-side (`DATA_DIR/.groq_key`, 0600); endpoints `/settings/groq` set/get/delete sin eco de la clave; UI sin round-trip ni store Tauri (migración automática del modo legacy)
- [x] `POST /verify` — tamper-evidencia local (HMAC + sha256), semántica explícita (no acredita autoría); visualización de firma en OutputPanel con re-verificación
- [ ] UI click-through sobre paquete reconstruido (protocolo en RELEASE_CHECKLIST)
- [ ] Keyring del OS como destino para distribución pública (0600-file es el estado RC)

## RC Release Engineering (2026-10-26)

- [x] Git repo + `v1.0.2-rc.1` tag  
- [x] `ci/pack-test.sh` repaired (spec path, onefile exe, `PA_PORT` discovery)  
- [x] `ci/rc-pipeline.yml` repaired (pytest-cov, frontend job, version string)  
- [x] Full live re-verification (health/models/generate/shutdown) on fresh binary  
- [x] Workspace hygiene (junk logs, `.bak` files, secret-bearing personal script removed)  

## Future (v1.1.0+)

- [ ] Persistent memory / session resume  
- [ ] NER-based PII  
- [ ] Ollama model browser UX polish  
- [ ] VS Code extension parity with dynamic port  
- [ ] Declarative MicroVM environment (no host `sudo`)  
- [ ] Sidecar rebuild automation in CI  

## v1.1 direction (per external review, 2026-11-08)
- Reproducible evaluation of prompt quality rather than more features.
  Benchmark: original prompts → refined prompts → independent task
  evaluation. Metrics: instruction adherence, constraint preservation,
  model compatibility, semantic drift, robustness, refinement efficiency.
  Goal: answer "does Prompt Architect systematically produce better
  instructions than a competent user without it?" 

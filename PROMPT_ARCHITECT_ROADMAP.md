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
- [x] Frontend single backend URL  
- [x] Weak key removal + gate expansion  
- [x] Test suite 100% green with pipeline contracts  
- [x] Docs honesty (RC, not false “stable”)  

## Future (v1.1.0+)

- [ ] Persistent memory / session resume  
- [ ] NER-based PII  
- [ ] Ollama model browser UX polish  
- [ ] VS Code extension parity with dynamic port  
- [ ] Declarative MicroVM environment (no host `sudo`)  
- [ ] Sidecar rebuild automation in CI  

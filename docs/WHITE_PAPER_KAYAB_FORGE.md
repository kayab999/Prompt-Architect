# Kayab Forge — Technical Note (RC)

Kayab is the governance layer around Prompt Architect:

- **Rules** (`backend/app/rules/*.toml`): constitutional + flavor statutes  
- **Linter / AutoFixer**: deterministic static analysis  
- **MaskService**: PII redaction, think-tag removal, integrity signing  
- **Pipeline**: iterative refine with success gate  

Optional experimental components (not required for RC):

- Firecracker MicroVM tribunal (`KAYAB_ENABLE_TRIBUNAL`)  
- SQLog signed quest log  
- ConstitutionForge for project TOML generation  

Primary product path for RC: **prompt refinement**, not code certification.

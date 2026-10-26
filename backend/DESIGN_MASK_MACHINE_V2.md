# Design: Mask Machine v2 (The "Ruff" Architecture)

## Philosophy
Inspired by **Ruff** (the extremely fast Python linter), the Mask Machine v2 aims to shift prompt refinement from "Pure LLM" to "Hybrid Static/Semantic Analysis".

**Core Principle:** *Don't ask an LLM to fix what a Regex can fix.*

## Architecture

### 1. The Linter (Static Analysis)
Instead of vague error messages, we implement a **Rule Registry** with specific codes.

| Code | Category | Name | Description | Fix Type |
| :--- | :--- | :--- | :--- | :--- |
| **S001** | Structure | `missing-context` | Prompt lacks a `<Context>` or `Context:` section. | LLM (Generative) |
| **S002** | Structure | `unclosed-tag` | Found an opening tag `<tag>` without `</tag>`. | **Code (Deterministic)** |
| **S003** | Structure | `nested-tag-error` | Improper nesting of XML-style tags. | **Code (Deterministic)** |
| **W001** | Weakness | `ambiguous-verbs` | Use of "want", "try", "make something". | LLM (Refinement) |
| **W002** | Weakness | `filler-words` | "Please", "If you can", "I was wondering". | **Code (Deterministic)** |
| **V001** | Variable | `orphan-variable` | Variable `{var}` exists but isn't defined. | LLM (Contextual) |

### 2. The Auto-Fixer (The "Fast Path")
A purely algorithmic component that runs *before* the LLM. 
- **Input:** Raw Prompt + Linter Report
- **Process:** Iterates through errors with `Fix Type: Code`. Applies string manipulation.
- **Output:** Cleaned Prompt (ready for LLM refinement or final use).

**Example:**
*Input:* "Please generate a json list."
*Linter:* Detected `W002` (filler-words: "Please").
*Fixer:* Removes "Please ".
*Result:* "Generate a json list."

### 3. The Refiner (The "Slow Path")
The LLM is invoked *only* for:
1.  **Generative Fixes:** Creating missing content (e.g., "Add a Persona").
2.  **Semantic Improvements:** Clarifying ambiguity, changing tone.

## Workflow (The Feedback Loop)

1.  **User Types Prompt.**
2.  **Linter Runs (ms):** Returns list of `Diagnostics`.
3.  **Auto-Fixer Runs (ms):** Applies all `Deterministic` fixes immediately.
4.  **Refiner Runs (sec):** (Optional/On-Demand) Solves the remaining `Generative` issues.

## Implementation Plan

1.  **Refactor `PromptLinter`:**
    -   Assign Error Codes.
    -   Return `Diagnostic` objects with `fixable: bool`.
2.  **Implement `AutoFixer`:**
    -   Registry of fix functions mapped to Error Codes.
3.  **Update `RefinementLoop`:**
    -   Integrate `AutoFixer` as step 0.
    -   Update LLM system prompt to focus only on the *hard* problems.

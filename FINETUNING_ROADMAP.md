# Prompt Architect - Fine-Tuning Roadmap

This document outlines the strategy and progress for fine-tuning a specialized small language model to act as the core AI for the Prompt Architect application.

## 1. Model Strategy

The core strategy is to leverage a fine-tuned model for advanced prompt refinement, ensuring high quality, adherence to specific styles, and optimal performance for target LLMs.

*   **Base Model:** The project can utilize various base models, with a focus on strong instruction-following and code generation capabilities. Models like **Llama 3 8B Instruct**, **Qwen2 7B Instruct**, or similar open-source alternatives are suitable candidates. The choice will depend on performance, licensing, and hardware requirements.
*   **Fine-Tuning Technique:** **QLoRA (Quantized Low-Rank Adaptation)** is the recommended method for efficient fine-tuning on consumer-grade hardware.
*   **Data Generation:** A synthetic dataset generation approach is preferred for scalability and cost-effectiveness. This involves using a highly capable model (e.g., GPT-4o-mini, Claude 3 Haiku) to transform simpler prompts into expert-level prompts based on a set of "gold standard" examples. This creates a dataset of `{"input": "simple_prompt", "output": "expert_prompt"}` pairs.

## 2. Fine-Tuning Process

### Step A: Dataset Preparation
- **Strategy:** "Gold Standard" Few-Shot Generation.
- **Process:**
    1.  Define a small set of "gold standard" prompt pairs for high-quality reference.
    2.  Use a capable model (e.g., GPT-4o-mini) in a few-shot configuration with the gold standards to generate a large dataset (10,000+ pairs) of simple-to-expert prompt transformations.
    3.  Ensure the generated prompts align with the desired output styles and are optimized for target LLMs.
    4.  Store the dataset in a structured format (e.g., JSONL).

### Step B: Training Implementation
- **Technique:** QLoRA for efficient fine-tuning.
- **Libraries:** Utilize `transformers`, `peft` (for LoRA), `bitsandbytes` (for quantization), and `trl` (for training utilities).
- **Script:** A dedicated fine-tuning script (`fine_tune.py`) will be developed/used to handle QLoRA configuration and data loading.

### Step C: Training Execution
- Run the fine-tuning process using the prepared dataset and QLoRA technique.
- Save the resulting LoRA adapter weights.

### Step D: Evaluation & Integration
- **Qualitative Testing:** Human-in-the-loop evaluation to confirm the fine-tuned model produces superior prompts compared to base models or simpler methods.
- **Integration:** Load and utilize the fine-tuned model within the Prompt Architect backend for prompt refinement tasks.

## 3. Progress Tracker

- [x] **Phase 1: Dataset Generation (scripts)**
    - [x] Setup synthetic generation script (`backend/generate_dataset.py`).
    - [ ] Generate and review initial examples.
    - [ ] Generate full dataset.
- [x] **Phase 2: Training Implementation (scripts)**
    - [x] Create fine-tuning script (`backend/fine_tune.py`).
    - [x] Configure script for QLoRA and chosen base model.
    - [ ] Test script with a subset of data.
- [ ] **Phase 3: Model Fine-Tuning**
    - [ ] Execute full fine-tuning process.
    - [ ] Save LoRA adapter weights.
- [ ] **Phase 4: Evaluation & Integration**
    - [ ] Perform qualitative testing.
    - [ ] Integrate the fine-tuned model into the Prompt Architect backend.

Note (RC 1.0.2-rc.1): scripts exist; training and runtime integration are **not** part of the RC ship criteria.

---
*This roadmap reflects the planned fine-tuning strategy for enhancing Prompt Architect's core AI capabilities.*

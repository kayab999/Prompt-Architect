import argparse
from datasets import load_dataset
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer
import torch

def parse_args():
    parser = argparse.ArgumentParser(description="Automate QLoRA fine-tuning for Llama 3")
    parser.add_argument("--model_name", type=str, default="meta-llama/Meta-Llama-3-8B-Instruct", help="Base model name")
    parser.add_argument("--dataset_path", type=str, required=True, help="Path to JSONL dataset")
    parser.add_argument("--output_dir", type=str, default="./fine_tuned_model", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size per device")
    parser.add_argument("--lora_rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--learning_rate", type=float, default=2e-4, help="Learning rate")
    return parser.parse_args()

def main():
    args = parse_args()

    # Quantization config for 4-bit
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # Load model and tokenizer
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        attn_implementation="flash_attention_2" if torch.cuda.is_available() else None,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token

    # Prepare model for QLoRA
    model = prepare_model_for_kbit_training(model)
    peft_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, peft_config)

    # Load dataset (assume JSONL with 'prompt' and 'completion')
    dataset = load_dataset("json", data_files=args.dataset_path, split="train")
    dataset = dataset.train_test_split(test_size=0.1)  # Split for validation

    # Training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        learning_rate=args.learning_rate,
        fp16=True,
        max_grad_norm=0.3,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="linear",
        logging_steps=10,
        save_steps=100,
        evaluation_strategy="steps",
        eval_steps=100,
        report_to="tensorboard",
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        peft_config=peft_config,
        dataset_text_field="text",  # Adjust if your dataset uses different fields
        tokenizer=tokenizer,
        args=training_args,
        max_seq_length=2048,  # Adjust based on context needs
    )

    # Train and save
    trainer.train()
    trainer.model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Fine-tuned model saved to {args.output_dir}")

if __name__ == "__main__":
    main()

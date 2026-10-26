import os
import json
import openai  # Using openai as a placeholder, can be swapped with anthropic, etc.
import argparse
from tqdm import tqdm

# --- Configuration ---
# IMPORTANT: Set your API key here or as an environment variable
# For example: export OPENAI_API_KEY='your-key-here'
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# The meta-prompt that instructs the powerful LLM to act as a prompt architect
META_PROMPT = """
You are a world-class prompt engineer. Your task is to take a simple user request and transform it into a detailed, expert-level prompt that is optimized for a modern, instruction-following Large Language Model. 

- You must be creative and add details that the user might not have thought of.
- For coding prompts, include requirements for efficiency, comments, and error handling.
- For creative prompts, include details about style, mood, and composition.
- The output must be ONLY the refined prompt, with no additional text, commentary, or pleasantries.
"""

# A list of simple prompts to be expanded upon. 
# This list should be expanded significantly for a real dataset.
SAMPLE_PROMPTS = [
    # Coding
    "python function to sort a list",
    "react component for a login form",
    "sql query to find duplicate emails",
    "dockerfile for a basic node.js app",
    "bash script to backup a directory",
    
    # Creative
    "a picture of a futuristic city",
    "a logo for a coffee shop called 'The Daily Grind'",
    "a poem about the moon",
    "a short story about a robot who discovers music",
    "a marketing slogan for a new electric car",

    # General/Reasoning
    "summarize the theory of relativity in simple terms",
    "explain the pros and cons of nuclear energy",
    "write an email to my boss asking for a raise",
    "plan a 3-day trip to Paris",
    "what is the capital of Mongolia?"
]

def parse_args():
    parser = argparse.ArgumentParser(description="Generate a synthetic dataset for prompt optimization.")
    parser.add_argument("--output_file", type=str, default="synthetic_prompts.jsonl", help="Path to the output JSONL file.")
    parser.add_argument("--model", type=str, default="gpt-4-turbo", help="The powerful model to use for generation.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of generated examples for a quick test.")
    return parser.parse_args()

def generate_synthetic_pair(prompt: str, model: str):
    """Generates a single input/output pair using the LLM."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": META_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, # A bit of creativity is good
        )
        refined_prompt = response.choices[0].message.content.strip()
        
        # Basic validation
        if len(refined_prompt) > len(prompt) and len(refined_prompt) > 20:
            return {"input": prompt, "output": refined_prompt}
    except Exception as e:
        print(f"\nAn error occurred while processing prompt '{prompt}': {e}")
    return None

def main():
    args = parse_args()
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set. Please set it to run this script.")
        return

    print(f"Starting dataset generation using model: {args.model}")
    print(f"Output will be saved to: {args.output_file}")

    prompts_to_generate = SAMPLE_PROMPTS
    if args.limit:
        prompts_to_generate = SAMPLE_PROMPTS[:args.limit]

    with open(args.output_file, 'w') as f:
        for prompt in tqdm(prompts_to_generate, desc="Generating prompts"):
            pair = generate_synthetic_pair(prompt, args.model)
            if pair:
                f.write(json.dumps(pair) + "\n")
    
    print(f"\nDataset generation complete. Saved to {args.output_file}")

if __name__ == "__main__":
    main()

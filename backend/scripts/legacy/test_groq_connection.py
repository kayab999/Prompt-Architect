import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from backend.app.groq_architect import GroqArchitect

async def test_groq():
    print(f"Current dir: {os.getcwd()}")
    env_path = Path(__file__).parent / ".env"
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("GROQ_API_KEY="):
                os.environ["GROQ_API_KEY"] = line.split("=")[1].strip()
    
    api_key = os.getenv("GROQ_API_KEY")
    print(f"Loaded key: {api_key[:5] if api_key else 'None'}")
    
    architect = GroqArchitect(model_name="llama-3.3-70b-versatile", api_key=api_key)
    print("Testing generate...")
    try:
        response = await architect.generate("Hello, are you working?")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_groq())

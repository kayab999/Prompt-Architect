import os
import yaml
from groq import Groq
from dotenv import load_dotenv

# Cargar entorno y perfiles
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Ruta al archivo profiles.yml
profiles_path = os.path.join(os.path.dirname(__file__), '../app/profiles.yml')

def load_profiles():
    with open(profiles_path, 'r') as f:
        return yaml.safe_load(f)

def test_profile(profile_key, profile_data, user_input):
    print(f"\n--- 🧪 PROBANDO PERFIL: {profile_data['name']} ---")
    print(f"📝 Input: '{user_input}'")
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": profile_data['system_prompt']},
                {"role": "user", "content": user_input}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
        )
        
        response = completion.choices[0].message.content
        print(f"\n🤖 Respuesta:\n{'-'*60}\n{response}\n{'-'*60}\n")
        
        # Validación rápida de listas
        if "- " in response or "1. " in response:
            print("⚠️ ALERTA: El modelo usó listas. Necesitamos reforzar el prompt negativo.")
        else:
            print("✅ ÉXITO: El modelo respetó la restricción de 'No Listas'.")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    profiles = load_profiles()
    
    # El mismo input para ver la diferencia de estilos
    test_topic = "Explícame qué es la entropía."
    
    # Probamos el Académico
    # test_profile('academic', profiles['academic'], test_topic)
    
    # Probamos el Didáctico
    # test_profile('didactic', profiles['didactic'], test_topic)

    # Probamos el Maestro Musical
    # zappa_question = "please explain in musical terms the theme 'uncle meat variation' by frank zappa"
    # test_profile('musical_bernstein', profiles['musical_bernstein'], zappa_question)

    # Probamos el Ingeniero Senior
    code_question = "a python function to check if a string is a palindrome"
    test_profile('senior_dev', profiles['senior_dev'], code_question)


if __name__ == "__main__":
    main()

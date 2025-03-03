from openai import OpenAI
import os
from dotenv import load_dotenv

def test_openai_api():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"Using API key: {api_key[:8]}...")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Test API with a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, World!'"}
            ]
        )
        
        print("\nSuccess! API Response:")
        print(f"Message: {response.choices[0].message.content}")
        print(f"Model: {response.model}")
        print(f"Usage: {response.usage}")
        
    except Exception as e:
        print("\nError:", str(e))

if __name__ == "__main__":
    test_openai_api()

from tavily import TavilyClient
import os
from dotenv import load_dotenv

def test_tavily_api():
    load_dotenv()
    api_key = os.getenv("TAVILY_API_KEY")
    print(f"Using API key: {api_key}")
    
    client = TavilyClient(api_key=api_key)
    try:
        response = client.search(query="test query", search_depth="basic")
        print("Success! API response:", response)
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    test_tavily_api()

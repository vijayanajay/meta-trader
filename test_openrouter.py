import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('OPENROUTER_API_KEY')
base_url = os.getenv('OPENROUTER_BASE_URL')

# Try a different model first
models_to_test = [
    'google/gemini-2.5-flash-image-preview:free',
    'moonshotai/kimi-k2:free'
]

for model in models_to_test:
    print(f'\n=== Testing model: {model} ===')

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    data = {
        'model': model,
        'messages': [{'role': 'user', 'content': 'Hello, just testing API'}],
        'max_tokens': 50
    }

    print('Sending request...')
    try:
        response = requests.post(f'{base_url}/chat/completions', headers=headers, json=data, timeout=15)
        print(f'Status Code: {response.status_code}')
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f'Success! Response: {content[:100]}...')
        else:
            print(f'Error response: {response.text}')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

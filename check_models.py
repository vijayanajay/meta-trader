import requests

try:
    response = requests.get('https://openrouter.ai/api/v1/models', timeout=10)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'Found {len(data.get("data", []))} models')
        # Print first few model IDs
        for model in data.get('data', [])[:10]:
            print(f'  - {model.get("id")}')
    else:
        print(f'Error: {response.text}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

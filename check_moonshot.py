import requests

response = requests.get('https://openrouter.ai/api/v1/models', timeout=10)
data = response.json()

moonshot_models = [model['id'] for model in data['data'] if 'moonshot' in model['id'].lower() or 'kimi' in model['id'].lower()]

print('Moonshot/Kimi models found:')
for model in moonshot_models:
    print(f'  - {model}')

if not moonshot_models:
    print('  No Moonshot or Kimi models found')

# Also check for free models
free_models = [model['id'] for model in data['data'] if 'free' in model['id'].lower()]
print(f'\nFree models found ({len(free_models)}):')
for model in free_models[:10]:  # Show first 10
    print(f'  - {model}')

from openai import OpenAI

print('module:', OpenAI)
names = [n for n in dir(OpenAI) if not n.startswith('_')]
print('names:', names)
for attr in ['models', 'chat', 'images', 'responses']:
    print(attr, hasattr(OpenAI(), attr))

try:
    client = OpenAI(api_key=None)
    print('client methods:', [n for n in dir(client) if not n.startswith('_')][:50])
except Exception as e:
    print('client inspect error', e)
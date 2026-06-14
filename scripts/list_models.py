import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

key = os.getenv('OPENAI_API_KEY')
print('OPENAI_API_KEY present:', bool(key))
client = OpenAI(api_key=key)

models = list(client.models.list())
print('total models:', len(models))
for model in models[:50]:
    print('model:', getattr(model, 'name', None) or str(model))

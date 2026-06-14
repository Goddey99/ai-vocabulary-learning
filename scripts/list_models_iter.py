from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

client = OpenAI()
for model in client.models.list():
    print(getattr(model, 'id', None) or getattr(model, 'name', None) or str(model))

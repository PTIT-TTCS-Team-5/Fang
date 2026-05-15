from openai import OpenAI

client = OpenAI(
    api_key="hello",
    base_url="https://api.orimise.com/v1",
)
try:
    models = client.models.list()
    for model in models:
        print(model.id)
except Exception as e:
    print(e)

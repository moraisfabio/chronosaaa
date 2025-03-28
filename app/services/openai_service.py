import openai

class OpenAIClient:
    def __init__(self, api_key):
        openai.api_key = api_key

    def get_assistant_response(self, message):
        client = openai.OpenAI()  # Create a client instance
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message['content']
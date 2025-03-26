import openai

class OpenAIClient:
    def __init__(self, api_key):
        openai.api_key = api_key

    def get_assistant_response(self, message):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message['content']
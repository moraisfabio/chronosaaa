import openai
import logging

class OpenAIClient:
    def __init__(self, api_key):
        openai.api_key = api_key

    def get_assistant_response(self, message):
        try:
            client = openai.OpenAI()  # Create a client instance
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um assistente útil."},
                    {"role": "user", "content": message}
                ]
            )
            # Acessar o conteúdo da resposta corretamente
            return response.choices[0].message.content
        except Exception as e:
            # Registrar o erro e retornar uma mensagem amigável
            logging.error(f"Erro ao obter resposta do OpenAI: {e}")
            return "Desculpe, ocorreu um erro ao processar sua solicitação. Tente novamente mais tarde."
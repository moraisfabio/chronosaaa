from flask import Flask, Blueprint, request, jsonify
import requests
from app.services.openai_service import OpenAIClient
from app.services.mongo_service import MongoDBClient
from app.utils.whatsapp_utils import send_whatsapp_message, send_interactive_menu, send_subservices_menu, send_available_slots_menu
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Inicialize o cliente OpenAI
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAIClient(api_key=openai_api_key)

# Inicialize o cliente MongoDB
mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")
mongo_client_caller = MongoDBClient(uri=mongo_uri, db_name=mongo_db_name)

# Configurações da API do WhatsApp Cloud
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

# Set your verification token (must match the one you enter in Meta)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Criação do Blueprint
routes_bp = Blueprint('routes', __name__)

@routes_bp.route("/webhook", methods=["GET"])
def verify_webhook():
    # Get parameters from the request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    # Check if the token matches
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    else:
        return "Forbidden", 403

@routes_bp.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    entry = data['entry'][0]
    changes = entry['changes'][0]
    value = changes['value']
    messages = value['messages'][0]
    incoming_msg = messages['text']['body'].strip()
    sender_id = messages['from']
    user_name = value['contacts'][0]['profile']['name']

    # Variável para armazenar o nome do serviço
    service_name = None

    if incoming_msg:
        # Check for greetings and keywords
        greetings = ["oi", "boa tarde", "bom dia", "boa noite", "ola", "olá"]
        keywords = ["agendar", "horário", "cabelo", "unha", "arrumar cabelo", "fazer unha"]

        if any(greeting in incoming_msg.lower() for greeting in greetings):
            reply = "Olá, eu sou o assistente do Studio Nice Hair, como posso ajudar?"
            send_whatsapp_message(sender_id, reply)
            # Verifique se a mensagem contém uma das palavras-chave após o reply
            if any(keyword in incoming_msg.lower() for keyword in keywords):
                service_name = next(keyword for keyword in keywords if keyword in incoming_msg.lower())
                send_subservices_menu(sender_id, service_name)
        elif any(keyword in incoming_msg.lower() for keyword in keywords):
            # Send interactive menu for services
            service_name = next(keyword for keyword in keywords if keyword in incoming_msg.lower())
            send_subservices_menu(sender_id, service_name)
        elif incoming_msg.lower() in ["cabelo", "manicure"]:
            # Send subservices menu based on the chosen service
            service_name = incoming_msg.lower()
            send_subservices_menu(sender_id, service_name)
        elif incoming_msg.lower() in ["corte", "serum", "escova", "unha_padrao", "alongamento"]:
            # Check availability for the chosen subservice
            service_name = incoming_msg.lower()
            service_time = mongo_client_caller.get_service_time(service_name)
            available_slots = mongo_client_caller.check_availability(service_name, service_time)
            send_available_slots_menu(sender_id, service_name, available_slots)
        elif incoming_msg.lower().startswith("confirmar"):
            # Extract date and hour from the message
            _, date, hour = incoming_msg.split()
            service_value = mongo_client_caller.get_service_value(service_name) 
            service_time = mongo_client_caller.get_service_time(service_name)
            mongo_client_caller.save_appointment(user_name, sender_id, service_name, service_value, service_time, date, hour)
            send_whatsapp_message(sender_id, f"Seu agendamento para {service_name} foi confirmado para {date} às {hour}. Obrigado e tenha um bom dia!")
        else:
            # Pass the user's message to the Assistants API
            reply = openai_client.get_assistant_response(incoming_msg)
            send_whatsapp_message(sender_id, reply)
    else:
        send_whatsapp_message(sender_id, "Desculpe, não entendi sua mensagem.")

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.register_blueprint(routes_bp)
    app.run(port=5000)
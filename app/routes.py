from flask import Flask, Blueprint, request, jsonify
from app.services.openai_service import OpenAIClient
from app.services.mongo_service import MongoDBClient
from app.utils.whatsapp_utils import send_whatsapp_message, send_subservices_menu, send_available_slots_menu
# from app.utils.test_utils import send_test_message, send_test_subservices_menu
from dotenv import load_dotenv
import os
import logging
from app.handlers.appointment_handlers import (
    handle_cancel_appointment,
    handle_service_availability,
    handle_confirm_appointment,
    handle_change_appointment,
    handle_get_employee,
    handle_get_services,
    handle_get_role_services
)
load_dotenv()

app = Flask(__name__)

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAIClient(api_key=openai_api_key)

mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")
mongo_client_caller = MongoDBClient(uri=mongo_uri, db_name=mongo_db_name)

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

user_slots = {}
name_service = {}
selected_slots = {}

routes_bp = Blueprint('routes', __name__)

@routes_bp.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    else:
        return "Forbidden", 403

@routes_bp.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Log the incoming request payload
        data = request.get_json()

        # Validate the payload structure
        if not data or 'entry' not in data or not data['entry']:
            logging.error("Invalid or empty payload received.")
            return jsonify({"error": "Invalid or empty payload."}), 400

        entry = data['entry'][0]
        if 'changes' not in entry or not entry['changes']:
            logging.error("Missing 'changes' in payload.")
            return jsonify({"error": "Missing 'changes' in payload."}), 400

        changes = entry['changes'][0]
        if 'value' not in changes:
            logging.error("Missing 'value' in payload.")
            return jsonify({"error": "Missing 'value' in payload."}), 400

        value = changes['value']
        # Check if the payload contains messages
        if 'messages' in value and value['messages']:
            messages = value['messages'][0]
            if 'text' in messages:
                incoming_msg = messages['text']['body'].strip()
            if 'interactive' in messages:   
                incoming_msg = messages['interactive']
            sender_id = messages['from']
            user_name = value['contacts'][0]['profile']['name']

            # Process the message (existing logic)
            return process_incoming_message(incoming_msg, sender_id, user_name)

        else:
            logging.warning("No messages found in payload.")
            return jsonify({"status": "No messages to process."}), 200

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

def process_incoming_message(incoming_msg, sender_id, user_name):
    service_name = None

    if incoming_msg:
        try:
            greetings = ["oi", "boa tarde", "bom dia", "boa noite", "ola", "olá"]
            cancel_keywords = ["cancelar", "desmarcar", "remover agendamento"]
            keywords = handle_get_role_services()
            update_keywords = ["alterar", "mudar", "trocar"]
            if isinstance(incoming_msg, dict) and 'button_reply' in incoming_msg:
                # Capturar a escolha do botão
                selected_option = incoming_msg['button_reply']['id']
                # Verificar se é uma ação de navegação
                user_slots["employee"] = selected_option
                if selected_option in [service["name"] for service in handle_get_services()]:
                    return jsonify(handle_service_availability(sender_id, incoming_msg))
                logging.info(f"Usuário escolheu a opção: {selected_option}")
                service_name = selected_slots["service_name"]
                return jsonify(send_subservices_menu(sender_id, service_name))
            elif 'list_reply' in incoming_msg:
                # Capturar a escolha da lista
                selected_option = incoming_msg['list_reply']['id']
                print(f"selected_option: {selected_option}")
                if selected_option.startswith("next_page_"):
                    next_page = int(selected_option.split("_")[-1])
                    return jsonify(send_available_slots_menu(sender_id, selected_slots["service_name"], selected_slots["available_slots"], page=next_page))
                elif selected_option.startswith("previous_page_"):
                    previous_page = int(selected_option.split("_")[-1])
                    return jsonify(send_available_slots_menu(sender_id, selected_slots["service_name"], selected_slots["available_slots"], page=previous_page))
                user_slots["employee"] = selected_option                
                if selected_option in [service["name"] for service in handle_get_services()]:
                    return jsonify(handle_service_availability(sender_id, incoming_msg))
                logging.info(f"Usuário escolheu a opção da lista: {selected_option}")
                service_name = selected_slots["service_name"]
                # Redirecionar para o menu de subserviços
                return jsonify(send_subservices_menu(sender_id, service_name))
                # return jsonify(send_test_subservices_menu(sender_id, service_name)) 
            # Process normal text messages
            if isinstance(incoming_msg, str):
                if any(greeting in incoming_msg.lower() for greeting in greetings):
                    reply = "Olá, eu sou o assistente de agendamento, qual serviço deseja agendar?"
                    return jsonify(send_whatsapp_message(sender_id, reply))
                    # return jsonify(send_test_message(sender_id, reply))
                elif any(keyword in incoming_msg.lower() for keyword in cancel_keywords):
                    return jsonify(handle_cancel_appointment(sender_id))
                elif any(keyword in incoming_msg.lower() for keyword in keywords):
                    service_name = next(keyword for keyword in keywords if keyword in incoming_msg.lower())
                    selected_slots["service_name"] = service_name
                    return jsonify(handle_get_employee(sender_id, service_name))                        
                elif incoming_msg.lower() == "sim":
                    employer_name = user_slots["employee"]
                    return jsonify(handle_confirm_appointment(sender_id, user_name, employer_name))
                elif any(keyword in incoming_msg.lower() for keyword in update_keywords):
                    return jsonify(handle_change_appointment(sender_id))
                else:
                    reply = openai_client.get_assistant_response(incoming_msg)
                    return jsonify(send_whatsapp_message(sender_id, reply))
                    # return jsonify(send_test_message(sender_id, reply))
            else:
                logging.warning("Message format not recognized.")
                return jsonify({"status": "Message format not recognized."}), 400
        except Exception as e:
            logging.error(f"Erro inesperado no processamento da mensagem: {e}")
            return jsonify(send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro inesperado. Tente novamente mais tarde."))
            # return jsonify(send_test_message(sender_id, "Desculpe, ocorreu um erro inesperado. Tente novamente mais tarde."))

if __name__ == '__main__':
    app.register_blueprint(routes_bp)
    app.run(port=5000)
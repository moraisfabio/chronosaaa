from flask import Flask, Blueprint, request, jsonify
from app.services.openai_service import OpenAIClient
from app.services.mongo_service import MongoDBClient
from app.utils.whatsapp_utils import send_whatsapp_message, send_subservices_menu
# from app.utils.test_utils import send_test_message, send_test_subservices_menu
from dotenv import load_dotenv
import os
import logging
from app.handlers.appointment_handlers import (
    handle_cancel_appointment,
    handle_service_availability,
    handle_confirm_appointment,
    handle_change_appointment
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
        data = request.get_json()
        entry = data['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']
        messages = value['messages'][0]
        incoming_msg = messages['text']['body'].strip()
        sender_id = messages['from']
        user_name = value['contacts'][0]['profile']['name']

        service_name = None

    except Exception as e:
        logging.error(f"Erro ao processar a requisição inicial: {e}")
        return jsonify(send_test_message(sender_id, "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente mais tarde."))
        #return jsonify(send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente mais tarde."))

    if incoming_msg:
        try:
            greetings = ["oi", "boa tarde", "bom dia", "boa noite", "ola", "olá"]
            cancel_keywords = ["cancelar", "desmarcar", "remover agendamento"]
            keywords = ["agendar", "horário", "cabelo", "unha", "arrumar cabelo", "fazer unha"]
            update_keywords = ["alterar", "mudar", "trocar"]

            if any(greeting in incoming_msg.lower() for greeting in greetings):
                reply = "Olá, eu sou o assistente do Studio X, como posso ajudar?"
                return jsonify(send_whatsapp_message(sender_id, reply))
                # return jsonify(send_test_message(sender_id, reply))
            elif any(keyword in incoming_msg.lower() for keyword in cancel_keywords):
                return jsonify(handle_cancel_appointment(sender_id))
            elif any(keyword in incoming_msg.lower() for keyword in keywords):
                service_name = next(keyword for keyword in keywords if keyword in incoming_msg.lower())
                return jsonify(send_subservices_menu(sender_id, service_name))
                # return jsonify(send_test_subservices_menu(sender_id, service_name))
            elif incoming_msg.lower() in ["corte", "serum", "escova", "unha_padrao", "alongamento"]:
                return jsonify(handle_service_availability(sender_id, incoming_msg.lower()))
            elif incoming_msg.lower() == "sim":
                return jsonify(handle_confirm_appointment(sender_id, user_name))
            elif any(keyword in incoming_msg.lower() for keyword in update_keywords):
                return jsonify(handle_change_appointment(sender_id))
            else:
                reply = openai_client.get_assistant_response(incoming_msg)
                return jsonify(send_whatsapp_message(sender_id, reply))
                # return jsonify(send_test_message(sender_id, reply))
        except Exception as e:
            logging.error(f"Erro inesperado no processamento da mensagem: {e}")
            return jsonify(send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro inesperado. Tente novamente mais tarde."))
            # return jsonify(send_test_message(sender_id, "Desculpe, ocorreu um erro inesperado. Tente novamente mais tarde."))

if __name__ == '__main__':
    app.register_blueprint(routes_bp)
    app.run(port=5000)
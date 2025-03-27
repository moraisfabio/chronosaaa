from flask import Flask, Blueprint, request, jsonify
from app.services.openai_service import OpenAIClient
from app.services.mongo_service import MongoDBClient
# from app.utils.whatsapp_utils import send_whatsapp_message, send_subservices_menu, send_available_slots_menu, send_confirmation_menu
from app.utils.test_utils import send_test_message, send_test_subservices_menu, send_test_available_slots_menu, send_test_confirmation_menu
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

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

# Armazenamento temporário para horários disponíveis
user_slots = {}
name_service = {}
selected_slots = {}

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
        cancel_keywords = ["cancelar", "desmarcar", "remover agendamento"]

        if any(greeting in incoming_msg.lower() for greeting in greetings):
            reply = "Olá, eu sou o assistente do Studio X, como posso ajudar?"
            # send_whatsapp_message(sender_id, reply)
            response = send_test_message(sender_id, reply)
            return jsonify(response)
        elif any(keyword in incoming_msg.lower() for keyword in cancel_keywords):
            appointment = mongo_client_caller.get_appointment(sender_id)
            if appointment:
                # Concatenar a data e a hora em uma única string
                appointment_datetime_str = f"{appointment['date']} {appointment['hour']}"
                appointment_date = datetime.strptime(appointment_datetime_str, "%Y-%m-%d %H:%M")
                current_time = datetime.now()

                if appointment_date - current_time > timedelta(hours=48):
                    mongo_client_caller.delete_appointment(sender_id)
                    # send_whatsapp_message(sender_id, "Seu agendamento foi cancelado com sucesso.")
                    response = send_test_message(sender_id, "Seu agendamento foi cancelado com sucesso.")
                    return jsonify(response)
                else:
                    # send_whatsapp_message(sender_id, "Desculpe, não é possível cancelar o agendamento com menos de 48 horas de antecedência.")
                    response = send_test_message(sender_id, "Desculpe, não é possível cancelar o agendamento com menos de 48 horas de antecedência.")
                    return jsonify(response)
            else:
                # send_whatsapp_message(sender_id, "Você não possui nenhum agendamento para cancelar.")
                response = send_test_message(sender_id, "Você não possui nenhum agendamento para cancelar.")
                return jsonify(response)
        elif any(keyword in incoming_msg.lower() for keyword in keywords):
            # Send interactive menu for services
            service_name = next(keyword for keyword in keywords if keyword in incoming_msg.lower())
            # send_subservices_menu(sender_id, service_name)
            response = send_test_subservices_menu(sender_id, service_name)
            return jsonify(response)
        elif incoming_msg.lower() in ["corte", "serum", "escova", "unha_padrao", "alongamento"]:
            
            # Check availability for the chosen subservice
            service_name = incoming_msg.lower()
            service_time = mongo_client_caller.get_service_time(service_name)
            available_slots = mongo_client_caller.check_availability(service_name, service_time)
           
            # Salvar os horários disponíveis no armazenamento temporário
            user_slots[sender_id] = available_slots
            name_service[sender_id] = service_name

            # Gerar a mensagem com os horários disponíveis usando o assistente do ChatGPT
            slots_message = "Aqui estão os horários disponíveis para o serviço {}:\n".format(service_name.capitalize())
            for index, slot in enumerate(available_slots, start=1):
                slots_message += f"{index} - {slot['date']} - {slot['time']}\n"
            slots_message += "Por favor, escolha o número correspondente ao horário desejado."

            # # Obter a resposta do assistente do ChatGPT
            # reply = openai_client.get_assistant_response(slots_message)
            
            # send_available_slots_menu(sender_id, service_name, available_slots)
            response = send_test_available_slots_menu(sender_id, service_name, available_slots)
            
            return jsonify(response)
        elif incoming_msg.isdigit():
            # Recuperar os horários disponíveis do armazenamento temporário
            available_slots = user_slots.get(sender_id, [])
            # Handle numeric input for selecting a slot
            slot_index = int(incoming_msg) - 1  # Convert input to zero-based index
            if 0 <= slot_index < len(available_slots):
                selected_slot = available_slots[slot_index]
                selected_slots[sender_id] = selected_slot  # Salvar o horário selecionado
                date = selected_slot["date"]
                hour = selected_slot["time"]
                service_name = name_service.get(sender_id)

                # Enviar menu de confirmação
                response = send_test_confirmation_menu(sender_id, service_name, date, hour)
                # response = send_confirmation_menu(sender_id, service_name, date, hour)
                return jsonify(response)
            else:
                response = send_test_message(sender_id, "Número inválido. Por favor, escolha um número válido da lista de horários disponíveis.")
                # response = send_whatsapp_message(sender_id, "Número inválido. Por favor, escolha um número válido da lista de horários disponíveis.")
                return jsonify(response)
        elif incoming_msg.lower() == "sim":
            # Recuperar o horário selecionado do armazenamento temporário
            selected_slot = selected_slots.get(sender_id)
            if selected_slot:
                date = selected_slot["date"]
                hour = selected_slot["time"]
                service_name = name_service.get(sender_id)
                service_value = mongo_client_caller.get_service_value(service_name)
                service_time = mongo_client_caller.get_service_time(service_name)

                # Salvar o agendamento no banco de dados
                mongo_client_caller.save_appointment(user_name, sender_id, service_name, service_value, service_time, date, hour)

                # Enviar mensagem de confirmação
                response = send_test_message(sender_id, f"Seu agendamento para {service_name} foi confirmado para {date} às {hour}. Obrigado e tenha um bom dia!")
                # response = send_whatsapp_message(sender_id, f"Seu agendamento para {service_name} foi confirmado para {date} às {hour}. Obrigado e tenha um bom dia!")
                return jsonify(response)
            else:
                # Caso não haja horário selecionado, enviar mensagem de erro
                response = send_test_message(sender_id, "Não foi possível confirmar o agendamento. Por favor, selecione um horário primeiro.")
                # response = send_whatsapp_message(sender_id, "Não foi possível confirmar o agendamento. Por favor, selecione um horário primeiro.")
                return jsonify(response)
        elif incoming_msg.lower().startswith("voltar"):
            # Resend available slots menu
            available_slots = user_slots.get(sender_id, [])
            service_name = name_service.get(sender_id)
            response = send_test_available_slots_menu(sender_id, service_name, available_slots)
            # response = send_available_slots_menu(sender_id, service_name, available_slots)
            return jsonify(response)
        else:
            # Pass the user's message to the Assistants API
            reply = openai_client.get_assistant_response(incoming_msg)
            # send_whatsapp_message(sender_id, reply)
            send_test_message(sender_id, reply)
    else:
        # send_whatsapp_message(sender_id, "Desculpe, não entendi sua mensagem.")
        # Resposta padrão
        response = send_test_message(sender_id, "Desculpe, não entendi sua mensagem.")
        send_test_message(sender_id, response)

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.register_blueprint(routes_bp)
    app.run(port=5000)
from flask import Flask, Blueprint, request, jsonify
from app.services.openai_service import OpenAIClient
from app.services.mongo_service import MongoDBClient
from app.utils.whatsapp_utils import (
    send_whatsapp_message, 
    send_subservices_menu, 
    send_available_slots_menu, 
    send_confirmation_menu, 
    # deactivate_conversation, 
    # activate_conversation,
    send_day_slots_menu
)

from dotenv import load_dotenv
import os
import logging
import time
from app.handlers.appointment_handlers import (
    handle_cancel_appointment,
    handle_service_availability,
    handle_confirm_appointment,
    handle_change_appointment,
    handle_get_employee,
    handle_get_services,
    handle_get_role_services,
    handle_service_availabilit_for_employees
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
active_conversations = {}
last_interaction = {}

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
     # Verificar se a conversa está ativa e se o tempo de inatividade ultrapassou 30 segundos
    # current_time = time.time()
    # if sender_id in last_interaction:
    #     time_elapsed = current_time - last_interaction[sender_id]
    #     if time_elapsed > 60:
    #         # Desativar a conversa e enviar mensagem ao cliente
    #         send_whatsapp_message(sender_id, "Esta conversa foi encerrada. Por favor, inicie uma nova conversa enviando um 'oi' caso deseje realizar um agendamento.")
    #         deactivate_conversation(sender_id)
    #         active_conversations.clear()
    #         return jsonify({"status": "Conversation deactivated."}), 200

    # # Atualizar o timestamp da última interação
    # last_interaction[sender_id] = current_time

    if incoming_msg:
        try:
            greetings = ["oi", "boa tarde", "bom dia", "boa noite", "ola", "olá"]
            cancel_keywords = ["cancelar", "desmarcar", "remover agendamento"]
            keywords = handle_get_role_services()
            update_keywords = ["alterar", "mudar", "trocar"]

            # print(active_conversations)
            # Verificar se a conversa está inativa e o cliente enviou "oi"
            # if sender_id not in active_conversations:
            #     activate_conversation(sender_id)
            #     active_conversations["sender_id"] = sender_id
            #     send_whatsapp_message(sender_id, "Conversa reativada! Como posso ajudá-lo? Por favor, informe o serviço que deseja agendar.")
            #     return jsonify({"status": "Conversation reactivated."}), 200
            if isinstance(incoming_msg, dict):
                if 'list_reply' in incoming_msg:
                    selected_option = incoming_msg['list_reply']['id']
                    if selected_option.startswith("employee_"): 
                        user_slots["employee"] = selected_option.split("employee_")[1]                
                        service_name = selected_slots["service_name"]
                        return jsonify(send_subservices_menu(sender_id, service_name))
                    
                    if selected_option.startswith("next_page_"):
                        next_page = int(selected_option.split("_")[-1])
                        available_slots = selected_slots["available_slots"]
                        service_name = selected_slots["service_name"]
                        return jsonify(send_available_slots_menu(sender_id, service_name, available_slots, page=next_page))
                
                    elif selected_option.startswith("previous_page_"):
                        previous_page = int(selected_option.split("_")[-1])
                        available_slots = selected_slots["available_slots"]
                        service_name = selected_slots["service_name"]
                        return jsonify(send_available_slots_menu(sender_id, service_name, available_slots, page=previous_page))
                    
                    if selected_option in [service["name"] for service in handle_get_services()]:
                        selected_employee = user_slots["employee"]
                        selected_slots["available_slots"] = handle_service_availability(sender_id, incoming_msg, selected_employee)
                        return jsonify(send_available_slots_menu(sender_id, selected_slots["service_name"], selected_slots["available_slots"]))
                    
                    if selected_option.startswith("slot_"):
                        selected_data = selected_option.split("slot_")[1]
                        selected_date, selected_hour = selected_data.split(" ")
                        return jsonify(send_confirmation_menu(sender_id, selected_date, selected_hour))  
                    logging.info(f"Usuário escolheu a opção da lista: {selected_option}")     
                                  
                if 'button_reply' in incoming_msg:
                    selected_option = incoming_msg['button_reply']['id']
                    if selected_option.startswith("confirmar_"):
                        _, selected_date, selected_hour = selected_option.split("_")
                        selected_employee = user_slots["employee"]
                        return handle_confirm_appointment(sender_id, user_name, selected_employee, selected_date, selected_hour)

                    elif selected_option == "voltar":
                        # Voltar para a seleção de horários
                        available_slots = selected_slots["available_slots"]
                        service_name = selected_slots["service_name"]
                        return send_available_slots_menu(sender_id, service_name, available_slots)
                    
                    selected_slots.clear()
                    logging.info(f"Usuário escolheu a opção: {selected_option}")

            # Process normal text messages
            if isinstance(incoming_msg, str):
                if 'active' not in selected_slots and incoming_msg.lower() not in greetings:    
                    services = handle_get_services() 
                    role_name = None
                    service_name = None
                    for service in services:
                        if service["role_service"].lower() in incoming_msg.lower():
                            role_name = service["role_service"]
                            service_name = service["name"]
                            break    
                    # Identificar o dia da semana mencionado
                    days_of_week = {
                        "segunda": 0,
                        "terça": 1,
                        "quarta": 2,
                        "quinta": 3,
                        "sexta": 4,
                        "sábado": 5,
                        "domingo": 6
                    }
                    day_of_week = next((day for day in days_of_week if day in incoming_msg.lower()), None)
                    if service_name and day_of_week:
                        # Converter o dia da semana para uma data específica
                        today = time.localtime()
                        target_date = None
                        for i in range(7):
                            potential_date = time.localtime(time.mktime(today) + i * 86400)  # Adiciona dias em segundos
                            if potential_date.tm_wday == days_of_week[day_of_week]:
                                target_date = time.strftime("%Y-%m-%d", potential_date)
                                break

                        if target_date:
                            # Buscar horários disponíveis para o serviço e a data
                            available_slots = handle_service_availabilit_for_employees(sender_id,service_name, role_name)
                            # Filtrar os horários disponíveis para a data solicitada
                            day_slots = [slot for slot in available_slots if isinstance(slot, dict) and slot.get("date") == target_date]
                            if day_slots:
                                # Enviar o menu interativo com os horários disponíveis
                                return jsonify(send_day_slots_menu(sender_id, service_name, day_slots, target_date, day_of_week))
                            else:
                                # Caso não haja horários disponíveis, buscar o próximo dia com horários livres
                                next_available_slot = next((slot for slot in available_slots if isinstance(slot, dict) and slot.get("date") > target_date), None)
                                if next_available_slot:
                                    next_date = next_available_slot["date"]
                                    next_day_of_week = time.strftime("%A", time.strptime(next_date, "%Y-%m-%d"))
                                    next_day_slots = [slot for slot in available_slots if slot.get("date") == next_date]

                                    # Enviar o menu interativo com os horários do próximo dia disponível
                                    return jsonify(send_day_slots_menu(sender_id, service_name, next_day_slots, next_date, next_day_of_week))
                                else:
                                    # Informar que não há horários disponíveis em nenhuma data futura
                                    return jsonify(send_whatsapp_message(sender_id, f"Desculpe, não há horários disponíveis para {service_name.capitalize()} na {day_of_week.capitalize()} ({target_date}) ou em datas futuras."))
                        else:
                            # Informar que não foi possível identificar a data
                            return jsonify(send_whatsapp_message(sender_id, "Desculpe, não consegui identificar a data solicitada. Por favor, tente novamente informando o dia da semana."))                
                if any(greeting in incoming_msg.lower() for greeting in greetings):
                    selected_slots["active"] = True
                    reply = "Oi, eu sou o assistente de agendamento, qual serviço deseja agendar?"
                    return jsonify(send_whatsapp_message(sender_id, reply))
                
                elif any(keyword in incoming_msg.lower() for keyword in cancel_keywords):
                    return jsonify(handle_cancel_appointment(sender_id))
               
                elif any(keyword in incoming_msg.lower() for keyword in keywords):
                    service_name = next(keyword for keyword in keywords if keyword in incoming_msg.lower())
                    selected_slots["service_name"] = service_name
                    return jsonify(handle_get_employee(sender_id, service_name))                        
                
                elif any(keyword in incoming_msg.lower() for keyword in update_keywords):
                    return jsonify(handle_change_appointment(sender_id))
                
                else:
                    # reply = openai_client.get_assistant_response(incoming_msg)
                    reply = "Desculpe, não consegui entender sua mensagem. Você pode me ajudar a entender melhor? Por favor, digite o serviço que deseja para seguirmos com o agendamento."
                    return jsonify(send_whatsapp_message(sender_id, reply))
            else:
                logging.warning("Message format not recognized.")
                
            return jsonify({"status": "Message format not recognized."}), 400
        except Exception as e:
            logging.error(f"Erro inesperado no processamento da mensagem: {e}")
            return jsonify(send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro inesperado. Tente novamente mais tarde."))


if __name__ == '__main__':
    app.register_blueprint(routes_bp)
    app.run(port=5000)
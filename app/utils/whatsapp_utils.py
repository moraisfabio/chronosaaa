import logging
import requests
import os
from dotenv import load_dotenv
from app.services.mongo_service import MongoDBClient

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

# Inicialize o cliente MongoDB
mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")
mongo_client_caller = MongoDBClient(uri=mongo_uri, db_name=mongo_db_name)

def send_whatsapp_message(recipient_id, message):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {
            "body": message
        }
    }
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        logging.info(f"Mensagem enviada com sucesso para {recipient_id}.")
    else:
        logging.error(f"Erro ao enviar mensagem para {recipient_id}: {response.text}")
    return response.json()

def send_subservices_menu(recipient_id, service):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    services = mongo_client_caller.db['services'].find({"name": {"$regex": service, "$options": "i"}})
    buttons = []
    for svc in services:
        buttons.append({
            "type": "reply",
            "reply": {
                "id": svc["name"],
                "title": f"{svc['name'].capitalize()} - {svc['value']} BRL - {svc['time']} min"
            }
        })
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": f"Por favor, escolha um subserviço de {service}:"
            },
            "action": {
                "buttons": buttons
            }
        }
    }
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        logging.info(f"Mensagem enviada com sucesso para {recipient_id}.")
    else:
        logging.error(f"Erro ao enviar mensagem para {recipient_id}: {response.text}")
    return response.json()

def send_available_slots_menu(recipient_id, service_name, available_slots):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    message_body = f"Aqui estão os horários disponíveis para o serviço {service_name.capitalize()}:\n"

    buttons = []
    for slot in available_slots:
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"{slot['date']} {slot['time']}",
                "title": f"{slot['date']} - {slot['time']}"
            }
        })
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": message_body
            },
            "action": {
                "buttons": buttons
            }
        }
    }

    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        logging.info(f"Mensagem enviada com sucesso para {recipient_id}.")
    else:
        logging.error(f"Erro ao enviar mensagem para {recipient_id}: {response.text}")
    return response.json()

def send_confirmation_menu(sender_id, service_name, date, hour):
    message = f"Você escolheu {service_name} para {date} às {hour}. Deseja confirmar o agendamento ou voltar para escolher outra data?"
    options = [
        {"title": "Confirmar", "id": f"confirmar {date} {hour}"},
        {"title": "Voltar", "id": "voltar"}
    ]
    send_whatsapp_message(sender_id, message, options)
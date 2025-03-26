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
    return response.json()

def send_interactive_menu(recipient_id):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "Por favor, escolha um serviço:"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cabelo",
                            "title": "Cabelo"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "unha",
                            "title": "Unha"
                        }
                    }
                ]
            }
        }
    }
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
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
    return response.json()

def send_available_slots_menu(recipient_id, service_name, available_slots):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
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
                "text": f"Os horários disponíveis para {service_name} são:"
            },
            "action": {
                "buttons": buttons
            }
        }
    }
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    return response.json()
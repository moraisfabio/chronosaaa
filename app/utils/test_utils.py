import os
from dotenv import load_dotenv
from app.services.mongo_service import MongoDBClient

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Inicialize o cliente MongoDB
mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")
mongo_client_caller = MongoDBClient(uri=mongo_uri, db_name=mongo_db_name)

def send_test_message(recipient_id, message):
    """Simula o envio de uma mensagem de texto."""
    response = {
        "recipient_id": recipient_id,
        "message": message
    }
    return response

def send_test_subservices_menu(recipient_id, service):
    """Simula o envio de um menu de subserviços."""
    services = mongo_client_caller.db['services'].find({"name": {"$regex": service, "$options": "i"}})
    buttons = []
    for svc in services:
        buttons.append({
            "id": svc["name"],
            "title": f"{svc['name'].capitalize()} - {svc['value']} BRL - {svc['time']} min"
        })
    response = {
        "recipient_id": recipient_id,
        "type": "menu",
        "service": service,
        "buttons": buttons
    }
    return response

def send_test_available_slots_menu(recipient_id, service_name, available_slots):
    """Simula o envio de um menu de horários disponíveis."""
    buttons = []
    for slot in available_slots:
        buttons.append({
            "id": f"{slot['date']} {slot['time']}",
            "title": f"{slot['date']} - {slot['time']}"
        })
    response = {
        "recipient_id": recipient_id,
        "type": "menu",
        "service_name": service_name,
        "available_slots": buttons
    }
    return response

def send_test_confirmation_menu(sender_id, service_name, date, hour):
    """Simula o envio de um menu de confirmação."""
    response = {
        "recipient_id": sender_id,
        "type": "confirmation",
        "message": f"Você escolheu {service_name} para {date} às {hour}. Deseja confirmar o agendamento ou voltar para escolher outra data?",
        "options": [
            {"title": "Confirmar", "id": f"sim {date} {hour}"},
            {"title": "Voltar", "id": "voltar"}
        ]
    }
    return response
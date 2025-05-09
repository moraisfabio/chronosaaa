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

# Dicionário para rastrear o estado da conversa ativa
active_conversations = {}

def send_whatsapp_message(recipient_id, message):
    # Verificar se o recipient_id está ativo
    # if not active_conversations.get(recipient_id, False):
    #     logging.info(f"Mensagem ignorada para {recipient_id}, pois a conversa não está ativa.")
    #     return {"status": "ignored", "message": "Conversa não está ativa."}

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

def send_finish_message(recipient_id, message):
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
    # deactivate_conversation(recipient_id)
    if response.status_code == 200:
        logging.info(f"Mensagem enviada com sucesso para {recipient_id}.")
    else:
        logging.error(f"Erro ao enviar mensagem para {recipient_id}: {response.text}")
    return response.json()

# def activate_conversation(recipient_id):
#     """Ativar a conversa para um recipient_id específico."""
#     active_conversations[recipient_id] = True
#     logging.info(f"Conversa ativada para {recipient_id}.")

# def deactivate_conversation(recipient_id):
#     """Desativar a conversa para um recipient_id específico."""
#     if recipient_id in active_conversations:
#         del active_conversations[recipient_id]
#         logging.info(f"Conversa encerrada para {recipient_id}.")

def send_subservices_menu(recipient_id, service):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    if service == "unha":
        service = "manicure"
    services = mongo_client_caller.db['services'].find({"role_service": {"$regex": service, "$options": "i"}})

    list_items = []
    for svc in services:
        list_items.append({
            "id": svc["name"],
            "title": f"{svc['name'].capitalize()}",
        })
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": f"Serviços disponíveis para {service.capitalize()}:"
            },
            "body": {
                "text": f"Por favor, escolha um subserviço de {service.capitalize()}:"
            },
            "action": {
                "button": "Ver serviços",
                "sections": [
                    {
                        "title": "Serviços Disponíveis",
                        "rows": list_items
                    }
                ]
            }
        }
    }
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        logging.info(f"Mensagem enviada com sucesso para {recipient_id}.")
    else:
        logging.error(f"Erro ao enviar mensagem para {recipient_id}: {response.text}")
    return response.json()

def send_available_slots_menu(recipient_id, service_name, available_slots, page=1):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Definir o número máximo de itens por página
    max_items_per_page = 8  # Reservar 2 itens para navegação (Próxima Página e Página Anterior)
    total_pages = (len(available_slots) + max_items_per_page - 1) // max_items_per_page

    # Calcular o índice inicial e final para a página atual
    start_index = (page - 1) * max_items_per_page
    end_index = start_index + max_items_per_page
    current_page_slots = available_slots[start_index:end_index]

    # Definir o texto do cabeçalho (limitar a 60 caracteres)
    header_text = f"Horários disponíveis para {service_name}"
    if len(header_text) > 60:
        header_text = header_text[:57] + "..."
    message_body = f"Aqui estão os horários disponíveis para o serviço {service_name}:\n"

    # Criar os itens da lista
    rows = []
    for slot in current_page_slots:
        rows.append({
            "id": f"slot_{slot['date']} {slot['time']}",
            "title": f"{slot['date']} - {slot['time']}",
        })

    # Adicionar opções de navegação
    if page < total_pages:
        rows.append({
            "id": f"next_page_{page + 1}",
            "title": "Próxima Página",
            "description": f"Veja mais horários (Página {page + 1} de {total_pages})"
        })
    if page > 1:
        rows.append({
            "id": f"previous_page_{page - 1}",
            "title": "Página Anterior",
            "description": f"Voltar para a página {page - 1}"
        })

    # Garantir que o número total de itens não exceda 10
    rows = rows[:10]

    # Criar a seção principal
    sections = [
        {
            "title": "Horários Disponíveis",
            "rows": rows
        }
    ]

    # Criar o payload da mensagem interativa
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": header_text
            },
            "body": {
                "text": message_body
            },
            "action": {
                "button": "Ver horários",
                "sections": sections
            }
        }
    }

    # Enviar a mensagem para a API do WhatsApp
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        logging.info(f"Mensagem enviada com sucesso para {recipient_id}.")
    else:
        logging.error(f"Erro ao enviar mensagem para {recipient_id}: {response.text}")
    return response.json()

def send_confirmation_menu(sender_id, date, hour):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Definir a mensagem de confirmação
    message_body = f"Você escolheu a data {date} às {hour}. Deseja confirmar o agendamento ou voltar para escolher outra data?"

    # Criar os botões
    buttons = [
        {
            "type": "reply",
            "reply": {
                "id": f"confirmar_{date}_{hour}",
                "title": "Confirmar"
            }
        },
        {
            "type": "reply",
            "reply": {
                "id": "voltar",
                "title": "Voltar"
            }
        }
    ]

    # Criar o payload da mensagem interativa
    data = {
        "messaging_product": "whatsapp",
        "to": sender_id,
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

    # Enviar a mensagem para a API do WhatsApp
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        logging.info(f"Mensagem de confirmação enviada com sucesso para {sender_id}.")
    else:
        logging.error(f"Erro ao enviar mensagem de confirmação para {sender_id}: {response.text}")
    return response.json()

def send_available_employees_menu(recipient_id, available_slots):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Definir o corpo da mensagem
    message_body = "Escolha um colaborador disponível:\n"

    # Criar os itens da lista
    list_items = []
    for slot in available_slots:
        list_items.append({
            "id": f"employee_{slot['name']}",
            "title": f"{slot['name'].capitalize()}",
        })

    # Criar o payload da mensagem interativa
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Colaboradores Disponíveis"
            },
            "body": {
                "text": message_body
            },
            "action": {
                "button": "Ver colaboradores",
                "sections": [
                    {
                        "title": "Colaboradores",
                        "rows": list_items
                    }
                ]
            }
        }
    }

    # Enviar a mensagem para a API do WhatsApp
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        logging.info(f"Mensagem enviada com sucesso para {recipient_id}.")
    else:
        logging.error(f"Erro ao enviar mensagem para {recipient_id}: {response.text}")
    return response.json()

def send_day_slots_menu(recipient_id, service_name, day_slots, target_date, day_of_week, page=1):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # Agrupar os horários por colaborador
    grouped_slots = {}
    for slot in day_slots:
        employee = slot.get("employee")
        if employee not in grouped_slots:
            grouped_slots[employee] = []
        grouped_slots[employee].append(slot)

    # Selecionar os 3 horários mais próximos para cada colaborador
    filtered_slots = []
    for employee, slots in grouped_slots.items():
        # Ordenar os horários por data e hora
        sorted_slots = sorted(slots, key=lambda x: (x["date"], x["time"]))
        # Adicionar os 3 primeiros horários
        filtered_slots.extend(sorted_slots[:3])

    # Paginação
    max_items_per_page = 10  # Limite máximo de itens por página
    total_pages = (len(filtered_slots) + max_items_per_page - 1) // max_items_per_page

    # Calcular o índice inicial e final para a página atual
    start_index = (page - 1) * max_items_per_page
    end_index = start_index + max_items_per_page
    current_page_slots = filtered_slots[start_index:end_index]

    # Definir o texto do cabeçalho (limitar a 60 caracteres)
    header_text = f"Horários disponíveis para {service_name}"
    if len(header_text) > 60:
        header_text = header_text[:57] + "..."
    message_body = f"Aqui estão os horários disponíveis para o serviço {service_name}:\n"

    # Criar os itens da lista
    rows = []
    for slot in current_page_slots:
        rows.append({
            "id": f"slot_{slot['date']}_{slot['time']}_{slot['employee']}",
            "title": f"{slot['time']} com {slot['employee']}",
            "description": f"Horário disponível em {slot['date']}"
        })

    # Adicionar opções de navegação
    if page < total_pages:
        rows.append({
            "id": f"next_page_{page + 1}",
            "title": "Próxima Página",
            "description": f"Veja mais horários (Página {page + 1} de {total_pages})"
        })
    if page > 1:
        rows.append({
            "id": f"previous_page_{page - 1}",
            "title": "Página Anterior",
            "description": f"Voltar para a página {page - 1}"
        })

    # Criar a seção principal
    sections = [
        {
            "title": f"Datas {day_of_week.capitalize()} ({target_date})",
            "rows": rows
        }
    ]

    # Criar o payload da mensagem interativa
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": header_text
            },
            "body": {
                "text": message_body
            },
            "action": {
                "button": "Ver horários",
                "sections": sections
            }
        }
    }

    # Enviar a mensagem para a API do WhatsApp
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)

    if response.status_code == 200:
        logging.info(f"Menu de horários enviado com sucesso para {recipient_id}.")
    else:
        logging.error(f"Erro ao enviar menu de horários para {recipient_id}: {response.text}")
    return response.json()
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from app.services.mongo_service import MongoDBClient
#from app.utils.test_utils import send_test_message, send_test_available_slots_menu, send_test_available_employees_menu
from app.utils.whatsapp_utils import send_whatsapp_message, send_available_employees_menu, send_finish_message

load_dotenv()
# Inicialize o cliente MongoDB
mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")
mongo_client_caller = MongoDBClient(uri=mongo_uri, db_name=mongo_db_name)

# Armazenamento temporário
user_slots = {}
name_service = {}
selected_slots = {}

def handle_cancel_appointment(sender_id):
    try:
        appointment = mongo_client_caller.get_appointment(sender_id)
        if appointment:
            appointment_datetime_str = f"{appointment['date']} {appointment['hour']}"
            appointment_date = datetime.strptime(appointment_datetime_str, "%Y-%m-%d %H:%M")
            current_time = datetime.now()

            if appointment_date - current_time > timedelta(hours=48):
                mongo_client_caller.delete_appointment(sender_id)
                return send_whatsapp_message(sender_id, "Seu agendamento foi cancelado com sucesso.")
            else:
                return send_whatsapp_message(sender_id, "Desculpe, não é possível cancelar o agendamento com menos de 48 horas de antecedência.")
        else:
            return send_whatsapp_message(sender_id, "Você não possui nenhum agendamento para cancelar.")
    except Exception as e:
        logging.error(f"Erro ao processar cancelamento de agendamento: {e}")
        return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao acessar os dados do agendamento. Tente novamente mais tarde.")

def handle_service_availabilit_for_employees(sender_id, service_name, role_name):
    
    try:
        # Obter os colaboradores que realizam o serviço
        collaborators = mongo_client_caller.db['employee'].find({"role": {"$regex": role_name, "$options": "i"}})
        if not collaborators:
            logging.warning(f"Nenhum colaborador encontrado para o serviço: {role_name}")
            return []

        # Obter os horários disponíveis para cada colaborador
        available_slots = []
        for collaborator in collaborators:
            service_time = mongo_client_caller.get_service_time(service_name)
            collaborator_slots = mongo_client_caller.check_availability(service_name, service_time, collaborator["name"].lower())

            for slot in collaborator_slots:
                available_slots.append({
                    "date": slot["date"],
                    "time": slot["time"],
                    "employee": collaborator["name"]
                })

        # Salvar os horários disponíveis no armazenamento temporário
        user_slots[sender_id] = available_slots
        name_service[sender_id] = service_name

        # Retornar os horários disponíveis
        return available_slots
    except Exception as e:
        logging.error(f"Erro ao verificar disponibilidade de horários: {e}")
        return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao verificar os horários disponíveis. Tente novamente mais tarde.")

def handle_service_availability(sender_id, service_name, collaborator_name):
    try:

        get_service_name = service_name.get('list_reply', {}).get('id')
        service_time = mongo_client_caller.get_service_time(get_service_name)
        available_slots = mongo_client_caller.check_availability(get_service_name, service_time, collaborator_name)

        # Salvar os horários disponíveis no armazenamento temporário
        user_slots[sender_id] = available_slots
        name_service[sender_id] = get_service_name

        # Enviar o menu interativo com os horários disponíveis
        return  available_slots
    except Exception as e:
        logging.error(f"Erro ao verificar disponibilidade de horários: {e}")
        return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao verificar os horários disponíveis. Tente novamente mais tarde.")      

def handle_confirm_appointment(sender_id, user_name, selected_employee, selected_date, selected_hour):
    try:

        if selected_employee:
            service_name = name_service.get(sender_id)
            service_value = mongo_client_caller.get_service_value(service_name)
            service_time = mongo_client_caller.get_service_time(service_name)

            # Salvar o agendamento no banco de dados com o nome do colaborador
            mongo_client_caller.save_appointment(
                user_name=user_name,
                user_phone=sender_id,
                service_name=service_name,
                service_value=service_value,
                service_time=service_time,
                date=selected_date,
                hour=selected_hour,
                employee_name=selected_employee
            )

            message = f"Seu agendamento foi confirmado para {selected_date} às {selected_hour} com o profissional {selected_employee.capitalize()}. Obrigado e tenha um bom dia!"
            return send_finish_message(sender_id,message)
        else:
            # return send_test_message(sender_id, "Não foi possível confirmar o agendamento. Por favor, selecione um horário e um profissional primeiro.")
            return send_whatsapp_message(sender_id, "Não foi possível confirmar o agendamento. Por favor, selecione um horário e um profissional primeiro.")
    except Exception as e:
        logging.error(f"Erro ao salvar agendamento: {e}")
        # return send_test_message(sender_id, "Desculpe, ocorreu um erro ao salvar o agendamento. Tente novamente mais tarde.")
        return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao salvar o agendamento. Tente novamente mais tarde.")

def handle_change_appointment(sender_id):
    try:
        # Recuperar o agendamento do cliente
        appointment = mongo_client_caller.get_appointment(sender_id)
        if appointment:
            # Concatenar a data e a hora em uma única string
            appointment_datetime_str = f"{appointment['date']} {appointment['hour']}"
            appointment_date = datetime.strptime(appointment_datetime_str, "%Y-%m-%d %H:%M")
            current_time = datetime.now()

            # Verificar se o prazo é maior que 24 horas
            if appointment_date - current_time > timedelta(hours=24):
                # Obter o serviço e os horários disponíveis
                service_name = appointment["service_name"]
                service_time = mongo_client_caller.get_service_time(service_name)
                available_slots = mongo_client_caller.check_availability(service_name, service_time, appointment["employee_name"])

                # Salvar os horários disponíveis no armazenamento temporário
                user_slots[sender_id] = available_slots
                name_service[sender_id] = service_name

                # Gerar a mensagem com os horários disponíveis
                slots_message = "Aqui estão os horários disponíveis para alteração do seu agendamento:\n"
                for index, slot in enumerate(available_slots, start=1):
                    slots_message += f"{index} - {slot['date']} - {slot['time']}\n"
                slots_message += "Por favor, escolha o número correspondente ao novo horário desejado."

                # Enviar a mensagem com os horários disponíveis
                return send_whatsapp_message(sender_id, slots_message)
                # return send_test_message(sender_id, slots_message)
            else:
                # Não é possível alterar com menos de 48 horas de antecedência
                return send_whatsapp_message(sender_id, "Desculpe, não é possível alterar o agendamento com menos de 48 horas de antecedência.")
                # return send_test_message(sender_id, "Desculpe, não é possível alterar o agendamento com menos de 48 horas de antecedência.")
        else:
            # Caso não exista um agendamento para o cliente
            return send_whatsapp_message(sender_id, "Você não possui nenhum agendamento para alterar.")
            # return send_test_message(sender_id, "Você não possui nenhum agendamento para alterar.")
    except Exception as e:
        logging.error(f"Erro ao processar alteração de agendamento: {e}")
        return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao acessar os dados do agendamento. Tente novamente mais tarde.")
        # return send_test_message(sender_id, "Desculpe, ocorreu um erro ao acessar os dados do agendamento. Tente novamente mais tarde.")
    
def handle_send_reminders_for_tomorrow():
    try:
        # Obter a data de amanhã (D+1)
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        # Buscar agendamentos para a data de amanhã
        appointments = mongo_client_caller.db['appointments'].find({"date": tomorrow_date})

        # Verificar se há agendamentos
        if not appointments:
            logging.info(f"Não há agendamentos para enviar lembretes em {tomorrow_date}.")
            return

        # Enviar mensagens de lembrete para cada agendamento
        for appointment in appointments:
            user_phone = appointment["user_phone"]
            service_name = appointment["service_name"]
            appointment_time = appointment["hour"]

            # Construir a mensagem de lembrete
            reminder_message = (
                f"Olá! Este é um lembrete do Studio X.\n"
                f"Você tem um agendamento para o serviço '{service_name}' amanhã, "
                f"às {appointment_time}.\n"
                f"Estamos ansiosos para atendê-lo!"
            )

            # Enviar a mensagem pelo WhatsApp
            # send_test_message(user_phone, reminder_message)
            send_whatsapp_message(user_phone, reminder_message)

        logging.info(f"Lembretes enviados para os agendamentos de {tomorrow_date}.")
    except Exception as e:
        logging.error(f"Erro ao enviar lembretes para os agendamentos de amanhã: {e}")

def handle_get_employee(sender_id, service_type):
    # Buscar colaboradores com o role correspondente
    print(f"service_type: {service_type}")
    try:
        if service_type == "unha":
            service_type = "manicure"
        
        employees = mongo_client_caller.db['employee'].find({"role": {"$regex": service_type, "$options": "i"}})
        # Verificar se há colaboradores disponíveis
        if not employees:
            # return send_test_message(sender_id, f"Desculpe, não encontramos profissionais disponíveis para {service_type} no momento.")
            return send_whatsapp_message(sender_id, f"Desculpe, não encontramos profissionais disponíveis para {service_type} no momento.")
        # Enviar o menu interativo com os profissionais disponíveis
        return send_available_employees_menu(sender_id, list(employees))
        # return send_test_available_employees_menu(sender_id, employees)
        return ""
    except Exception as e:
        logging.error(f"Erro ao buscar profissionais para {service_type}: {e}")
        return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao buscar os profissionais disponíveis. Tente novamente mais tarde.")
        # return send_test_message(sender_id, "Desculpe, ocorreu um erro ao buscar os profissionais disponíveis. Tente novamente mais tarde.")
    
def handle_get_services():
    # Obter todos os serviços disponíveis
    try:
        services = mongo_client_caller.db['services'].find()
        return services
    except Exception as e:
        logging.error(f"Erro ao buscar serviços: {e}")
        return []
        # return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao buscar os serviços disponíveis. Tente novamente mais tarde.")

def handle_get_role_services():
    try:
        services = mongo_client_caller.db['services'].find({}, {"role_service": 1, "_id": 0})
        
        role_services_set = {service["role_service"] for service in services if "role_service" in service}
        
        role_services = list(role_services_set)
        
        return role_services
    except Exception as e:
        logging.error(f"Erro ao buscar role_service na tabela services: {e}")
        return []


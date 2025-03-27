import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from app.services.mongo_service import MongoDBClient
from app.utils.test_utils import send_test_message, send_test_available_slots_menu
#from app.utils.whatsapp_utils import send_whatsapp_message, send_available_slots_menu

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
                #return send_whatsapp_message(sender_id, "Seu agendamento foi cancelado com sucesso.")
                return send_test_message(sender_id, "Seu agendamento foi cancelado com sucesso.")
            else:
                #return send_whatsapp_message(sender_id, "Desculpe, não é possível cancelar o agendamento com menos de 48 horas de antecedência.")
                return send_test_message(sender_id, "Desculpe, não é possível cancelar o agendamento com menos de 48 horas de antecedência.")
        else:
            #return send_whatsapp_message(sender_id, "Você não possui nenhum agendamento para cancelar.")
            return send_test_message(sender_id, "Você não possui nenhum agendamento para cancelar.")
    except Exception as e:
        logging.error(f"Erro ao processar cancelamento de agendamento: {e}")
        #return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao acessar os dados do agendamento. Tente novamente mais tarde.")
        return send_test_message(sender_id, "Desculpe, ocorreu um erro ao acessar os dados do agendamento. Tente novamente mais tarde.")

def handle_service_availability(sender_id, service_name):
    try:
        # Obter o tempo do serviço e os horários disponíveis
        service_time = mongo_client_caller.get_service_time(service_name)
        available_slots = mongo_client_caller.check_availability(service_name, service_time)

        # Salvar os horários disponíveis no armazenamento temporário
        user_slots[sender_id] = available_slots
        name_service[sender_id] = service_name

        # Enviar o menu interativo com os horários disponíveis
        #return send_available_slots_menu(sender_id, service_name, available_slots)
        return send_test_available_slots_menu(sender_id, service_name, available_slots)
    except Exception as e:
        logging.error(f"Erro ao verificar disponibilidade de horários: {e}")
        #return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao verificar os horários disponíveis. Tente novamente mais tarde.")
        return send_test_message(sender_id, "Desculpe, ocorreu um erro ao verificar os horários disponíveis. Tente novamente mais tarde.")

def handle_confirm_appointment(sender_id, user_name):
    try:
        selected_slot = selected_slots.get(sender_id)
        if selected_slot:
            date = selected_slot["date"]
            hour = selected_slot["time"]
            service_name = name_service.get(sender_id)
            service_value = mongo_client_caller.get_service_value(service_name)
            service_time = mongo_client_caller.get_service_time(service_name)

            mongo_client_caller.save_appointment(user_name, sender_id, service_name, service_value, service_time, date, hour)
            #return send_whatsapp_message(sender_id, f"Seu agendamento para {service_name} foi confirmado para {date} às {hour}. Obrigado e tenha um bom dia!")
            return send_test_message(sender_id, f"Seu agendamento para {service_name} foi confirmado para {date} às {hour}. Obrigado e tenha um bom dia!")
        else:
            #return send_whatsapp_message(sender_id, "Não foi possível confirmar o agendamento. Por favor, selecione um horário primeiro.")
            return send_test_message(sender_id, "Não foi possível confirmar o agendamento. Por favor, selecione um horário primeiro.")
    except Exception as e:
        logging.error(f"Erro ao salvar agendamento: {e}")
        #return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao salvar o agendamento. Tente novamente mais tarde.")
        return send_test_message(sender_id, "Desculpe, ocorreu um erro ao salvar o agendamento. Tente novamente mais tarde.")

def handle_change_appointment(sender_id):
    try:
        # Recuperar o agendamento do cliente
        appointment = mongo_client_caller.get_appointment(sender_id)
        if appointment:
            # Concatenar a data e a hora em uma única string
            appointment_datetime_str = f"{appointment['date']} {appointment['hour']}"
            appointment_date = datetime.strptime(appointment_datetime_str, "%Y-%m-%d %H:%M")
            current_time = datetime.now()

            # Verificar se o prazo é maior que 48 horas
            if appointment_date - current_time > timedelta(hours=48):
                # Obter o serviço e os horários disponíveis
                service_name = appointment["service_name"]
                service_time = mongo_client_caller.get_service_time(service_name)
                available_slots = mongo_client_caller.check_availability(service_name, service_time)

                # Salvar os horários disponíveis no armazenamento temporário
                user_slots[sender_id] = available_slots
                name_service[sender_id] = service_name

                # Gerar a mensagem com os horários disponíveis
                slots_message = "Aqui estão os horários disponíveis para alteração do seu agendamento:\n"
                for index, slot in enumerate(available_slots, start=1):
                    slots_message += f"{index} - {slot['date']} - {slot['time']}\n"
                slots_message += "Por favor, escolha o número correspondente ao novo horário desejado."

                # Enviar a mensagem com os horários disponíveis
                #return send_whatsapp_message(sender_id, slots_message)
                return send_test_message(sender_id, slots_message)
            else:
                # Não é possível alterar com menos de 48 horas de antecedência
                # return send_whatsapp_message(sender_id, "Desculpe, não é possível alterar o agendamento com menos de 48 horas de antecedência.")
                return send_test_message(sender_id, "Desculpe, não é possível alterar o agendamento com menos de 48 horas de antecedência.")
        else:
            # Caso não exista um agendamento para o cliente
            # return send_whatsapp_message(sender_id, "Você não possui nenhum agendamento para alterar.")
            return send_test_message(sender_id, "Você não possui nenhum agendamento para alterar.")
    except Exception as e:
        logging.error(f"Erro ao processar alteração de agendamento: {e}")
        # return send_whatsapp_message(sender_id, "Desculpe, ocorreu um erro ao acessar os dados do agendamento. Tente novamente mais tarde.")
        return send_test_message(sender_id, "Desculpe, ocorreu um erro ao acessar os dados do agendamento. Tente novamente mais tarde.")
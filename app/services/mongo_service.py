from pymongo import MongoClient
import datetime
from datetime import datetime, timedelta
import logging

class MongoDBClient:
    def __init__(self, uri, db_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def get_service_time(self, service_name):
        collection = self.db['services']
        service = collection.find_one({"name": service_name})
        return service['time'] if service else None

    def get_service_role(self, service_name):
        collection = self.db['services']
        service = collection.find_one({"name": service_name})
        return service['role_service'] if service else None

    def get_service_value(self, service_name):
        service = self.db.services.find_one({"name": service_name})
        return service["value"] if service else None

    def check_availability(self, service_name, service_time, collaborator_name):
       
        # Obtenha o papel (role) do serviço
        role = self.get_service_role(service_name)
        if not role:
            return []

        # Obter o turno de trabalho do colaborador
        work_shift_collection = self.db['work_shift']
        work_shift = work_shift_collection.find_one({"role": role})
        if not work_shift:
            return []

        start_time = datetime.strptime(work_shift["start_time"], "%H:%M")
        end_time = datetime.strptime(work_shift["end_time"], "%H:%M")
        available_slots = []
        current_date = datetime.now()

        for day in range(7):  # Verificar os próximos 7 dias
            date = (current_date + timedelta(days=day)).strftime('%Y-%m-%d')
            day_start_time = start_time

            if day == 0:  # Ajustar o horário inicial para o dia atual
                current_time = current_date.time()
                if current_time > start_time.time():
                    day_start_time = datetime.combine(current_date.date(), current_time)

            while day_start_time + timedelta(minutes=service_time) <= end_time:
                slot_available = True
                current_slot_start = datetime.strptime(f"{date} {day_start_time.strftime('%H:%M')}", "%Y-%m-%d %H:%M")
                current_slot_end = current_slot_start + timedelta(minutes=service_time)

                # Verifique se há conflitos com agendamentos existentes para o colaborador
                appointments = self.db['appointments'].find({
                    "date": date,
                    "employee_name": collaborator_name,
                    "$or": [
                        {
                            "hour": {"$lt": current_slot_end.strftime("%H:%M")}
                        },
                        {
                            "hour": {"$gte": current_slot_start.strftime("%H:%M")}
                        }
                    ]
                })

                for appointment in appointments:
                    appointment_start = datetime.strptime(appointment["date"] + " " + appointment["hour"], "%Y-%m-%d %H:%M")
                    appointment_end = appointment_start + timedelta(minutes=appointment["service_time"])

                    # Verifique se o horário atual ou os horários subsequentes se sobrepõem ao agendamento existente
                    if not (current_slot_end <= appointment_start or current_slot_start >= appointment_end):
                        slot_available = False
                        break

                if slot_available:
                    available_slots.append({"date": date, "time": day_start_time.strftime("%H:%M"), "employee": collaborator_name})

                # Avance para o próximo horário disponível
                day_start_time += timedelta(minutes=60)  # Avançar em incrementos de 60 minutos

        return available_slots

    def save_appointment(self, user_name, user_phone, service_name, service_value, service_time, date, hour, employee_name):
        """Salva um agendamento no banco de dados."""
        try:
            appointment_data = {
                "user_name": user_name,
                "user_phone": user_phone,
                "service_name": service_name,
                "service_value": service_value,
                "service_time": service_time,
                "date": date,
                "hour": hour,
                "employee_name": employee_name
            }
            self.db['appointments'].insert_one(appointment_data)
            logging.info(f"Agendamento salvo com sucesso: {appointment_data}")
        except Exception as e:
            logging.error(f"Erro ao salvar agendamento no MongoDB: {e}")
            raise

    def get_appointment(self, sender_id):
        return self.db.appointments.find_one({"user_phone": sender_id})

    def delete_appointment(self, sender_id):
        self.db.appointments.delete_one({"user_phone": sender_id})

    def update_appointment(self, sender_id, new_date, new_hour):
        try:
            self.db['appointments'].update_one(
                {"sender_id": sender_id},
                {"$set": {"date": new_date, "hour": new_hour}}
            )
        except Exception as e:
            logging.error(f"Erro ao atualizar agendamento no MongoDB: {e}")
            raise
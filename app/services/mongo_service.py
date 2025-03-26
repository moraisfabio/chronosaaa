from pymongo import MongoClient
import datetime

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

    def check_availability(self, service_name, service_time):
        # Obtenha o papel (role) do serviço
        role = self.get_service_role(service_name)
        if not role:
            return []

        # Obtenha o turno de trabalho (work shift) com base no papel (role)
        work_shift_collection = self.db['work_shift']
        work_shift = work_shift_collection.find_one({"role": role})
        if not work_shift:
            return []

        start_time = datetime.datetime.strptime(work_shift["start_time"], "%H:%M")
        end_time = datetime.datetime.strptime(work_shift["end_time"], "%H:%M")
        available_slots = []
        current_date = datetime.datetime.now()

        # Verifique a disponibilidade para os próximos 7 dias
        for day in range(7):
            date = (current_date + datetime.timedelta(days=day)).strftime('%Y-%m-%d')
            day_start_time = start_time

            # Se for o dia atual, comece a partir do horário atual
            if day == 0:
                day_start_time = max(start_time, current_date)

            while day_start_time + datetime.timedelta(minutes=service_time) <= end_time:
                slot_available = True
                appointments = self.db['appointments'].find({"date": date})
                for appointment in appointments:
                    appointment_start = datetime.datetime.strptime(appointment["date"] + " " + appointment["hour"], "%Y-%m-%d %H:%M")
                    appointment_end = appointment_start + datetime.timedelta(minutes=appointment["service_time"])
                    if not (day_start_time >= appointment_end or day_start_time + datetime.timedelta(minutes=service_time) <= appointment_start):
                        slot_available = False
                        break
                if slot_available:
                    available_slots.append({"date": date, "time": day_start_time.strftime("%H:%M")})
                day_start_time += datetime.timedelta(minutes=service_time)
        return available_slots

    def save_appointment(self, user_name, user_phone, service_name, service_value, service_time, date, hour):
        collection = self.db['appointments']
        appointment_data = {
            "user_name": user_name,
            "user_phone": user_phone,
            "service_name": service_name,
            "service_value": service_value,
            "service_time": service_time,
            "date": date,
            "hour": hour
        }
        collection.insert_one(appointment_data)
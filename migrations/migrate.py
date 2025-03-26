from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Inicialize o cliente MongoDB
mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME")
client = MongoClient(mongo_uri)
db = client[mongo_db_name]

# Crie as coleções e índices necessários
def create_collections():
    if 'services' not in db.list_collection_names():
        services = db['services']
        services.insert_many([
            {"name": "corte", "time": 60, "value": 50, "role_service": "cabelo"},
            {"name": "serum", "time": 45, "value": 40, "role_service": "cabelo"},
            {"name": "escova", "time": 30, "value": 30, "role_service": "cabelo"},
            {"name": "unha_padrao", "time": 30, "value": 25, "role_service": "manicure"},
            {"name": "alongamento", "time": 90, "value": 70, "role_service": "manicure"}
        ])
        print("Coleção 'services' criada com sucesso!")
    else:
        print("Coleção 'services' já existe. Nenhuma ação necessária.")
    
    # Verifique se a coleção 'work_shift' já existe
    if 'work_shift' not in db.list_collection_names():
        work_shift = db['work_shift']
        work_shift.insert_many([
            {"role": "cabelo", "start_time": "09:00", "end_time": "18:00"},
            {"role": "manicure", "start_time": "09:00", "end_time": "18:00"}
        ])
        print("Coleção 'work_shift' criada com sucesso!")
    else:
        print("Coleção 'work_shift' já existe. Nenhuma ação necessária.")
    
    db.create_collection("appointments")

    # Adicione índices se necessário
    db["appointments"].create_index([("date", 1), ("hour", 1)], unique=True)

if __name__ == "__main__":
    create_collections()
    print("Collections created successfully.")
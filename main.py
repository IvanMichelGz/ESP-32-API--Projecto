from fastapi import FastAPI
from pymongo import MongoClient
from datetime import datetime

app = FastAPI()

# 1. URI Corregida: Asegúrate de que el usuario sea 'iot' según lo que mencionaste
# Si el usuario es 'iot', la cadena queda así:
MONGO_URI = "mongodb+srv://esp32:esp32pass@cluster0.ywzq68o.mongodb.net/iot?retryWrites=true&w=majority&appName=Cluster0"

# 2. Conexión al cliente
# Añadimos un bloque try-except para detectar errores de conexión rápidamente
try:
    client = MongoClient(MONGO_URI)
    db = client.iot  # Nombre de la base de datos
    collection = db.sensores
    # Verificamos la conexión
    client.admin.command('ping')
    print("Conexión exitosa a MongoDB Atlas")
except Exception as e:
    print(f"Error al conectar: {e}")

@app.get("/")
def root():
    return {"mensaje": "API funcionando"}

@app.post("/sensor")
def guardar_sensor(data: dict):
    try:
        data["fecha"] = datetime.now()
        result = collection.insert_one(data)
        return {"status": "dato guardado", "id": str(result.inserted_id)}
    except Exception as e:
        # Esto te dirá el error real en la respuesta de la terminal
        return {"status": "error", "detalle": str(e)}
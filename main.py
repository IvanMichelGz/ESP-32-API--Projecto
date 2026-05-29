from fastapi import FastAPI
from pymongo import MongoClient
from datetime import datetime

app = FastAPI()

MONGO_URI = "mongodb+srv://esp32:esp32pass@cluster0.ywzq68o.mongodb.net/iot?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI)
    db = client.iot
    collection = db.sensores
    client.admin.command('ping')
    print("✅ Conexión exitosa a MongoDB Atlas")
except Exception as e:
    print(f"❌ Error al conectar: {e}")

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
        return {"status": "error", "detalle": str(e)}

@app.get("/test")
def test_insercion():
    doc = {"temperatura": 99.9, "humedad": 10, "fecha": datetime.now()}
    result = collection.insert_one(doc)
    return {"status": "ok", "inserted_id": str(result.inserted_id)}

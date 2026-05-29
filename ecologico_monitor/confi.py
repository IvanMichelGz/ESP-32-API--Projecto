import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sistema_monitoreo_ambiental_key')
    # Tu cadena de conexión real a MongoDB Atlas
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://esp32:esp32pass@cluster0.ywzq68o.mongodb.net/iot?retryWrites=true&w=majority&appName=Cluster0')
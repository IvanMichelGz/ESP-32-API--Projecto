from pymongo import MongoClient
from config import Config

class Database:
    client = None
    db = None

    @classmethod
    def initialize(cls):
        if cls.client is None:
            try:
                cls.client = MongoClient(Config.MONGO_URI)
                cls.db = cls.client.get_database('iot')
                cls.client.admin.command('ping')
                print("✅ Conexión exitosa a MongoDB Atlas (Módulo Database)")
            except Exception as e:
                print(f"❌ Error crítico de conexión en módulo Database: {e}")
                raise e
        return cls.db

    @classmethod
    def get_collection(cls, collection_name='sensores'):
        if cls.db is None:
            cls.initialize()
        return cls.db[collection_name]
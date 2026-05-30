from pymongo import MongoClient
from confi import Config

class Database:
    client = None
    db = None

    @classmethod
    def initialize(cls):
        """Inicializa el cliente de Mongo y asigna la base de datos."""
        if cls.client is None:
            try:
                cls.client = MongoClient(Config.MONGO_URI)
                # Forzar la asignación directa de la base de datos 'iot'
                cls.db = cls.client.get_database('iot')
                
                # Prueba de verificación
                cls.client.admin.command('ping')
                print("✅ Conexión exitosa a MongoDB Atlas (Módulo Database)")
            except Exception as e:
                print(f"❌ Error crítico de conexión en módulo Database: {e}")
                cls.client = None
                cls.db = None
                raise e
        return cls.db

    @classmethod
    def get_collection(cls, collection_name='sensores'):
        """Asegura que la base de datos esté lista antes de pedir una colección."""
        # Si por alguna razón db sigue siendo None, forzar la inicialización
        if cls.db is None:
            print("🔄 Base de datos no inicializada. Conectando ahora...")
            cls.initialize()
            
        # Doble verificación por seguridad estilo senior
        if cls.db is None:
            raise RuntimeError("❌ No se pudo establecer la conexión con la base de datos. cls.db sigue siendo None.")
            
        return cls.db[collection_name]
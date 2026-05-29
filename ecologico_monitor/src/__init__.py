from flask import Flask
from config import Config

from src.database import Database

def create_app():  # <--- Asegúrate de que esté escrito exactamente así
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar pool de conexiones a MongoDB
    Database.initialize()

    # Registrar rutas
    from src.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='')

    return app
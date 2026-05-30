from flask import Flask
from confi import Config
from src.database import Database

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar pool de conexiones a MongoDB
    Database.initialize()

    # Importar los Blueprints
    from src.routes.api import api_bp
    from src.routes.web import web_bp
    
    # SOLUCIÓN: Separamos la API agregándole el prefijo '/api'
    # Así, el ESP32 enviará los datos a: http://tu-ip:5000/api/sensor
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # La interfaz web se queda con la raíz '/'
    # Así, cuando entres a http://tu-ip:5000/ verás el Dashboard HTML
    app.register_blueprint(web_bp, url_prefix='')

    return app
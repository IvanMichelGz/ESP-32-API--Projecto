import os
from flask import Flask
from src.database import Database  # Importa tu clase corregida
from src.routes.web import web_bp
from src.routes.api import api_bp  # Asegúrate de registrar también tu API para el ESP32

# 1. Configuración absoluta de rutas para la estructura de carpetas 'src/'
# os.path.dirname(__file__) se posiciona en la raíz del nuevo repositorio
base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'src', 'templates')
static_dir = os.path.join(base_dir, 'src', 'static')

# 2. Instanciar Flask pasándole explícitamente los directorios correctos
app = Flask(__name__, 
            template_folder=template_dir, 
            static_folder=static_dir)

# 3. Registrar tus Blueprints/Rutas
app.register_blueprint(web_bp)
app.register_blueprint(api_bp)  # 🚨 IMPORTANTE: No olvides registrar las rutas del /sensor

# 4. INICIALIZACIÓN OBLIGATORIA DE LA BASE DE DATOS AL ARRANCAR EL SERVIDOR
with app.app_context():
    try:
        print("🚀 Inicializando servicios del sistema...")
        Database.initialize()  # Esto levanta el ping y asegura que apunte a tu clúster NoSQL
    except Exception as e:
        print(f"⚠️ Alerta: El servidor inició pero la BD reportó problemas: {e}")

if __name__ == '__main__':
    # Ejecución local del servidor
    app.run(debug=True, port=5000)
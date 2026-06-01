import os
from flask import Flask
from src.database import Database  # Importa tu clase corregida
from src.routes.web import web_bp

template_dir=os.path.abspath(os.path.join(os.path.dirname(__file__),'src','templates'))
app = Flask(__name__)

# 1. Registrar tus Blueprints/Rutas
app.register_blueprint(web_bp)

# 2. INICIALIZACIÓN OBLIGATORIA DE LA BASE DE DATOS AL ARRANCAR EL SERVIDOR
with app.app_context():
    try:
        print("🚀 Inicializando servicios del sistema...")
        Database.initialize()  # Esto levanta el ping y asegura que apunte a 'iot'
    except Exception as e:
        print(f"⚠️ Alerta: El servidor inició pero la BD reportó problemas: {e}")

if __name__ == '__main__':
    # Ejecución local del servidor
    app.run(debug=True, port=5000)
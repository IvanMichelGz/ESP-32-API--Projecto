from flask import Blueprint, render_template
from src.database import Database

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def dashboard():
    collection = Database.get_collection('lecturas')
    
    # Obtener la última lectura registrada
    last_reading = collection.find_one(sort=[("fecha", -1)])
    
    # Obtener las últimas 10 lecturas para el histórico (gráficas)
    history_cursor = collection.find().sort("fecha", -1).limit(10)
    history = list(history_cursor)

    # Limpiar el formato para pasar a Jinja2/HTML si es necesario
    if last_reading:
        last_reading['_id'] = str(last_reading['_id'])
        
    return render_template('dashboard.html', current=last_reading, history=history)
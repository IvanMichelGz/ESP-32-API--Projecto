from flask import Blueprint, request, jsonify
from datetime import datetime
from src.database import Database
from src.services.analyzer import CultiveAnalyzer

api_bp = Blueprint('api', __name__)

@api_bp.route('/', methods=['GET'])
def root():
    return jsonify({"mensaje": "API del Monitor Ecológico funcionando bajo Flask"}), 200

@api_bp.route('/sensor', methods=['POST'])
def guardar_sensor():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "detalle": "Cuerpo de petición vacío"}), 400
            
        # 1. Extraer y validar variables obligatorias enviadas por el ESP32
        temp_val = float(data.get('temperatura'))
        hum_val = float(data.get('humedad'))
        
        # 2. Sincronizar fecha nativa en el servidor (PIEZA CLAVE)
        # Esto guarda un objeto ISODate real que MongoDB Atlas sí puede indexar,
        # permitiendo que aparezca al instante en el Dashboard y en los reportes.
        data["fecha"] = datetime.now()
        
        # 3. Inyectar lógica de análisis inteligente para las tarjetas del cultivo
        analisis_resultado = CultiveAnalyzer.analyze(temp_val, hum_val)
        data["analisis"] = analisis_resultado

        # 4. Persistencia inmediata en MongoDB Atlas
        collection = Database.get_collection('sensores')
        result = collection.insert_one(data)
        
        # Devolvemos la respuesta de éxito requerida por el firmware
        return jsonify({
            "status": "dato guardado",
            "id": str(result.inserted_id),
            "analisis": analisis_resultado
        }), 201
        
    except (TypeError, ValueError) as format_error:
        return jsonify({"status": "error", "detalle": f"Datos numéricos inválidos: {str(format_error)}"}), 400
    except Exception as e:
        return jsonify({"status": "error", "detalle": str(e)}), 500

@api_bp.route('/test', methods=['GET'])
def test_insercion():
    try:
        doc = {
            "temperatura": 24.5, 
            "humedad": 62.0, 
            "fecha": datetime.now(),
            "analisis": CultiveAnalyzer.analyze(24.5, 62.0)
        }
        collection = Database.get_collection('sensores')
        result = collection.insert_one(doc)
        return jsonify({"status": "ok", "inserted_id": str(result.inserted_id)}), 200
    except Exception as e:
        return jsonify({"status": "error", "detalle": str(e)}), 500
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
            
        # Extraer variables obligatorias
        temp_val = float(data.get('temperatura'))
        hum_val = float(data.get('humedad'))
        
        # Sincronizar fecha en el servidor
        data["fecha"] = datetime.now()
        
        # Inyectar lógica de análisis inteligente
        analisis_resultado = CultiveAnalyzer.analyze(temp_val, hum_val)
        data["analisis"] = analisis_resultado

        # Guardar en MongoDB Atlas
        collection = Database.get_collection('sensores')
        result = collection.insert_one(data)
        
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
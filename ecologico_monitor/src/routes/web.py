from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from src.database import Database  
from datetime import datetime, timedelta
import statistics

# Blueprint configurado de forma limpia para heredar las rutas estáticas globales
web_bp = Blueprint('web', __name__)

def formatear_fecha(fecha_obj):
    """Función auxiliar para mitigar errores de tipo de dato en fechas de MongoDB Atlas."""
    if isinstance(fecha_obj, datetime):
        return fecha_obj.strftime('%H:%M:%S')
    fecha_str = str(fecha_obj)
    if " " in fecha_str:
        return fecha_str.split(" ")[1]
    if "T" in fecha_str:
        return fecha_str.split("T")[-1][:8]
    return fecha_str

@web_bp.route('/')
def dashboard():
    """Carga inicial estática del tablero de control con el estado más reciente."""
    try:
        coleccion = Database.get_collection('sensores')
        # Obtenemos las últimas 10 lecturas reales para poblar la vista base
        registros = list(coleccion.find().sort('fecha', -1).limit(10))
        registros.reverse()
        
        historial = []
        for r in registros:
            fecha_obj = r.get('fecha')
            if isinstance(fecha_obj, datetime):
                # Si el dato es de días anteriores, se incluye día/mes para mejor contexto visual
                ahora = datetime.now()
                if fecha_obj.date() < ahora.date():
                    fecha_str = fecha_obj.strftime('%d/%m %H:%M')
                else:
                    fecha_str = fecha_obj.strftime('%H:%M:%S')
            else:
                fecha_str = str(fecha_obj).split('T')[-1][:8] if 'T' in str(fecha_obj) else str(fecha_obj)

            historial.append({
                'fecha_str': fecha_str,
                'temperatura': r.get('temperatura', 0),
                'humedad': r.get('humedad', 0)
            })
            
        actual = registros[-1] if registros else None
        if actual:
            actual['temperatura'] = actual.get('temperatura', 0)
            actual['humedad'] = actual.get('humedad', 0)
            
            # Lógica analítica síncrona de respaldo
            analisis = actual.get('analisis', {})
            actual['analisis'] = {
                'estado': analisis.get('estado', 'Óptimo' if actual['humedad'] >= 40 else 'Crítico'),
                'necesita_agua': analisis.get('necesita_agua', actual['humedad'] < 40),
                'recomendaciones': analisis.get('recomendaciones', ['El sistema opera en rangos normales.'] if actual['humedad'] >= 40 else ['Alerta: Humedad baja.', 'Activar riego.'])
            }

        return render_template('dashboard.html', historial=historial, actual=actual)
    except Exception as e:
        print(f"❌ Error en dashboard: {e}")
        return render_template('dashboard.html', historial=[], actual=None)


@web_bp.route('/api/live-data')
def live_data():
    """API Endpoint optimizado para el refresco asíncrono cada 5 segundos buscando datos históricos reales."""
    try:
        coleccion = Database.get_collection('sensores')
        
        # 1. Traemos los 10 registros más recientes guardados en la base de datos
        registros_nuevos = list(coleccion.find().sort('fecha', -1).limit(10))
        
        # Si la base de datos está completamente vacía (sin registros históricos)
        if not registros_nuevos:
            ahora = datetime.now()
            labels_mock = [(ahora - timedelta(seconds=(10-i)*5)).strftime('%H:%M:%S') for i in range(10)]
            temp_dinamica = 24.0 + (ahora.second % 5) * 0.4
            hum_dinamica = 50.0 - (ahora.second % 5) * 0.6
            
            return jsonify({
                'actual': {
                    'temperatura': temp_dinamica,
                    'humedad': hum_dinamica,
                    'analisis': {
                        'estado': 'Óptimo (Simulado)',
                        'necesita_agua': False,
                        'recomendaciones': ['Esperando transmisión física del ESP32...', 'Monitoreando canal virtual.']
                    }
                },
                'grafica': {
                    'labels': labels_mock,
                    'temperaturas': [23, 24, 23.5, 24.2, 24.8, 24.1, 23.9, 24.3, 24.5, temp_dinamica],
                    'humedades': [55, 54, 53.8, 54.1, 53.2, 52.9, 52.1, 51.8, 51.2, hum_dinamica]
                }
            })
            
        # 2. Guardamos el dato más reciente para las tarjetas de métricas
        actual_reg = registros_nuevos[0]
        
        temp_val = float(actual_reg.get('temperatura', 0))
        hum_val = float(actual_reg.get('humedad', 0))
        
        # Extraer análisis inteligente
        analisis_api = actual_reg.get('analisis', {})
        estado = analisis_api.get('estado', "Óptimo")
        necesita_agua = analisis_api.get('necesita_agua', False)
        recomendaciones = analisis_api.get('recomendaciones', ["El sistema opera en rangos normales."])
        
        if not analisis_api:
            if hum_val < 40:
                estado = "Crítico"
                necesita_agua = True
                recomendaciones = ["Alerta: Humedad críticamente baja.", "Activar riego automatizado inmediatamente."]
            elif temp_val > 30:
                estado = "Alerta"
                recomendaciones = ["Temperatura elevada.", "Monitorear ventilación del invernadero."]

        # 3. Clonamos y volteamos la lista para renderizar el eje X de forma cronológica (antiguo -> nuevo)
        registros_grafica = list(registros_nuevos)
        registros_grafica.reverse()
        
        # Formatear etiquetas de tiempo dinámicamente si los datos son históricos
        labels_dinamicos = []
        ahora_ref = datetime.now()
        for r in registros_grafica:
            f_obj = r.get('fecha')
            if isinstance(f_obj, datetime) and f_obj.date() < ahora_ref.date():
                labels_dinamicos.append(f_obj.strftime('%d/%m %H:%M'))
            else:
                labels_dinamicos.append(formatear_fecha(f_obj))

        data = {
            'actual': {
                'temperatura': temp_val,
                'humedad': hum_val,
                'analisis': {
                    'estado': estado,
                    'necesita_agua': necesita_agua,
                    'recomendaciones': recomendaciones
                }
            },
            'grafica': {
                'labels': labels_dinamicos,
                'temperaturas': [float(r.get('temperatura', 0)) for r in registros_grafica],
                'humedades': [float(r.get('humedad', 0)) for r in registros_grafica]
            }
        }
        return jsonify(data)
        
    except Exception as e:
        print(f"❌ Error en Endpoint /api/live-data: {e}")
        return jsonify({'error': str(e)}), 500

@web_bp.route('/reporte')
def reporte_historico():
    """Generación de reportes avanzados optimizados con agregaciones por hora."""
    inicio_str = request.args.get('inicio')
    fin_str = request.args.get('fin')
    
    if not inicio_str or not fin_str:
        return redirect(url_for('web.dashboard'))
        
    try:
        fecha_inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
        fecha_fin = datetime.strptime(fin_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
        
        coleccion = Database.get_collection('sensores')
        
        # Pipeline de Agregación: Evita el colapso visual promediando ráfagas masivas por hora
        pipeline = [
            {"$match": {"fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}}},
            {"$group": {
                "_id": {
                    "fecha_hora": {"$dateToString": {"format": "%Y-%m-%d %H:00", "date": "$fecha"}}
                },
                "temp_promedio": {"$avg": "$temperatura"},
                "hum_promedio": {"$avg": "$humedad"},
                "temp_max_hora": {"$max": "$temperatura"},
                "temp_min_hora": {"$min": "$temperatura"},
                "hum_max_hora": {"$max": "$humedad"},
                "hum_min_hora": {"$min": "$humedad"}
            }},
            {"$sort": {"_id.fecha_hora": 1}}
        ]
        
        registros_agrupados = list(coleccion.aggregate(pipeline))
        
        # Respaldo de seguridad si el rango consultado carece por completo de lecturas
        if not registros_agrupados:
            print("⚠️ El rango seleccionado no contiene datos agregados. Extrayendo histórico general...")
            registros_raw = list(coleccion.find().sort('fecha', -1).limit(50))
            registros_raw.reverse()
            
            if not registros_raw:
                grafica_vacia = {'labels': [], 'temperaturas': [], 'humedades': []}
                return render_template('reporte.html', vacio=True, inicio=inicio_str, fin=fin_str, grafica=grafica_vacia)
            
            temps = [float(r.get('temperatura', 0)) for r in registros_raw]
            hums = [float(r.get('humedad', 0)) for r in registros_raw]
            labels_grafica = [r.get('fecha').strftime('%d/%m %H:%M') if isinstance(r.get('fecha'), datetime) else str(r.get('fecha'))[:16] for r in registros_raw]
            
            metricas = {
                'temp_max': max(temps), 'temp_min': min(temps), 'temp_mediana': statistics.median(temps),
                'hum_max': max(hums), 'hum_min': min(hums), 'hum_mediana': statistics.median(hums)
            }
        else:
            # Procesamiento estructurado de datos limpios agrupados por bloque de hora
            temps = [round(float(r['temp_promedio']), 1) for r in registros_agrupados]
            hums = [round(float(r['hum_promedio']), 1) for r in registros_agrupados]
            
            labels_grafica = []
            for r in registros_agrupados:
                dt_parse = datetime.strptime(r['_id']['fecha_hora'], '%Y-%m-%d %H:00')
                labels_grafica.append(dt_parse.strftime('%d/%m %H:00'))
            
            metricas = {
                'temp_max': max([r['temp_max_hora'] for r in registros_agrupados]),
                'temp_min': min([r['temp_min_hora'] for r in registros_agrupados]),
                'temp_mediana': statistics.median(temps),
                'hum_max': max([r['hum_max_hora'] for r in registros_agrupados]),
                'hum_min': min([r['hum_min_hora'] for r in registros_agrupados]),
                'hum_mediana': statistics.median(hums)
            }

        grafica = {
            'labels': labels_grafica,
            'temperaturas': temps,
            'humedades': hums
        }
        
        # Extracción y filtrado estricto del Top 5 de picos calurosos eliminando duplicados por minuto
        query_top = {'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}}
        todos_registros = list(coleccion.find(query_top))
        registros_ordenados = sorted(todos_registros, key=lambda x: x.get('temperatura', 0), reverse=True)
        
        top_calorosos = []
        minutos_procesados = set()
        
        for reg in registros_ordenados:
            f_obj = reg.get('fecha')
            if isinstance(f_obj, datetime):
                f_format = f_obj.strftime('%d/%m/%Y %H:%M')
            else:
                f_format = str(f_obj).replace('T', ' ')[:16]
            
            if f_format in minutos_procesados:
                continue
                
            minutos_procesados.add(f_format)
            top_calorosos.append({
                'fecha': f_format, 
                'temp': reg.get('temperatura', 0)
            })
            
            if len(top_calorosos) == 5:
                break
            
        return render_template('reporte.html', 
                               vacio=False, 
                               inicio=inicio_str, 
                               fin=fin_str, 
                               metricas=metricas, 
                               grafica=grafica, 
                               top_calorosos=top_calorosos)
                               
    except Exception as e:
        print(f"❌ Error crítico procesando reporte estadístico: {e}")
        grafica_error = {'labels': [], 'temperaturas': [], 'humedades': []}
        return render_template('reporte.html', vacio=True, inicio=inicio_str, fin=fin_str, grafica=grafica_error)
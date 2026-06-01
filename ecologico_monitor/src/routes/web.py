from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from src.database import Database  
from datetime import datetime, timedelta
import statistics

# Modifica esta línea en tu web.py (Línea 5 aprox.)
web_bp = Blueprint('web', __name__, template_folder='../templates')

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
    try:
        coleccion = Database.get_collection('sensores')
        registros = list(coleccion.find().sort('fecha', -1).limit(10))
        registros.reverse()
        
        historial = []
        for r in registros:
            fecha_obj = r.get('fecha')
            if isinstance(fecha_obj, datetime):
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
            actual['analisis'] = {
                'estado': 'Óptimo' if actual['humedad'] >= 40 else 'Crítico',
                'necesita_agua': actual['humedad'] < 40,
                'recomendaciones': ['El sistema opera en rangos normales.'] if actual['humedad'] >= 40 else ['Alerta: Humedad baja.', 'Activar riego.']
            }

        return render_template('dashboard.html', historial=historial, actual=actual)
    except Exception as e:
        print(f"❌ Error en dashboard: {e}")
        return render_template('dashboard.html', historial=[], actual=None)


@web_bp.route('/api/live-data')
def live_data():
    """API Endpoint para el refresco asíncrono cada 5 segundos usando la colección correcta."""
    try:
        # Se unifica a la colección 'sensores' para mantener consistencia global
        coleccion = Database.get_collection('sensores')
        registros = list(coleccion.find().sort('fecha', -1).limit(10))
        
        # Si no hay datos reales en Atlas, responde con datos simulados dinámicos
        if not registros:
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
                        'recomendaciones': ['Conexión Atlas exitosa.', 'Monitoreando canal de datos virtual de prueba.']
                    }
                },
                'grafica': {
                    'labels': labels_mock,
                    'temperaturas': [23, 24, 23.5, 24.2, 24.8, 24.1, 23.9, 24.3, 24.5, temp_dinamica],
                    'humedades': [55, 54, 53.8, 54.1, 53.2, 52.9, 52.1, 51.8, 51.2, hum_dinamica]
                }
            })
            
        actual_reg = registros[0]
        registros.reverse()
        
        temp_val = actual_reg.get('temperatura', 0)
        hum_val = actual_reg.get('humedad', 0)
        
        estado = "Óptimo"
        necesita_agua = False
        recomendaciones = ["El sistema opera en rangos normales."]
        
        if hum_val < 40:
            estado = "Crítico"
            necesita_agua = True
            recomendaciones = ["Alerta: Humedad críticamente baja.", "Activar riego automatizado inmediatamente."]
        elif temp_val > 30:
            estado = "Alerta"
            recomendaciones = ["Temperatura elevada.", "Monitorear ventilación del invernadero."]
            
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
                'labels': [formatear_fecha(r.get('fecha', datetime.now())) for r in registros],
                'temperaturas': [r.get('temperatura', 0) for r in registros],
                'humedades': [r.get('humedad', 0) for r in registros]
            }
        }
        return jsonify(data)
    except Exception as e:
        print(f"❌ Error en Endpoint /api/live-data: {e}")
        return jsonify({'error': str(e)})


@web_bp.route('/reporte')
def reporte_historico():
    inicio_str = request.args.get('inicio')
    fin_str = request.args.get('fin')
    
    if not inicio_str or not fin_str:
        return redirect(url_for('web.dashboard'))
        
    try:
        # 1. Convertir strings a objetos datetime con zona horaria/límites correctos
        fecha_inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
        # Forzamos que el día de fin termine exactamente a las 23:59:59.999
        fecha_fin = datetime.strptime(fin_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
        
        nombre_coleccion = 'sensores' 
        coleccion = Database.get_collection(nombre_coleccion)
        
        total_documentos = coleccion.count_documents({})
        print(f"📊 [DEBUG] Total de documentos guardados en la colección '{nombre_coleccion}': {total_documentos}")
        
        # 2. Consulta filtrando estrictamente por el rango seleccionado
        query = {'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}}
        registros = list(coleccion.find(query).sort('fecha', 1))
        
        print(f"🔍 [DEBUG] Documentos encontrados en el rango seleccionado: {len(registros)}")
        
        # 3. Respaldo inteligente: Si no hay datos hoy, buscamos las últimas 50 lecturas reales totales
        hubo_respaldo = False
        if not registros:
            print("⚠️ El rango seleccionado no contiene datos. Extrayendo histórico general de 'sensores'...")
            registros = list(coleccion.find().sort('fecha', -1).limit(50))
            registros.reverse()  # Orden cronológico para Chart.js
            hubo_respaldo = True
            
        if not registros:
            print("❌ La colección 'sensores' está completamente vacía en Atlas.")
            grafica_vacia = {'labels': [], 'temperaturas': [], 'humedades': []}
            return render_template('reporte.html', vacio=True, inicio=inicio_str, fin=fin_str, grafica=grafica_vacia)
            
        # Extracción segura de campos convirtiéndolos en flotantes limpios
        temps = [float(r.get('temperatura', 0)) for r in registros if r.get('temperatura') is not None]
        hums = [float(r.get('humedad', 0)) for r in registros if r.get('humedad') is not None]
        
        # Formatear la fecha de forma segura para las etiquetas de la gráfica
        labels_grafica = []
        for r in registros:
            f = r.get('fecha')
            if isinstance(f, datetime):
                # Si es un respaldo de varios días, incluimos el día/mes para evitar confusión visual
                labels_grafica.append(f.strftime('%d/%m %H:%M') if hubo_respaldo else f.strftime('%H:%M:%S'))
            else:
                labels_grafica.append(str(f).split('T')[0][5:] if 'T' in str(f) else str(f)[:10])

        grafica = {
            'labels': labels_grafica,
            'temperaturas': temps,
            'humedades': hums
        }
        
        # Cálculo de métricas estadísticas asistidas por la librería estándar
        metricas = {
            'temp_max': max(temps) if temps else 0,
            'temp_min': min(temps) if temps else 0,
            'temp_mediana': statistics.median(temps) if temps else 0,
            'hum_max': max(hums) if hums else 0,
            'hum_min': min(hums) if hums else 0,
            'hum_mediana': statistics.median(hums) if hums else 0
        }
        
        # =========================================================================
        # 🔥 FILTRADO DEL TOP 5 SIN DUPLICADOS EN EL MISMO MINUTO
        # =========================================================================
        registros_ordenados = sorted(registros, key=lambda x: x.get('temperatura', 0), reverse=True)
        
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
        # =========================================================================
            
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
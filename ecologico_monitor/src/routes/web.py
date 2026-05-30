from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from src.database import Database  # Importación correcta desde la raíz de src
from datetime import datetime, timedelta
import statistics  # Módulo nativo para analíticas matemáticas

# Definición del Blueprint alineado con tu __init__.py
web_bp = Blueprint('web', __name__)

def formatear_fecha(fecha_obj):
    """Función auxiliar para mitigar errores de tipo de dato en fechas de MongoDB Atlas."""
    if isinstance(fecha_obj, datetime):
        return fecha_obj.strftime('%H:%M:%S')
    # Si el ESP32 lo guardó como String (ej. "2026-05-28 20:30:15"), intentamos limpiarlo o pasarlo directo
    fecha_str = str(fecha_obj)
    if " " in fecha_str:
        return fecha_str.split(" ")[1]  # Retorna solo la hora HH:MM:SS
    return fecha_str

@web_bp.route('/')
def dashboard():
    """Ruta del Dashboard principal."""
    try:
        coleccion = Database.get_collection('temperatura_humedad')
        
        # Intentar extraer las últimas 10 lecturas de MongoDB Atlas
        registros = list(coleccion.find().sort('fecha', -1).limit(10))
        
        # --- PLAN DE RESPALDO (MOCK DATA) ---
        # Si tu base de datos en Atlas está vacía porque el ESP32 aún no envía nada,
        # inyectamos datos simulados para que la pantalla NO se quede congelada y veas el diseño funcionar.
        if not registros:
            print("⚠️ Alerta: No se encontraron datos en Atlas. Usando datos simulados de prueba.")
            ahora = datetime.now()
            registros = []
            for i in range(10):
                registros.append({
                    'fecha': ahora - timedelta(minutes=10-i),
                    'temperatura': 24.5 + (i * 0.3),
                    'humedad': 55.0 - (i * i * 0.1)
                })
            # Clonamos el último elemento simulado como el actual
            actual = registros[-1]
            actual['analisis'] = {
                'estado': 'Óptimo (Simulado)',
                'necesita_agua': False,
                'recomendaciones': ['Operando en modo de respaldo.', 'Conexión a Atlas OK, esperando al ESP32.']
            }
            historial = []
            for r in registros:
                historial.append({
                    'fecha_str': r['fecha'].strftime('%H:%M:%S'),
                    'temperatura': r['temperatura'],
                    'humedad': r['humedad']
                })
            return render_template('dashboard.html', historial=historial, actual=actual)
            
        # --- FLUJO REAL (SI HAY DATOS EN ATLAS) ---
        registros.reverse()  # Orden cronológico para Chart.js
        
        historial = []
        for r in registros:
            historial.append({
                'fecha_str': formatear_fecha(r.get('fecha', datetime.now())),
                'temperatura': r.get('temperatura', 0),
                'humedad': r.get('humedad', 0)
            })
            
        # Estructurar la tarjeta de tiempo real con la última lectura física
        ultimo_registro = registros[-1]
        
        # Procesar análisis del microclima en el render inicial
        estado = "Óptimo"
        necesita_agua = False
        recomendaciones = ["El sistema opera en rangos normales."]
        
        temp_val = ultimo_registro.get('temperatura', 0)
        hum_val = ultimo_registro.get('humedad', 0)
        
        if hum_val < 40:
            estado = "Crítico"
            necesita_agua = True
            recomendaciones = ["Alerta: Humedad críticamente baja.", "Activar riego automatizado inmediatamente."]
        elif temp_val > 30:
            estado = "Alerta"
            recomendaciones = ["Temperatura elevada.", "Monitorear ventilación del invernadero."]
            
        actual = {
            'temperatura': temp_val,
            'humedad': hum_val,
            'analisis': {
                'estado': estado,
                'necesita_agua': necesita_agua,
                'recomendaciones': recomendaciones
            }
        }
        
        return render_template('dashboard.html', historial=historial, actual=actual)
    except Exception as e:
        print(f"❌ Error crítico en vista dashboard: {e}")
        return render_template('dashboard.html', historial=[], actual=None)


@web_bp.route('/api/live-data')
def live_data():
    """API Endpoint para el refresco asíncrono cada 5 segundos."""
    try:
        coleccion = Database.get_collection('temperatura_humedad')
        registros = list(coleccion.find().sort('fecha', -1).limit(10))
        
        # Si no hay datos reales en Atlas, la API asíncrona también responde con datos simulados dinámicos
        if not registros:
            ahora = datetime.now()
            labels_mock = [(ahora - timedelta(seconds=(10-i)*5)).strftime('%H:%M:%S') for i in range(10)]
            # Un pequeño cálculo aleatorio/fijo para ver movimiento en las gráficas
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
            
        # Si hay datos reales
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
    """Ruta del procesamiento estadístico de rangos de fecha."""
    inicio_str = request.args.get('inicio')
    fin_str = request.args.get('fin')
    
    if not inicio_str or not fin_str:
        return redirect(url_for('web.dashboard'))
        
    try:
        fecha_inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
        fecha_fin = datetime.strptime(fin_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        
        query = {'fecha': {'$gte': fecha_inicio, '$lte': fecha_fin}}
        coleccion = Database.get_collection('temperatura_humedad')
        registros = list(coleccion.find(query).sort('fecha', 1))
        
        if not registros:
            return render_template('reporte.html', vacio=True, inicio=inicio_str, fin=fin_str)
            
        temps = [r['temperatura'] for r in registros]
        hums = [r['humedad'] for r in registros]
        
        grafica = {
            'labels': [r['fecha'].strftime('%d/%m %H:%M') if isinstance(r['fecha'], datetime) else str(r['fecha']) for r in registros],
            'temperaturas': temps,
            'humedades': hums
        }
        
        metricas = {
            'temp_max': max(temps),
            'temp_min': min(temps),
            'temp_mediana': statistics.median(temps),
            'hum_max': max(hums),
            'hum_min': min(hums),
            'hum_mediana': statistics.median(hums)
        }
        
        registros_ordenados = sorted(registros, key=lambda x: x['temperatura'], reverse=True)
        top_calorosos = []
        for reg in registros_ordenados[:5]:
            f_format = reg['fecha'].strftime('%d/%m/%Y %H:%M') if isinstance(reg['fecha'], datetime) else str(reg['fecha'])
            top_calorosos.append({'fecha': f_format, 'temp': reg['temperatura']})
            
        return render_template('reporte.html', vacio=False, inicio=inicio_str, fin=fin_str, metricas=metricas, grafica=grafica, top_calorosos=top_calorosos)
                               
    except Exception as e:
        print(f"❌ Error en reporte histórico: {e}")
        return redirect(url_for('web.dashboard'))
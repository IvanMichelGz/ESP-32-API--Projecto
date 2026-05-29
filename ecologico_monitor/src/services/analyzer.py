class CultiveAnalyzer:
    # Umbrales óptimos configurables para el cultivo
    TEMP_MIN = 18.0
    TEMP_MAX = 30.0
    HUM_MIN = 50.0
    HUM_MAX = 80.0

    @classmethod
    def analyze(cls, temperature: float, humidity: float) -> dict:
        status = "Óptimo"
        needs_water = False
        recommendations = []

        # Análisis de Humedad y necesidad de riego
        if humidity < cls.HUM_MIN:
            status = "Alerta"
            needs_water = True
            recommendations.append(f"Humedad baja ({humidity}%). El cultivo requiere agua.")
        elif humidity > cls.HUM_MAX:
            status = "Alerta"
            recommendations.append(f"Humedad alta ({humidity}%). Riesgo de hongos.")

        # Análisis de Temperatura
        if temperature < cls.TEMP_MIN:
            status = "Crítico" if status == "Alerta" else "Alerta"
            recommendations.append(f"Temperatura fría ({temperature}°C).")
        elif temperature > cls.TEMP_MAX:
            status = "Crítico" if status == "Alerta" else "Alerta"
            recommendations.append(f"Temperatura elevada ({temperature}°C).")

        if not recommendations:
            recommendations.append("El microclima se encuentra en condiciones ideales.")

        return {
            "estado": status,
            "necesita_agua": needs_water,
            "recomendaciones": recommendations
        }
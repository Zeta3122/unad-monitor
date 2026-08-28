"""
Configuracion del monitor de la Politica de Gratuidad en la Matricula - UNAD.
Edita este archivo para ajustar las URLs vigiladas, las palabras clave
y el comportamiento del mensaje diario de estado.
"""

# ---------------------------------------------------------------------------
# 1. URLs A VIGILAR
# ---------------------------------------------------------------------------
URLS = [
    "https://noticias.unad.edu.co/index.php",
    # Agrega aqui mas URLs si decides vigilar otras paginas, por ejemplo
    # micrositios de admisiones o gratuidad, una por linea:
    # "https://estudiantes.unad.edu.co/gratuidad",
]

# ---------------------------------------------------------------------------
# 2. PALABRAS CLAVE
# ---------------------------------------------------------------------------
# Frase que por si sola ya dispara una alerta de prioridad alta.
KEYWORDS_TRIGGER_ALONE = [
    "política de gratuidad",
    "politica de gratuidad",  # variante sin tilde, por si el HTML la pierde
]

# Palabra "ancla": si aparece junto con alguna de KEYWORDS_SECONDARY,
# se dispara la alerta.
KEYWORD_ANCHOR = "gratuidad"

KEYWORDS_SECONDARY = [
    "inscripción",
    "inscripcion",
    "inscripciones",
    "postulación",
    "postulacion",
    "postulaciones",
    "convocatoria",
    "convocatorias",
    "matrícula",
    "matricula",
    "aspirantes",
    "beneficiarios",
    "2027-i",
    "16-01",
]

# ---------------------------------------------------------------------------
# 3. MENSAJE DIARIO DE ESTADO
# ---------------------------------------------------------------------------
# Cambia a True si quieres recibir un mensaje diario aunque no haya novedades.
SEND_DAILY_STATUS = True

# Hora (hora de Colombia, 0-23) a partir de la cual se envia el mensaje
# de estado, si SEND_DAILY_STATUS = True. Solo se envia una vez por dia.
STATUS_HOUR_BOGOTA = 8

# ---------------------------------------------------------------------------
# 3b. DETECCIÓN DE FALLAS SILENCIOSAS ("el bot está ciego")
# ---------------------------------------------------------------------------
# Si una página se descarga bien pero se extraen menos enlaces que este
# número, se considera sospechoso (posible cambio de diseño del sitio).
# Ajusta este valor tras ver en los logs cuántos enlaces suele encontrar
# normalmente (revisa "Enlaces totales" en el resumen de cada ejecución).
MIN_EXPECTED_ITEMS = 5

# Cuántas revisiones seguidas con fallas (de descarga o de lectura) deben
# pasar antes de mandar una alerta roja de "el bot puede estar ciego".
# Con revisiones cada 2 horas, un valor de 2 significa que te avisa a
# más tardar 4 horas después de que algo empezó a fallar.
FAILURE_ALERT_THRESHOLD = 2

# ---------------------------------------------------------------------------
# 4. ARCHIVO DE ESTADO / DEDUPLICACION
# ---------------------------------------------------------------------------
STATE_FILE = "state.json"

# ---------------------------------------------------------------------------
# 5. RED
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = (
    "Mozilla/5.0 (compatible; MonitorGratuidadUNAD/1.0) "
    "bot personal de un aspirante - revisa la pagina cada 1-2 horas "
    "durante el periodo de convocatoria, contacto vía GitHub del propietario."
)

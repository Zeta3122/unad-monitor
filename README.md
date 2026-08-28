# Monitor Gratuidad UNAD

Bot que revisa noticias.unad.edu.co en busca de novedades sobre la
Política de Gratuidad en la Matrícula (periodo 2027-I, 16-01) y avisa
por Telegram. Se ejecuta en GitHub Actions, sin necesidad de tener el
computador encendido.

Ver la guía completa entregada en la conversación para:
- Instalación paso a paso en GitHub.
- Creación del bot de Telegram con BotFather.
- Configuración de secretos (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).
- Prueba manual y verificación de ejecuciones automáticas.
- Cómo cambiar la frecuencia el 1 de noviembre.
- Qué hacer si algo falla.

Archivos:
- `monitor.py` — lógica principal.
- `config.py` — URLs, palabras clave, mensaje de estado (editable).
- `requirements.txt` — dependencias.
- `state.json` — memoria de publicaciones ya alertadas (se actualiza solo).
- `.github/workflows/monitor-unad.yml` — programación en GitHub Actions.

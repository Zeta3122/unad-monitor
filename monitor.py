#!/usr/bin/env python3
"""
Monitor de la Politica de Gratuidad en la Matricula - UNAD.

Revisa las paginas configuradas en config.py, busca coincidencias de
palabras clave relacionadas con la convocatoria de gratuidad, y envia
una alerta por Telegram cuando encuentra algo nuevo y relevante.

Disenado para ejecutarse en GitHub Actions (ver
.github/workflows/monitor-unad.yml), pero tambien funciona en tu propio
computador si lo deseas (ver instrucciones de prueba manual).
"""

import hashlib
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import urllib3
from bs4 import BeautifulSoup

import config

# El servidor de noticias.unad.edu.co no envía el certificado intermedio
# completo (cadena de confianza incompleta de su lado, no un problema de
# este script). Cuando eso pasa, reintentamos una vez sin verificar el
# certificado. Al hacerlo, silenciamos la advertencia esperada de urllib3
# para no llenar el log de ruido.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOGOTA_TZ = ZoneInfo("America/Bogota")


# ---------------------------------------------------------------------------
# Estado (para no repetir alertas entre ejecuciones)
# ---------------------------------------------------------------------------
def load_state():
    if not os.path.exists(config.STATE_FILE):
        return {"seen": [], "last_status_date": None, "consecutive_fetch_failures": 0, "consecutive_zero_items": 0}
    try:
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("seen", [])
            data.setdefault("last_status_date", None)
            data.setdefault("consecutive_fetch_failures", 0)
            data.setdefault("consecutive_zero_items", 0)
            return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[ADVERTENCIA] No se pudo leer {config.STATE_FILE}, se crea uno nuevo: {e}")
        return {"seen": [], "last_status_date": None, "consecutive_fetch_failures": 0, "consecutive_zero_items": 0}


def save_state(state):
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def make_id(url, title):
    raw = f"{url}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Descarga y extraccion de contenido
# ---------------------------------------------------------------------------
def fetch_page(url):
    headers = {"User-Agent": config.USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.SSLError as e:
        # Cadena de certificados incompleta del lado del servidor (conocido
        # en noticias.unad.edu.co). Reintentamos una sola vez sin verificar
        # el certificado; si el sitio corrige su configuración, este bloque
        # deja de activarse solo y la verificación normal vuelve a aplicar.
        print(f"[ADVERTENCIA] Fallo de verificación SSL en {url}, reintentando sin verificar certificado: {e}")
        try:
            resp = requests.get(
                url, headers=headers, timeout=config.REQUEST_TIMEOUT_SECONDS, verify=False
            )
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e2:
            print(f"[ERROR] No se pudo descargar {url} ni siquiera sin verificar certificado: {e2}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] No se pudo descargar {url}: {e}")
        return None


def extract_items(html, base_url):
    """
    Extrae una lista de items candidatos (titulo, url, texto_contexto)
    a partir de los enlaces visibles de la pagina. Como no conocemos de
    antemano la estructura exacta del HTML de la UNAD, usamos un enfoque
    generico basado en etiquetas <a>, tomando tambien el texto del bloque
    que rodea al enlace como contexto para la busqueda de palabras clave.
    """
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen_local = set()

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"]

        if not title or len(title) < 8:
            continue

        full_url = requests.compat.urljoin(base_url, href)

        parent_text = ""
        if a.parent is not None:
            parent_text = a.parent.get_text(" ", strip=True)

        context_text = f"{title} {parent_text}"

        key = (full_url, title)
        if key in seen_local:
            continue
        seen_local.add(key)

        items.append({
            "title": title,
            "url": full_url,
            "context": context_text,
        })

    return items


# ---------------------------------------------------------------------------
# Evaluacion de palabras clave
# ---------------------------------------------------------------------------
def matches_keywords(text):
    """Devuelve (es_relevante, lista_de_palabras_que_activaron_la_alerta)."""
    text_lower = text.lower()
    hits = []

    for phrase in config.KEYWORDS_TRIGGER_ALONE:
        if phrase.lower() in text_lower:
            hits.append(phrase)

    if config.KEYWORD_ANCHOR in text_lower:
        for secondary in config.KEYWORDS_SECONDARY:
            if secondary.lower() in text_lower:
                hits.append(f"{config.KEYWORD_ANCHOR} + {secondary}")

    return (len(hits) > 0, hits)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def send_telegram_message(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[ERROR] Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en el entorno.")
        return False

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(api_url, data=payload, timeout=config.REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] No se pudo enviar el mensaje de Telegram: {e}")
        return False


def build_alert_message(item, hits):
    now_bogota = datetime.now(BOGOTA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    hits_text = ", ".join(sorted(set(hits)))
    snippet = item["context"][:280].strip()

    return (
        "⚠️ <b>Posible convocatoria de Gratuidad UNAD</b>\n\n"
        f"<b>Título:</b> {item['title']}\n"
        f"<b>Detectado:</b> {now_bogota} (hora Colombia)\n"
        f"<b>URL:</b> {item['url']}\n"
        f"<b>Palabras que activaron la alerta:</b> {hits_text}\n"
        f"<b>Fragmento:</b> {snippet}\n\n"
        "Verifica inmediatamente la información en el sitio oficial de la UNAD."
    )


def build_status_message(pages_ok, pages_total, items_found):
    now_bogota = datetime.now(BOGOTA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    return (
        "✅ Monitor UNAD funcionando; no se detectaron convocatorias nuevas.\n"
        f"Última revisión: {now_bogota} (hora Colombia).\n"
        f"Páginas revisadas con éxito: {pages_ok}/{pages_total} — enlaces encontrados: {items_found}."
    )


def build_health_warning_message(kind, count):
    now_bogota = datetime.now(BOGOTA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    if kind == "descarga":
        detalle = f"no ha podido descargar ninguna de las páginas vigiladas en las últimas {count} revisiones seguidas"
    else:
        detalle = (
            f"descargó la página pero encontró muy pocos enlaces (o ninguno) en las últimas {count} "
            "revisiones seguidas — es posible que la UNAD haya cambiado el diseño de la página"
        )
    return (
        "🔴 <b>Posible falla del monitor UNAD</b>\n\n"
        f"El bot {detalle}.\n"
        f"Hora: {now_bogota} (hora Colombia)\n\n"
        "Esto no significa que haya o no haya convocatoria: significa que el bot "
        "puede no estar revisando bien. Revisa la pestaña Actions en GitHub."
    )


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main():
    state = load_state()
    seen_ids = set(state["seen"])
    new_alerts_sent = 0
    successful_fetches = 0
    total_items_found = 0

    for url in config.URLS:
        print(f"Revisando: {url}")
        html = fetch_page(url)
        if html is None:
            continue

        successful_fetches += 1
        items = extract_items(html, url)
        total_items_found += len(items)
        print(f"  -> {len(items)} enlaces candidatos encontrados")

        for item in items:
            is_relevant, hits = matches_keywords(item["context"])
            if not is_relevant:
                # No se marca como visto: si esta misma pagina se edita mas
                # adelante y se vuelve relevante sin cambiar URL ni titulo,
                # queremos poder detectarla en una proxima ejecucion.
                continue

            item_id = make_id(item["url"], item["title"])
            if item_id in seen_ids:
                continue

            print(f"  [ALERTA] {item['title']} ({item['url']})")
            message = build_alert_message(item, hits)
            if send_telegram_message(message):
                new_alerts_sent += 1
            seen_ids.add(item_id)

    # -----------------------------------------------------------------
    # Chequeo de salud: detectar si el bot esta "ciego" (no descarga
    # nada, o descarga pero no encuentra enlaces) aunque no haya un
    # error de Python que haga fallar la ejecucion. Esto es independiente
    # del mensaje diario de estado: si algo esta mal, avisa aunque
    # SEND_DAILY_STATUS este desactivado y sin esperar a la hora fijada.
    # -----------------------------------------------------------------
    consecutive_fetch_failures = state.get("consecutive_fetch_failures", 0)
    consecutive_zero_items = state.get("consecutive_zero_items", 0)

    if successful_fetches == 0:
        consecutive_fetch_failures += 1
        consecutive_zero_items = 0  # no aplica si ni siquiera hubo descarga
    elif total_items_found < config.MIN_EXPECTED_ITEMS:
        consecutive_fetch_failures = 0
        consecutive_zero_items += 1
    else:
        consecutive_fetch_failures = 0
        consecutive_zero_items = 0

    def _should_warn(count):
        # Avisa la primera vez que se cruza el umbral, y luego cada
        # tantas veces el umbral para no llenar Telegram de alertas.
        return count >= config.FAILURE_ALERT_THRESHOLD and (
            count % config.FAILURE_ALERT_THRESHOLD == 0
        )

    if _should_warn(consecutive_fetch_failures):
        send_telegram_message(build_health_warning_message("descarga", consecutive_fetch_failures))

    if _should_warn(consecutive_zero_items):
        send_telegram_message(build_health_warning_message("lectura", consecutive_zero_items))

    state["consecutive_fetch_failures"] = consecutive_fetch_failures
    state["consecutive_zero_items"] = consecutive_zero_items

    # Mensaje diario de estado (opcional)
    if config.SEND_DAILY_STATUS and new_alerts_sent == 0:
        today_str = datetime.now(BOGOTA_TZ).strftime("%Y-%m-%d")
        current_hour = datetime.now(BOGOTA_TZ).hour
        already_sent_today = state.get("last_status_date") == today_str

        if current_hour >= config.STATUS_HOUR_BOGOTA and not already_sent_today:
            status_msg = build_status_message(successful_fetches, len(config.URLS), total_items_found)
            if send_telegram_message(status_msg):
                state["last_status_date"] = today_str

    state["seen"] = list(seen_ids)
    save_state(state)

    print(
        f"Listo. Alertas nuevas enviadas: {new_alerts_sent}. "
        f"Páginas ok: {successful_fetches}/{len(config.URLS)}. "
        f"Enlaces totales: {total_items_found}."
    )


if __name__ == "__main__":
    main()

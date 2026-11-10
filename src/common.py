"""Utilidades compartidas por los 4 agentes."""
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OPPORTUNITY_FILE = OUTPUT_DIR / "opportunity.json"
HISTORY_FILE = OUTPUT_DIR / "processed_posts.json"

MODEL_FAST = "claude-haiku-5-5"
MODEL_CODER = "claude-sonnet-5-5"

VALID_SOLUTIONS = ("chrome_extension", "single_file_html")
VALID_MODELS = ("monthly_subscription", "lifetime")

# Simula las APIs de Chrome cuando se abre popup.html por file:// (QA y demo).
CHROME_STUB = """
(() => {
  const store = {};
  const keysOf = k => Array.isArray(k) ? k : typeof k === 'string' ? [k] : Object.keys(k || {});
  const wrap = (fn) => (...args) => {
    const cb = typeof args[args.length - 1] === 'function' ? args.pop() : null;
    const res = fn(...args);
    if (cb) { cb(res); return; }
    return Promise.resolve(res);
  };
  const area = {
    get: wrap(k => { const r = {}; keysOf(k).forEach(x => { if (x in store) r[x] = store[x]; }); return r; }),
    set: wrap(o => { Object.assign(store, o); }),
    remove: wrap(k => { keysOf(k).forEach(x => delete store[x]); }),
    clear: wrap(() => { Object.keys(store).forEach(x => delete store[x]); }),
  };
  window.chrome = window.chrome || {};
  window.chrome.runtime = { id: 'qa-stub', lastError: null, getURL: p => p,
    onMessage: { addListener() {} }, sendMessage: wrap(() => undefined) };
  window.chrome.storage = { local: area, sync: area };
  window.chrome.tabs = { query: wrap(() => [{ id: 1, url: 'https://example.com', title: 'Example' }]) };
})();
"""


# Sin esto, una petición colgada de red (SSL, proxy, Wi-Fi inestable...) se queda esperando
# indefinidamente y el único modo de salir es Ctrl+C, como le pasó al usuario. Con el timeout,
# la llamada lanza una excepción a los N segundos y el bucle de reintentos de cada paso la
# captura con normalidad, igual que cualquier otro error de API.
ANTHROPIC_TIMEOUT_SECONDS = float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "180"))


def get_client() -> Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("Error: ANTHROPIC_API_KEY no encontrada en .env")
    return Anthropic(api_key=key, timeout=ANTHROPIC_TIMEOUT_SECONDS)


def safe_slug(name: Any, default: str = "MicroApp") -> str:
    """El nombre de la app viene del LLM (y, indirectamente, de un post público):
    nunca debe usarse tal cual en rutas de disco."""
    slug = re.sub(r"[^A-Za-z0-9]", "", str(name or ""))[:40]
    return slug or default


def safe_join(base: Path, rel: str) -> Path:
    """Une base + rel garantizando que el resultado queda dentro de base."""
    p = PurePosixPath(rel.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError(f"Ruta no permitida: {rel!r}")
    base_r = base.resolve()
    target = (base_r / Path(*p.parts)).resolve()
    if base_r not in target.parents:
        raise ValueError(f"Ruta fuera del directorio de destino: {rel!r}")
    return target


def response_text(response) -> str:
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise RuntimeError("Respuesta truncada por max_tokens")
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text").strip()


def extract_json(raw: str, expect: Optional[type] = None) -> Any:
    """Devuelve el primer valor JSON válido del texto (sin regex voraz)."""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(raw):
        if ch in "{[":
            try:
                obj, _ = decoder.raw_decode(raw, i)
            except json.JSONDecodeError:
                continue
            if expect is None or isinstance(obj, expect):
                return obj
    raise ValueError("No se encontró JSON válido en la respuesta")


MAX_ATTEMPTS_PER_POST = 3
REVIEW_COOLDOWN_HOURS = 12  # no re-analizar con el LLM un post ya descartado antes de este plazo


def load_history() -> Dict[str, Dict]:
    """Historial con estado por URL: {url: {"status": ..., "attempts": N, "reviewed_at": iso}}.

    'done'      -> ya se le vendió/propuso algo; no se vuelve a tocar.
    'failed'    -> el paso 2 (QA automática) falló MAX_ATTEMPTS_PER_POST veces; se descarta.
    'pending'   -> intentado en el paso 2 pero puede reintentarse.
    'reviewed'  -> Claude lo evaluó en el paso 1 y no llegó al umbral de viabilidad; no se
                   vuelve a enviar al LLM hasta pasado REVIEW_COOLDOWN_HOURS (ahorra tokens,
                   ya que el post no ha cambiado y la evaluación no va a variar mientras tanto).
    Compatible con el formato antiguo (lista de URLs = todas 'done').
    """
    if not HISTORY_FILE.exists():
        return {}
    try:
        raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(raw, list):  # migración desde el formato antiguo
        return {u: {"status": "done", "attempts": 1} for u in raw}
    return raw if isinstance(raw, dict) else {}


def save_history(history: Dict[str, Dict]):
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def urls_to_skip(history: Dict[str, Dict]) -> set:
    """Excluye las resueltas/agotadas (done, failed) y las revisadas recientemente
    (reviewed, dentro del periodo de enfriamiento). Las 'pending' siempre se reintentan."""
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)
    skip = set()
    for u, v in history.items():
        status = v.get("status")
        if status in ("done", "failed"):
            skip.add(u)
        elif status == "reviewed":
            reviewed_at = v.get("reviewed_at")
            try:
                age_h = (now - _dt.datetime.fromisoformat(reviewed_at)).total_seconds() / 3600
            except (TypeError, ValueError):
                age_h = REVIEW_COOLDOWN_HOURS  # sin fecha válida: no bloquear, dejar reevaluar
            if age_h < REVIEW_COOLDOWN_HOURS:
                skip.add(u)
    return skip


def record_attempt(url: str, success: bool):
    history = load_history()
    entry = history.get(url, {"status": "pending", "attempts": 0})
    entry["attempts"] = entry.get("attempts", 0) + 1
    if success:
        entry["status"] = "done"
    elif entry["attempts"] >= MAX_ATTEMPTS_PER_POST:
        entry["status"] = "failed"
    else:
        entry["status"] = "pending"
    history[url] = entry
    save_history(history)


def record_reviewed(urls, exclude: str = None):
    """Marca posts evaluados por el LLM en el paso 1 que no llegaron al umbral de viabilidad,
    para no volver a gastar tokens en ellos antes de REVIEW_COOLDOWN_HOURS. 'exclude' es la
    URL elegida como oportunidad (si la hay), que no debe marcarse como descartada."""
    import datetime as _dt
    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
    history = load_history()
    for u in urls:
        if u == exclude or u in history:  # no pisar un estado ya existente (pending/done/failed)
            continue
        history[u] = {"status": "reviewed", "reviewed_at": now_iso}
    save_history(history)


def load_opportunity() -> Dict:
    if not OPPORTUNITY_FILE.exists():
        raise FileNotFoundError(f"No existe {OPPORTUNITY_FILE}. Ejecuta el Script 01 primero.")
    with open(OPPORTUNITY_FILE, "r", encoding="utf-8") as f:
        opp = json.load(f)
    for key in ("app_name", "solution_type", "pain_summary", "core_features", "pricing", "selected_post"):
        if key not in opp:
            raise ValueError(f"opportunity.json incompleto: falta '{key}'")
    if opp["solution_type"] not in VALID_SOLUTIONS:
        raise ValueError(f"solution_type inválido: {opp['solution_type']}")
    opp["app_name"] = safe_slug(opp["app_name"])
    return opp

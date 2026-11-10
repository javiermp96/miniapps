# Pipeline de micro-apps — uso real, supervisado

Este proyecto busca demanda en Reddit, genera una micro-herramienta con Claude,
la valida automáticamente y te prepara un enlace de pago y una propuesta de venta.
**No automatiza la venta de principio a fin**: hay dos puntos de parada obligatorios
donde tienes que intervenir tú, y así debe seguir siendo.

## Instalación

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # y rellena las claves
```

## Uso

```bash
python main.py                      # ciclo completo, con los gates de revisión
python main.py --from-step 3        # reanudar desde un paso concreto
python main.py --only 2             # ejecutar un solo paso
```

### Los dos gates obligatorios

1. **Tras el paso 2** (`human_qa_gate`): la QA automática solo comprueba que la
   herramienta carga sin errores de consola, NUNCA que hace bien su trabajo. Antes
   de seguir, el pipeline se para y te pide abrir la herramienta y probarla con
   datos reales. Esto es tu responsabilidad, no se puede automatizar.
2. **Antes del paso 4** (`sales_gate`): te muestra el riesgo de demanda detectado y
   el precio sugerido (una fórmula, no una verdad) antes de crear el cobro.

Puedes saltarte ambos con `--skip-human-qa` / `--skip-sales-gate`, pero no es
recomendable: son la única salvaguarda antes de poner tu nombre y tu dinero detrás
de algo generado por un LLM.

## Qué NO hace este proyecto (y por qué)

- **No envía nada por ti.** El paso 4 solo escribe el texto de la propuesta en un
  `.txt`. Enviar DMs comerciales no solicitados en Reddit viola sus normas y puede
  acabar en un baneo de cuenta — decide tú el canal.
- **No valida que haya demanda real.** Un post de Reddit no es un cliente validado:
  puede que ya exista una alternativa gratuita, o que el autor ya resolviera su
  problema. El campo `demand_risk` en `opportunity.json` te da una señal, pero la
  decisión final es tuya (gate 2).
- **No gestiona impuestos, facturación ni licencias.** Mira `legal/` para
  plantillas de partida — tienes que hacerlas revisar por un profesional y darte
  de alta en tu régimen fiscal antes de cobrar nada en serio.
- **No fuerza el cumplimiento de la licencia.** El producto es un ZIP local sin
  servidor de licencias: tras el primer pago, técnicamente el cliente se lo queda.
  Si eso te preocupa, considera pasar a pago único en vez de suscripción, o montar
  un backend de licencias (fuera del alcance de este proyecto).

## Entrega al cliente

Si el resultado es una extensión de Chrome, instalarla exige activar el "modo
desarrollador" en `chrome://extensions`. El ZIP incluye un `INSTALL.md` con los
pasos exactos para el cliente. El prompt del paso 1 prioriza `single_file_html`
(se abre con doble clic, sin fricción) y solo elige extensión cuando la tarea
realmente necesita interactuar con páginas de terceros mientras el usuario navega.
Para vender extensiones a más escala, publícalas en la Chrome Web Store (5 USD,
con revisión de Google) en vez de repartir ZIPs.

## Reintentos

Si un post falla la QA del paso 2, no se descarta: queda en estado `pending` en
`output/processed_posts.json` y se reintenta en la próxima ejecución, hasta un
máximo de `MAX_ATTEMPTS_PER_POST` (3) intentos, tras los cuales pasa a `failed` y
se descarta. No hace falta borrar nada a mano.

## Reddit RSS bloqueado (429/403)

El RSS público de Reddit suele bloquear peticiones desde IPs de servidores/cloud.
Si te pasa, configura `REDDIT_CLIENT_ID` y `REDDIT_CLIENT_SECRET` en `.env` (API
oficial, gratis en https://www.reddit.com/prefs/apps) y el paso 1 la usará
automáticamente en vez del RSS.

## Fuentes de demanda

El paso 1 ya no busca solo en Reddit: también consulta **Hacker News** (vía la API
pública de Algolia) y **Stack Overflow** (vía la API pública de Stack Exchange),
ambas sin necesidad de credenciales. Puedes activar/desactivar fuentes con
`SOURCES` en `.env` (por ejemplo `SOURCES=reddit,hackernews` para quitar Stack
Overflow). Cada fuente falla de forma independiente: si una se cae, las demás
siguen funcionando.

## "Nunca se cumplen los criterios de viabilidad"

Si el paso 1 nunca encuentra nada viable, antes de tocar el umbral a ciegas,
ejecuta:

```bash
python src/01_demand_scout.py --debug
```

Esto te muestra el top 5 de candidatas de esa tanda con la puntuación que les dio
Claude y el motivo. Te deja ver si el problema es:
- **El umbral es demasiado alto** para el volumen real de buenas oportunidades en
  tus fuentes — baja `MIN_SCORE` en `.env` (por defecto 6.0) con esta evidencia en
  la mano, no a ciegas.
- **Las fuentes no traen material adecuado** — en ese caso amplía `SOURCES`,
  cambia `REDDIT_SUBREDDITS`, o añade tus propias palabras clave a `HN_QUERIES`/
  `SE_TAGS` en `src/01_demand_scout.py`.

Cada post evaluado y descartado se marca como `reviewed` en
`output/processed_posts.json` y no se vuelve a analizar hasta pasado el
enfriamiento (`REVIEW_COOLDOWN_HOURS`, 12 h por defecto en `src/common.py`), para
no gastar tokens reevaluando lo mismo en cada ejecución.

Desde `main.py` también puedes pasarlo: `python main.py --debug` (se reenvía al
paso 1 automáticamente).

## "Respuesta truncada por max_tokens"

Con muchas candidatas (3 fuentes a la vez puede dar 50-60+ posts), la respuesta
del modelo puede superar el límite de tokens de salida. El paso 1 ya lo detecta y
reintenta automáticamente una vez con solo las 25 candidatas más recientes en vez
de perder toda la tanda. Si sigue fallando con 25, revisa tu conexión o baja
manualmente `SOURCES` a una sola fuente para esa ejecución.

## Error SSL "CERTIFICATE_VERIFY_FAILED" (típico en Windows)

Si ves `self-signed certificate in certificate chain`, casi siempre es un
antivirus con inspección HTTPS (Kaspersky, Avast, ESET...) o un proxy corporativo
que intercepta el tráfico con su propio certificado: Windows confía en él, pero el
almacén de certificados que usa Python por defecto (`certifi`) no. La solución
recomendada:

```bash
pip install truststore
```

El paso 1 lo detecta automáticamente si está instalado y verifica usando el
almacén de certificados del propio sistema operativo, igual que hace tu
navegador — sin desactivar la verificación TLS en ningún momento. Si prefieres no
instalarlo, el proyecto sigue funcionando igual, solo con ese riesgo de bloqueo en
redes con ese tipo de interceptación.

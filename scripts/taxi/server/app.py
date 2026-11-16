"""EV7 Smart Taxi Monitor — web server + AI-agent proxy

Serves the built web folder (build_dashboard.py --web <dir>) and relays the assistant's questions to Claude.
The server is stateless: the browser sends the whole conversation each time, Claude asks for tools,
and the browser runs those tools on its own data (plates and positions never reach the server —
vehicles appear only as car:<id>). The server only holds the API key.

Run (dev):
    pip install -r scripts/taxi/server/requirements.txt
    set WEB_DIR=D:\\Taxi\\dashboard_v3            (the folder built by build_dashboard.py --web)
    set ANTHROPIC_API_KEY=...                     (optional — without it the page uses the offline assistant)
    set EV7_USER=ops & set EV7_PASS=...           (optional basic auth — strongly recommended: the data has plates/VINs)
    uvicorn app:app --app-dir scripts/taxi/server --port 8080

⚠️ Never put the API key in the web files or the repo — environment / secret manager only.
"""
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(os.environ.get("WEB_DIR", Path(__file__).parent / "web"))
MODEL = os.environ.get("EV7_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("EV7_EFFORT", "low")            # low | medium | high — low is enough for tool routing
MAX_TOKENS = int(os.environ.get("EV7_MAX_TOKENS", "2048"))
AUTH = (os.environ.get("EV7_USER"), os.environ.get("EV7_PASS"))

client = None
if os.environ.get("ANTHROPIC_API_KEY"):
    import anthropic
    client = anthropic.Anthropic()

SYSTEM = """You are the assistant inside "EV7 Smart Taxi Monitor", a read-only map dashboard of a Thai EV taxi fleet.
Users are fleet operations staff. Answer questions about the fleet using the tools; they run in the user's browser
and also move the map / timeline to show the answer, so say briefly what is now shown.

Rules:
- Reply in the user's language: Thai if the question contains Thai, otherwise English. Be short and concrete — numbers first.
- Vehicles are identified only as car:<id>. Always write a vehicle as [[car:<id>]] exactly (the page turns it into the plate).
  Never guess a plate or make up an id. A user message may already contain [[car:<id>]] for a plate they typed.
- The data is a batch pull, not live: "now" means the latest point in the data (see context). Quote the as-of time.
- Time arguments: "now", "today", "yesterday", "HH:MM", "YYYY-MM-DD", "YYYY-MM-DD HH:MM", or Thai expressions (ตี 3, บ่าย 2).
- Places: Thai provinces/districts in Thai or English, plus landmarks such as Siam or Suvarnabhumi.
- The dashboard cannot control vehicles (cut power, lock, stop, message drivers) — say so. When the user asks to cut power for a
  specific car, still run parking_status and report whether it would be safe now and why, so they can act in the telematics system.
- EV charger data comes from OpenStreetMap and covers only part of the real network — never claim an area has no chargers.
- If a tool returns an error, explain it plainly. Only answer from tool results and the context; say when you don't know.
- Questions unrelated to the fleet: say what you can help with instead."""

_T = {"type": "string"}
TOOLS = [
    {"name": "cars_in_area", "description": "Vehicles online in a province, district or landmark at a time, with counts by status. Highlights them on the map.",
     "input_schema": {"type": "object", "properties": {
         "place": {"type": "string", "description": "Province, district or landmark, Thai or English"},
         "time": {"type": "string", "description": "Default: now (latest data)"},
         "status": {"type": "string", "enum": ["on_trip", "available", "parked"]}}, "required": ["place"]}},
    {"name": "vehicle_status", "description": "Where one vehicle is and what it is doing at a time. Selects it on the map.",
     "input_schema": {"type": "object", "properties": {"car": {"type": "string", "description": "car:<id>"}, "time": _T}, "required": ["car"]}},
    {"name": "vehicle_track", "description": "Route summary of one vehicle over a period (km, top speed, provinces, start/end). Draws the route.",
     "input_schema": {"type": "object", "properties": {"car": {"type": "string", "description": "car:<id>"},
         "time": {"type": "string", "description": "today · yesterday · YYYY-MM-DD · empty = all data"}}, "required": ["car"]}},
    {"name": "out_of_zone", "description": "Vehicles that left the allowed zone in a period: counts by level and the top vehicles. Opens the Out of zone panel.",
     "input_schema": {"type": "object", "properties": {"time": {"type": "string", "description": "today · yesterday · YYYY-MM-DD · empty = all data"},
         "zone": {"type": "string", "enum": ["bkk", "bkk_air", "metro"], "description": "bkk = Bangkok only · bkk_air = + Suvarnabhumi · metro = + vicinity"}}}},
    {"name": "fleet_stats", "description": "Fleet snapshot at a time: online, by status, share on trip, outside the zone, areas with most vehicles. Optional place narrows it (a province ranks its districts).",
     "input_schema": {"type": "object", "properties": {"time": _T, "place": _T, "level": {"type": "string", "enum": ["province", "district"]}}}},
    {"name": "nearest_chargers", "description": "Nearest EV chargers to a vehicle, a place, or the map centre. Shows them numbered on the map.",
     "input_schema": {"type": "object", "properties": {"car": {"type": "string", "description": "car:<id>"}, "place": _T, "time": _T,
         "n": {"type": "integer", "minimum": 1, "maximum": 10}}}},
    {"name": "parking_status", "description": "Is one vehicle really parked, and where (EV charger · depot · home = its usual overnight spot · street), engine state, and whether cutting its power would be safe now under two rules — basic (parked / engine off ≥ 10 min) and off-road (also not on a public road; road distance is the median over the still GPS points with a ±8–12 m margin) — with reasons. The dashboard cannot send the command itself.",
     "input_schema": {"type": "object", "properties": {"car": {"type": "string", "description": "car:<id>"}, "time": _T}, "required": ["car"]}},
    {"name": "peak_time", "description": "When the most vehicles were on a trip / online, and the quietest time. Moves the timeline to the peak.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "data_info", "description": "Period covered by the data, number of vehicles and GPS points.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "control_map", "description": "Change the page: open a panel, base map, 2D/3D, zoom, layers, or clear highlights.",
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["open_panel", "set_basemap", "set_view", "zoom_bangkok", "zoom_thailand", "zoom_place", "toggle_layer", "clear"]},
         "panel": {"type": "string", "enum": ["overview", "vehicles", "zone", "parking", "areas"]},
         "basemap": {"type": "string", "enum": ["light", "streets", "satellite"]},
         "view": {"type": "string", "enum": ["2d", "3d"]},
         "layer": {"type": "string", "enum": ["ev_chargers", "area_colors"]},
         "on": {"type": "boolean"}, "place": _T}, "required": ["action"]}},
]

app = FastAPI(title="EV7 Smart Taxi Monitor", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=2048)      # html/css/js (the data files are already compressed inside)


@app.middleware("http")
async def guard(request: Request, call_next):
    # optional basic auth for everything (page, data, API) — the data contains plates / VINs / positions
    if AUTH[0] and AUTH[1]:
        import base64
        ok = False
        h = request.headers.get("authorization", "")
        if h.lower().startswith("basic "):
            try:
                u, _, p = base64.b64decode(h[6:]).decode().partition(":")
                ok = secrets.compare_digest(u, AUTH[0]) and secrets.compare_digest(p, AUTH[1])
            except Exception:
                ok = False
        if not ok:
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="EV7"'})
    res = await call_next(request)
    p = request.url.path
    if p.startswith("/api/"):
        res.headers["Cache-Control"] = "no-store"
    elif p == "/" or p.endswith(".html") or p.startswith("/data/"):
        # always ask the server, but reuse the copy when unchanged (ETag → 304) — the road file is 11 MB
        res.headers["Cache-Control"] = "private, no-cache"
    elif "v=" in request.url.query:
        res.headers["Cache-Control"] = "private, max-age=31536000, immutable"   # css/js named by content hash
    res.headers["X-Content-Type-Options"] = "nosniff"
    res.headers["Referrer-Policy"] = "same-origin"
    return res


@app.get("/api/health")
def health():
    return {"ok": True, "ai": client is not None, "endpoint": "/api/agent" if client else None, "model": MODEL if client else None}


@app.post("/api/agent")
async def agent(request: Request):
    if client is None:
        return JSONResponse({"error": "AI agent is not configured on this server (no ANTHROPIC_API_KEY)."}, status_code=503)
    body = await request.body()
    if len(body) > 400_000:
        return JSONResponse({"error": "conversation too long — start a new chat"}, status_code=413)
    try:
        data = await request.json()
        messages = data["messages"]
        assert isinstance(messages, list) and 0 < len(messages) <= 60
        assert all(m.get("role") in ("user", "assistant") for m in messages)
    except Exception:
        return JSONResponse({"error": "bad request"}, status_code=400)
    ctx = data.get("context") or {}
    context = "Page context (JSON): " + str({k: ctx.get(k) for k in (
        "data_from", "data_to", "timeline_cursor", "selected_range", "zone", "selected_car", "open_panel")})
    try:
        resp = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": context}],
            tools=TOOLS, messages=messages,
            output_config={"effort": EFFORT},
        )
    except anthropic.APIStatusError as e:
        return JSONResponse({"error": f"Claude API {e.status_code}: {e.message}"}, status_code=502)
    except anthropic.APIError as e:
        return JSONResponse({"error": f"Claude API: {e}"}, status_code=502)
    # content goes back to the browser, which echoes it unchanged in the next request (keeps thinking/tool_use intact)
    return {"content": [b.model_dump(exclude_none=True) for b in resp.content], "stop_reason": resp.stop_reason}


if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

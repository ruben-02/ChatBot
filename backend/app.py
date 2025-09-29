import os
import json
import sqlite3
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai  # keep as you had

DB_FILE = "chatbots.db"
APP_HOST = "0.0.0.0"
APP_PORT = int(os.environ.get("PORT", 5000))

app = Flask(__name__)
CORS(app, origins=["https://chatbot-frontend-hwuf.onrender.com"], supports_credentials=True)

# ---------------- Datasources ----------------
DATASOURCES = {
    "zoho": {"label": "Zoho", "subproducts": ["books", "crm", "sheet"]},
    "hubspot": {"label": "HubSpot", "subproducts": ["crm_contacts", "crm_deals", "crm_companies"]},
    "freshdesk": {"label": "Freshdesk", "subproducts": ["tickets", "contacts"]},
    "google_sheets": {"label": "Google Sheets", "subproducts": ["sheet"]},
    "Odoo": {"label": "Odoo", "subproducts": ["crm", "sales", "inventory","Todo",]},
}

# ---------------- Database ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS connectors (
        id TEXT PRIMARY KEY,
        username TEXT,
        datasource TEXT,
        subproduct TEXT,
        config_json TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS chatbots (
        id TEXT PRIMARY KEY,
        username TEXT,
        chatbot_name TEXT,
        gemini_api_key TEXT,
        gemini_model TEXT,
        connector_id TEXT,
        extra_config TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chatbot_id TEXT,
        role TEXT, -- 'user' or 'bot'
        message TEXT,
        created_at TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# ---------------- DB helpers ----------------
def save_connector(connector_id, username, datasource, subproduct, config_dict):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""INSERT OR REPLACE INTO connectors 
        (id, username, datasource, subproduct, config_json)
        VALUES (?, ?, ?, ?, ?)""",
        (connector_id, username, datasource, subproduct, json.dumps(config_dict))
    )
    conn.commit()
    conn.close()

def get_connector(connector_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM connectors WHERE id=?", (connector_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def list_chatbots_db(username):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM chatbots WHERE username=?", (username,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_chatbot_db(chatbot_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM chatbots WHERE id=?", (chatbot_id,))
    cur.execute("DELETE FROM chat_history WHERE chatbot_id=?", (chatbot_id,))
    conn.commit()
    conn.close()

def save_chat_message(chatbot_id, role, message):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO chat_history (chatbot_id, role, message, created_at) VALUES (?, ?, ?, ?)",
                (chatbot_id, role, message, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_chat_history_db(chatbot_id, limit=500):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT role, message, created_at FROM chat_history WHERE chatbot_id=? ORDER BY id ASC LIMIT ?",
                (chatbot_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [{"role": r["role"], "message": r["message"], "created_at": r["created_at"]} for r in rows]

# ---------------- API Clients / Fetchers ----------------
def fetch_zoho(config, subproduct):
    try:
        # Zoho API shape varies; user should supply an access_token in config
        token = config.get("access_token")
        if not token:
            return {"error": "Zoho config missing access_token"}
        # Very generic attempt; specific endpoints depend on subproduct
        if subproduct == "books":
            base = "https://www.zohoapis.com/books/v3/"
            endpoint = "organizations"
        elif subproduct == "crm":
            # CRM has many endpoints; try /users
            base = "https://www.zohoapis.com/crm/v2/"
            endpoint = "users"
        elif subproduct == "sheet":
            # Zoho sheet APIs are different; user likely uses Google Sheets instead
            return {"error": "Zoho sheet access not implemented; use google_sheets datasource for Google Sheets"}
        else:
            return {"error": "Unsupported Zoho subproduct"}
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        resp = requests.get(base + endpoint, headers=headers, timeout=10)
        try:
            return resp.json()
        except ValueError:
            return {"error": "Invalid JSON from Zoho", "text": resp.text}
    except Exception as e:
        return {"error": str(e)}

def fetch_freshdesk(config, subproduct):
    try:
        domain = config.get("domain")
        api_key = config.get("api_key")
        if not domain or not api_key:
            return {"error": "Missing domain or api_key in Freshdesk config"}
        url = f"https://{domain}.freshdesk.com/api/v2/{subproduct}"
        resp = requests.get(url, auth=(api_key, "X"), timeout=10)
        try:
            return resp.json()
        except ValueError:
            return {"error": "Invalid JSON from Freshdesk", "text": resp.text}
    except Exception as e:
        return {"error": str(e)}

def fetch_hubspot(config, subproduct):
    try:
        token = config.get("access_token")
        if not token:
            return {"error": "HubSpot config missing access_token"}
        headers = {"Authorization": f"Bearer {token}"}

        if subproduct == "crm_contacts":
            url = "https://api.hubapi.com/crm/v3/objects/contacts"
        elif subproduct == "crm_deals":
            url = "https://api.hubapi.com/crm/v3/objects/deals"
        elif subproduct == "crm_companies":
            url = "https://api.hubapi.com/crm/v3/objects/companies"
        else:
            return {"error": "Unsupported HubSpot subproduct"}

        resp = requests.get(url, headers=headers, timeout=10)
        try:
            return resp.json()
        except ValueError:
            return {"error": "Invalid JSON from HubSpot", "text": resp.text}
    except Exception as e:
        return {"error": str(e)}

def fetch_google_sheets(config, subproduct):
    """
    config examples:
    - { "sheet_id": "...", "range": "Sheet1!A1:C100", "api_key": "..." }
    - or using OAuth token: { "sheet_id": "...", "range":"Sheet1", "access_token":"..." }
    If range not provided, reads first sheet values by using range = "Sheet1"
    """
    try:
        sheet_id = config.get("sheet_id") or config.get("spreadsheet_id")
        if not sheet_id:
            return {"error": "Missing sheet_id in config"}
        # prefer explicit range, else try "Sheet1"
        rng = config.get("range", config.get("tab", "Sheet1"))
        access_token = config.get("access_token")
        api_key = config.get("api_key")
        if access_token:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{rng}"
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = requests.get(url, headers=headers, timeout=10)
        elif api_key:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{rng}?key={api_key}"
            resp = requests.get(url, timeout=10)
        else:
            return {"error": "Provide either api_key or access_token in config"}
        try:
            return resp.json()
        except ValueError:
            return {"error": "Invalid JSON from Google Sheets", "text": resp.text}
    except Exception as e:
        return {"error": str(e)}
    




def fetch_odoo(config, subproduct):
    """
    Example config:
    {
        "base_url": "https://yourcompany.odoo.com",
        "db": "your_db_name",
        "username": "user@example.com",
        "password": "yourpassword",
        "api_key": "optional_api_key"
    }
    """
    try:
        base_url = config.get("base_url")
        db = config.get("db")
        username = config.get("username")
        password = config.get("password")
        api_key = config.get("api_key")  # Optional

        if not all([base_url, db, username, password]):
            return {"error": "Missing required Odoo connection details (base_url, db, username, password)"}

        # Construct endpoint based on subproduct
        if subproduct == "crm":
            endpoint = "/api/crm.lead"
        elif subproduct == "sales":
            endpoint = "/api/sale.order"
        elif subproduct == "inventory":
            endpoint = "/api/stock.inventory"
        elif subproduct == "Todo":
            endpoint = "/api/project.task"
        else:
            return {"error": "Unsupported Odoo subproduct"}

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Simple GET request to Odoo endpoint (assuming Odoo REST API module installed)
        url = f"{base_url}{endpoint}"
        resp = requests.get(url, auth=(username, password), headers=headers, timeout=10)

        try:
            return resp.json()
        except ValueError:
            return {"error": "Invalid JSON from Odoo", "text": resp.text}

    except Exception as e:
        return {"error": str(e)}


# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"message":"Unified Chatbot backend running", "datasources": list(DATASOURCES.keys())})

@app.route("/datasources", methods=["GET"])
def get_datasources():
    return jsonify(DATASOURCES)

@app.route("/connect", methods=["POST"])
def connect_datasource():
    data = request.json
    connector_id = data.get("connector_id")
    username = data.get("username")
    datasource = data.get("datasource")
    subproduct = data.get("subproduct")
    config = data.get("config", {})
    if not all([connector_id, username, datasource, subproduct]):
        return jsonify({"error":"Missing required fields"}), 400
    if datasource not in DATASOURCES:
        return jsonify({"error":"Unknown datasource"}), 400
    if subproduct not in DATASOURCES[datasource]["subproducts"]:
        return jsonify({"error":"Unsupported subproduct for datasource"}), 400

    save_connector(connector_id, username, datasource, subproduct, config)
    return jsonify({"message":"Connector saved", "connector_id": connector_id})

@app.route("/test_connection/<connector_id>", methods=["GET"])
def test_connection(connector_id):
    conn = get_connector(connector_id)
    if not conn:
        return jsonify({"error":"Connector not found"}), 404
    datasource, subproduct = conn["datasource"], conn["subproduct"]
    config = json.loads(conn["config_json"])
    if datasource == "zoho":
        result = fetch_zoho(config, subproduct)
    elif datasource == "freshdesk":
        result = fetch_freshdesk(config, subproduct)
    elif datasource == "hubspot":
        result = fetch_hubspot(config, subproduct)
    elif datasource == "google_sheets":
        result = fetch_google_sheets(config, subproduct)

    elif datasource.lower() == "odoo":
        result = fetch_odoo(config, subproduct)

    else:
        result = {"error":"Unsupported datasource"}
    return jsonify(result)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    chatbot_id = data.get("chatbot_id")
    user_message = data.get("message")
    if not chatbot_id or user_message is None:
        return jsonify({"error":"Missing chatbot_id or message"}), 400

    # Fetch chatbot info
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM chatbots WHERE id=?", (chatbot_id,))
    bot = cur.fetchone()
    conn.close()
    if not bot:
        return jsonify({"error":"Chatbot not found"}), 404

    gemini_api_key = bot["gemini_api_key"]
    gemini_model = bot["gemini_model"]

    # Save user message
    save_chat_message(chatbot_id, "user", user_message)

    # ---------------- Enrich message with connector data ----------------
    enriched_message = user_message
    connector_info = get_connector(bot["connector_id"])
    if connector_info:
        datasource = connector_info["datasource"]
        config = json.loads(connector_info["config_json"])

    # ---------- Google Sheets ----------
    if datasource == "google_sheets":
        sheet_data = fetch_google_sheets(config, "sheet")
        if "values" in sheet_data:
            headers = sheet_data["values"][0]
            rows = sheet_data["values"][1:]
            sheet_text = "\n".join([
                ", ".join([f"{h}: {v}" for h, v in zip(headers, row)])
                for row in rows
            ])
            sheet_text = sheet_text[:2000]
            enriched_message = f"{user_message}\n\nReference Data from Google Sheet:\n{sheet_text}"

    # ---------- Odoo ----------
    elif datasource.lower() == "odoo":
        odoo_data = fetch_odoo(config, connector_info["subproduct"])
        if isinstance(odoo_data, list) and len(odoo_data) > 0:
            odoo_text = "\n".join([
                ", ".join([f"{k}: {v}" for k, v in item.items()])
                for item in odoo_data[:20]  # limit to first 20 records
            ])
            odoo_text = odoo_text[:2000]
            enriched_message = f"{user_message}\n\nReference Data from Odoo ({connector_info['subproduct']}):\n{odoo_text}"
        elif isinstance(odoo_data, dict) and "error" in odoo_data:
            enriched_message = f"{user_message}\n\n(Odoo fetch error: {odoo_data['error']})"

    # ---------- Freshdesk ----------
    elif datasource.lower() == "freshdesk":
        fresh_data = fetch_freshdesk(config, connector_info["subproduct"])
        if isinstance(fresh_data, list) and len(fresh_data) > 0:
            fresh_text = "\n".join([
                ", ".join([f"{k}: {v}" for k, v in item.items()])
                for item in fresh_data[:20]
            ])
            fresh_text = fresh_text[:2000]
            enriched_message = f"{user_message}\n\nReference Data from Freshdesk ({connector_info['subproduct']}):\n{fresh_text}"
        elif isinstance(fresh_data, dict) and "error" in fresh_data:
            enriched_message = f"{user_message}\n\n(Freshdesk fetch error: {fresh_data['error']})"

    # ---------- HubSpot ----------
    elif datasource.lower() == "hubspot":
        hubspot_data = fetch_hubspot(config, connector_info["subproduct"])
        if "results" in hubspot_data and isinstance(hubspot_data["results"], list):
            hubspot_text = "\n".join([
                ", ".join([f"{k}: {v}" for k, v in item.items()])
                for item in hubspot_data["results"][:20]
            ])
            hubspot_text = hubspot_text[:2000]
            enriched_message = f"{user_message}\n\nReference Data from HubSpot ({connector_info['subproduct']}):\n{hubspot_text}"
        elif isinstance(hubspot_data, dict) and "error" in hubspot_data:
            enriched_message = f"{user_message}\n\n(HubSpot fetch error: {hubspot_data['error']})"

    # ---------- Zoho ----------
    elif datasource.lower() == "zoho":
        zoho_data = fetch_zoho(config, connector_info["subproduct"])
        if isinstance(zoho_data, dict) and "data" in zoho_data and isinstance(zoho_data["data"], list):
            zoho_text = "\n".join([
                ", ".join([f"{k}: {v}" for k, v in item.items()])
                for item in zoho_data["data"][:20]
            ])
            zoho_text = zoho_text[:2000]
            enriched_message = f"{user_message}\n\nReference Data from Zoho ({connector_info['subproduct']}):\n{zoho_text}"
        elif isinstance(zoho_data, dict) and "error" in zoho_data:
            enriched_message = f"{user_message}\n\n(Zoho fetch error: {zoho_data['error']})"

    # ---------------- Call Gemini API ----------------
    try:
        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(model=gemini_model, contents=enriched_message)
        # Handle different SDK response formats
        answer = getattr(response, "text", None) or (response.get("content") if isinstance(response, dict) else str(response))
    except Exception as e:
        answer = f"Gemini API error: {str(e)}"

    # Save bot reply
    save_chat_message(chatbot_id, "bot", answer)

    return jsonify({"reply": answer})

@app.route("/save_chatbot", methods=["POST"])
def save_chatbot():
    data = request.json
    chatbot_id = data.get("id")
    username = data.get("username")
    chatbot_name = data.get("chatbot_name")
    gemini_api_key = data.get("gemini_api_key")
    gemini_model = data.get("gemini_model","gemini-1.5-flash")
    connector_id = data.get("connector_id")
    extra_config = json.dumps(data.get("extra_config",{}))
    if not all([chatbot_id, username, chatbot_name, gemini_api_key, connector_id]):
        return jsonify({"error":"Missing required fields"}), 400
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""INSERT OR REPLACE INTO chatbots
        (id, username, chatbot_name, gemini_api_key, gemini_model, connector_id, extra_config)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (chatbot_id, username, chatbot_name, gemini_api_key, gemini_model, connector_id, extra_config))
    conn.commit()
    conn.close()
    return jsonify({"message":"Chatbot saved", "chatbot_id": chatbot_id})

# ---------- New endpoints expected by your frontend ----------
@app.route("/list_chatbots/<username>", methods=["GET"])
def list_chatbots(username):
    bots = list_chatbots_db(username)
    # Normalize keys to match frontend expectations (id, connector_id, chatbot_name)
    out = []
    for b in bots:
        out.append({
            "id": b["id"],
            "chatbot_name": b.get("chatbot_name"),
            "connector_id": b.get("connector_id")
        })
    return jsonify(out)

@app.route("/get_chat_history/<chatbot_id>", methods=["GET"])
def get_chat_history(chatbot_id):
    history = get_chat_history_db(chatbot_id)
    # Keep same shape as frontend expects: { role: "user"|"bot", message: "..."}
    out = [{"role": h["role"], "message": h["message"], "created_at": h.get("created_at")} for h in history]
    return jsonify(out)

@app.route("/delete_chatbot/<chatbot_id>", methods=["DELETE"])
def delete_chatbot(chatbot_id):
    delete_chatbot_db(chatbot_id)
    return jsonify({"message":"Chatbot and history deleted"})

if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=True)
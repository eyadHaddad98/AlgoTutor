import json
import logging
from pathlib import Path
import secrets
import threading
from uuid import uuid4
from urllib.parse import urlsplit
from flask import Flask, jsonify, render_template, request, session, send_file
from werkzeug.exceptions import HTTPException
from .config import Settings, ROOT
from .storage import Store
from .retrieval import Retriever
from .agent import Tutor
from .catalog import public_catalog, CATALOG
from .algorithms import InputError
from .chat_history import register_chat_history


def create_app(settings=None, store=None, retriever=None, tutor=None):
    settings = settings or Settings()
    if settings.demo:
        instance = ROOT / "instance"
        instance.mkdir(exist_ok=True)
        if not settings.secret_key:
            secret_file = instance / "demo-secret"
            if not secret_file.exists():
                secret_file.write_text(secrets.token_hex(32), encoding="utf-8")
            settings.secret_key = secret_file.read_text(encoding="utf-8").strip()
        settings.database_url = settings.database_url or "sqlite:///" + str(instance / "demo.sqlite3")
    if len(settings.secret_key) < 32:
        raise ValueError("SECRET_KEY must contain at least 32 characters. Run python scripts/setup.py.")
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.json.ensure_ascii = False
    app.config.update(SECRET_KEY=settings.secret_key, MAX_CONTENT_LENGTH=100_000,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=settings.secure_cookie)
    store = store or Store(settings.database_url, allow_sqlite=settings.demo)
    store.init()
    retriever = retriever or Retriever(settings)
    tutor = tutor or Tutor(settings, store, retriever)
    app.extensions.update(store=store, retriever=retriever, tutor=tutor)
    locks = [threading.Lock() for _ in range(128)]

    def sid():
        if "sid" not in session:
            session["sid"] = str(uuid4())
        store.ensure(session["sid"])
        return session["sid"]

    def body():
        value = request.get_json()
        if not isinstance(value, dict):
            raise InputError("יש לשלוח אובייקט JSON.")
        return value

    def attached_input(value):
        if value is None:
            return None
        if not isinstance(value, dict) or not isinstance(value.get("algorithm"), str) or value.get("algorithm") not in {a[0] for a in CATALOG} or not isinstance(value.get("arguments"), dict):
            raise InputError("tool_request חייב לכלול algorithm מוכר ו־arguments כאובייקט JSON.")
        return {"algorithm": value["algorithm"], "arguments": value["arguments"]}

    @app.before_request
    def same_origin():
        if request.method == "POST" and request.headers.get("Origin"):
            origin = urlsplit(request.headers["Origin"])
            if origin.netloc != request.host or origin.scheme != request.scheme:
                return jsonify(error="בקשה ממקור אחר נדחתה."), 403

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'"
        if request.path not in ("/",) and not request.path.startswith(("/static/", "/lectures/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        database = store.health()
        rag = retriever.status()
        ready = database and rag["status"] == "ready" and bool(settings.api_key) and not settings.demo
        return jsonify(status="ready" if ready else "degraded" if database else "unhealthy",
                       server="ok", database="ok" if database else "unavailable", rag=rag,
                       llm="configured" if settings.api_key and not settings.demo else "not_configured",
                       demo=settings.demo), 200 if database else 503

    @app.get("/catalog")
    def catalog():
        manifest = settings.data_dir / "processed/manifest.json"
        lectures = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else []
        return jsonify(algorithms=public_catalog(), lectures=lectures)

    @app.get("/history")
    def history():
        return jsonify(messages=store.history(sid()))

    @app.post("/sessions/new")
    def new_session():
        session["sid"] = str(uuid4())
        store.ensure(session["sid"])
        return jsonify(ok=True)

    @app.post("/chat")
    def chat():
        data = body()
        message = data.get("message")
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 12000:
            raise InputError("יש להזין הודעה באורך 1–12,000 תווים.")
        attached = attached_input(data.get("tool_request"))
        session_id = sid()
        lock = locks[hash(session_id) % len(locks)]
        if not lock.acquire(blocking=False):
            return jsonify(error="בקשה קודמת עדיין מתבצעת. נסו שוב לאחר סיומה."), 409
        try:
            history = store.history(session_id, 20)
            rid = str(uuid4())
            store.add(session_id, "user", message.strip(), {"tool_request": attached, "request_id": rid})
            response = tutor.process(message.strip(), history, attached, session_id, rid)
            store.add(session_id, "assistant", response["answer"], response)
            return jsonify(response)
        finally:
            lock.release()

    @app.post("/tools/run")
    def calculator():
        attached = attached_input(body())
        session_id, rid = sid(), str(uuid4())
        result = tutor.run_tool(session_id, rid, attached["algorithm"], attached["arguments"])
        return jsonify(**result, request_id=rid, execution="python_calculator"), 200 if result["ok"] else 422

    @app.get("/lectures/<int:number>")
    def lecture(number):
        if not 1 <= number <= 11:
            return jsonify(error="ההרצאה אינה קיימת."), 404
        lecture_path = settings.data_dir / "lectures" / f"lecture-{number:02}.pdf"
        if not lecture_path.is_file():
            return jsonify(error="Lecture PDF is not included in the public repository."), 404
        return send_file(lecture_path, mimetype="application/pdf")

    @app.errorhandler(InputError)
    def input_error(exc):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return jsonify(error={400: "JSON אינו תקין.", 413: "הבקשה גדולה מדי.", 415: "נדרש Content-Type: application/json."}.get(exc.code, exc.description)), exc.code

    @app.errorhandler(Exception)
    def server_error(exc):
        logging.exception("Request failed")
        return jsonify(error="השרת לא הצליח להשלים את הבקשה. בדקו את חיבור מסד הנתונים ולוגי השרת."), 503

    register_chat_history(app, store)
    return app

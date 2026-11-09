"""Browser-owned conversation history for the existing AlgoTutor application.

No existing table is changed. A new access table links conversations to the
signed browser cookie; only the current legacy conversation can be adopted.
"""
from datetime import timedelta, timezone
import threading
from uuid import uuid4

from flask import g, jsonify, request, session
from sqlalchemy import Column, DateTime, ForeignKey, String, delete, func, select

from .storage import Base, Conversation, Message, ToolCall, now


class ConversationAccess(Base):
    __tablename__ = "conversation_access"
    conversation_id = Column(String(36), ForeignKey("conversations.id"), primary_key=True)
    browser_id = Column(String(36), nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


def register_chat_history(app, store):
    """Call once, inside create_app(), immediately before 'return app'."""
    ConversationAccess.__table__.create(store.engine, checkfirst=True)
    app.permanent_session_lifetime = timedelta(days=365)
    app.config["SESSION_REFRESH_EACH_REQUEST"] = False
    # The existing Docker deployment uses one worker with four threads.
    # Serialize requests for a browser so deletion cannot race a running answer.
    locks = [threading.Lock() for _ in range(256)]

    def create_conversation(db, browser_id):
        conversation_id = str(uuid4())
        db.add(Conversation(id=conversation_id))
        db.flush()
        db.add(ConversationAccess(conversation_id=conversation_id, browser_id=browser_id))
        return conversation_id

    def ensure_current():
        browser_id = session["history_browser_id"]
        conversation_id = session.get("sid")
        with store.sessions.begin() as db:
            conversation = db.get(Conversation, conversation_id) if conversation_id else None
            access = db.get(ConversationAccess, conversation_id) if conversation else None
            if conversation and access is None:
                # This id came from Flask's signed cookie, never from a request parameter.
                db.add(ConversationAccess(conversation_id=conversation_id, browser_id=browser_id))
            elif not conversation or access.browser_id != browser_id or access.deleted_at:
                conversation_id = create_conversation(db, browser_id)
        if session.get("sid") != conversation_id:
            session["sid"] = conversation_id
        return conversation_id

    def owned(db, conversation_id):
        access = db.get(ConversationAccess, conversation_id)
        return access if access and access.browser_id == session["history_browser_id"] and not access.deleted_at else None

    def missing():
        return jsonify(error="השיחה לא נמצאה או שאינה שייכת לדפדפן הזה."), 404

    def iso(value):
        if value.tzinfo is None:  # SQLite demo stores naive UTC timestamps.
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    @app.before_request
    def history_identity():
        relevant = request.path in {"/", "/history", "/chat", "/tools/run", "/sessions/new"}
        if not relevant and not request.path.startswith("/conversations"):
            return
        if "history_browser_id" not in session:
            session["history_browser_id"] = str(uuid4())
        if not session.permanent:
            session.permanent = True
        lock = locks[hash(session["history_browser_id"]) % len(locks)]
        if not lock.acquire(blocking=False):
            return jsonify(error="בקשה קודמת עדיין מתבצעת. נסו שוב לאחר סיומה."), 409
        g.history_lock = lock
        ensure_current()

    @app.after_request
    def remember_legacy_new_chat(response):
        # Keep compatibility with the original /sessions/new endpoint.
        if request.path == "/sessions/new" and response.status_code < 400:
            ensure_current()
        return response

    @app.teardown_request
    def release_history_lock(_error):
        lock = g.pop("history_lock", None)
        if lock is not None:
            lock.release()

    @app.get("/conversations")
    def list_conversations():
        title = (select(Message.content).where(Message.session_id == Conversation.id, Message.role == "user")
                 .order_by(Message.created_at, Message.id).limit(1).scalar_subquery())
        last_message = select(func.max(Message.created_at)).where(Message.session_id == Conversation.id).scalar_subquery()
        count = select(func.count(Message.id)).where(Message.session_id == Conversation.id).scalar_subquery()
        updated = func.coalesce(last_message, Conversation.created_at)
        query = (select(Conversation.id, Conversation.created_at, title.label("title"),
                        updated.label("updated_at"), count.label("message_count"))
                 .join(ConversationAccess, ConversationAccess.conversation_id == Conversation.id)
                 .where(ConversationAccess.browser_id == session["history_browser_id"],
                        ConversationAccess.deleted_at.is_(None))
                 .order_by(updated.desc(), Conversation.id))
        with store.sessions() as db:
            conversations = [{"id": row.id, "title": " ".join((row.title or "שיחה חדשה").split())[:80],
                              "created_at": iso(row.created_at), "updated_at": iso(row.updated_at),
                              "message_count": row.message_count} for row in db.execute(query)]
        return jsonify(active_id=session["sid"], conversations=conversations)

    @app.post("/conversations/new")
    def history_new_conversation():
        with store.sessions.begin() as db:
            conversation_id = create_conversation(db, session["history_browser_id"])
        session["sid"] = conversation_id
        return jsonify(active_id=conversation_id, messages=[])

    @app.post("/conversations/<uuid:conversation_id>/open")
    def open_conversation(conversation_id):
        conversation_id = str(conversation_id)
        with store.sessions() as db:
            if not owned(db, conversation_id):
                return missing()
        messages = store.history(conversation_id, limit=None)
        session["sid"] = conversation_id
        return jsonify(active_id=conversation_id, messages=messages)

    @app.post("/conversations/<uuid:conversation_id>/delete")
    def delete_conversation(conversation_id):
        conversation_id = str(conversation_id)
        active_id = session["sid"]
        with store.sessions.begin() as db:
            access = owned(db, conversation_id)
            if not access:
                return missing()
            db.execute(delete(ToolCall).where(ToolCall.session_id == conversation_id))
            db.execute(delete(Message).where(Message.session_id == conversation_id))
            # Retain only an id/ownership tombstone: stale cookies cannot recreate it.
            access.deleted_at = now()
            if active_id == conversation_id:
                active_id = create_conversation(db, session["history_browser_id"])
        session["sid"] = active_id
        return jsonify(ok=True, active_id=active_id)

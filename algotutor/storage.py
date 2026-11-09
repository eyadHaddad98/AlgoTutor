"""PostgreSQL persistence; SQLite is allowed ONLY for the labelled local demo/tests."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, Column, String, Text, JSON, DateTime, ForeignKey, select, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(36), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class Message(Base):
    __tablename__ = "messages"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), ForeignKey("conversations.id"), index=True, nullable=False)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class ToolCall(Base):
    __tablename__ = "tool_calls"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), ForeignKey("conversations.id"), index=True, nullable=False)
    request_id = Column(String(36), index=True, nullable=False)
    name = Column(String(64), nullable=False)
    input = Column(JSON, nullable=False)
    output = Column(JSON, nullable=False)
    status = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class Store:
    def __init__(self, url, allow_sqlite=False):
        if not url:
            raise ValueError("DATABASE_URL חסר. הפעילו scripts/setup.py ופעלו לפי README.")
        if not url.startswith("postgresql") and not (allow_sqlite and url.startswith("sqlite")):
            raise ValueError("Production mode requires PostgreSQL.")
        kwargs = {"pool_pre_ping": True}
        if url.startswith("postgresql"):
            kwargs["connect_args"] = {"connect_timeout": 5}
        self.engine = create_engine(url, **kwargs)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def init(self):
        Base.metadata.create_all(self.engine)

    def health(self):
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def ensure(self, sid):
        with self.sessions.begin() as db:
            if db.get(Conversation, sid) is None:
                db.add(Conversation(id=sid))

    def add(self, sid, role, content, payload=None):
        with self.sessions.begin() as db:
            message = Message(session_id=sid, role=role, content=content, payload=payload or {})
            db.add(message)
            db.flush()
            return message.id

    def history(self, sid, limit=100):
        with self.sessions() as db:
            rows = db.scalars(select(Message).where(Message.session_id == sid)
                              .order_by(Message.created_at.desc(), Message.id.desc()).limit(limit)).all()
            return [{"id": m.id, "role": m.role, "content": m.content, "payload": m.payload,
                     "created_at": m.created_at.isoformat()} for m in reversed(rows)]

    def log_tool(self, sid, rid, name, args, output, success):
        with self.sessions.begin() as db:
            db.add(ToolCall(session_id=sid, request_id=rid, name=name, input=args,
                            output=output, status="ok" if success else "error"))


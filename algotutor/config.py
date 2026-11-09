from dataclasses import dataclass, field
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Settings:
    demo: bool = field(default_factory=lambda: os.getenv("ALGO_DEMO", "0") == "1")
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"))
    chroma_host: str = field(default_factory=lambda: os.getenv("CHROMA_HOST", "localhost"))
    chroma_port: int = field(default_factory=lambda: int(os.getenv("CHROMA_PORT", "8000")))
    collection: str = field(default_factory=lambda: os.getenv("CHROMA_COLLECTION", "algotutor_e5_v1"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small"))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", str(ROOT / "data"))))
    secure_cookie: bool = field(default_factory=lambda: os.getenv("COOKIE_SECURE", "0") == "1")
    top_k: int = 6


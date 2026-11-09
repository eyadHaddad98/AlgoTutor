"""Create .env with random local secrets. Does not overwrite an existing .env."""

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / ".env"

if target.exists():
    print(".env already exists; left unchanged.")
else:
    password = secrets.token_hex(24)
    secret_key = secrets.token_hex(32)

    text = f"""ANTHROPIC_API_KEY=
SECRET_KEY={secret_key}
POSTGRES_PASSWORD={password}
DATABASE_URL=postgresql+psycopg://algotutor:{password}@localhost:5433/algotutor
ALGO_DEMO=0
CHROMA_HOST=localhost
CHROMA_PORT=8000
"""

    with target.open("x", encoding="utf-8") as output:
        output.write(text)

    print("Created .env. Add your ANTHROPIC_API_KEY there, then follow README.md.")
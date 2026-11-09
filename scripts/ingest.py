import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()
from algotutor.config import Settings
from algotutor.retrieval import Retriever

if __name__ == "__main__":
    print(Retriever(Settings()).ingest())

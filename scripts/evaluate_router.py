"""Router evaluation. --live uses the configured paid Anthropic API."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()
from algotutor.agent import Router
from algotutor.config import Settings

CASES = [("שלום", "direct"), ("איך משתמשים במערכת?", "direct"), ("Hello!", "direct"),
         ("למה דייקסטרה דורש משקלים אי שליליים?", "rag"), ("מה ההבדל בין BFS ל־DFS?", "rag"),
         ("הסבר את הוכחת הנכונות של קרוסקל", "rag"), ("מהו חתך מינימלי?", "rag"),
         ("What is the complexity of Floyd Warshall?", "rag"),
         ("הרץ דייקסטרה על הגרף שלי", "tools"), ("חשב זרימה באדמונדס קארפ", "tools"),
         ("Run BFS from A", "tools"), ("חשב עץ פורש באמצעות פרים", "tools")]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Call the paid Anthropic API for the classifier.")
    args = parser.parse_args()
    model = None
    if args.live:
        from langchain_anthropic import ChatAnthropic
        settings = Settings()
        if not settings.api_key:
            raise SystemExit("ANTHROPIC_API_KEY is required for --live.")
        model = ChatAnthropic(model=settings.model, api_key=settings.api_key, timeout=40, max_retries=2)
    router, rows = Router(model), []
    for query, expected in CASES:
        decision = router.decide(query, [])
        rows.append({"query": query, "expected": expected, "actual": decision["route"],
                     "correct": decision["route"] == expected, "method": decision["method"]})
    print(json.dumps({"mode": "live_requested" if args.live else "rules", "accuracy": sum(r["correct"] for r in rows) / len(rows),
                      "cases": rows, "scope": "12 labelled examples, not a representative benchmark."}, ensure_ascii=False, indent=2))

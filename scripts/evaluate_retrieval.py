"""Small, transparent lecture recall@6 evaluation; requires an indexed Chroma."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()
from algotutor.config import Settings
from algotutor.retrieval import Retriever

CASES = [
    (1, "מהו גרף וכיצד מייצגים רשימת שכנויות?"),
    (2, "איך אלגוריתם BFS מחשב מרחקים בגרף לא ממושקל?"),
    (3, "למה אלגוריתם דייקסטרה דורש משקלים חיוביים?"),
    (4, "איך בלמן פורד מזהה מעגל שלילי?"),
    (5, "איך אלגוריתם פלויד וורשל מחשב מרחקים בין כל זוג צמתים?"),
    (6, "איך אלגוריתם פרים בונה עץ פורש מינימלי?"),
    (7, "מה תפקיד Union Find באלגוריתם קרוסקל?"),
    (8, "מהם זמני הגילוי והסיום ב DFS?"),
    (9, "מהם צמתי הפרדה ורכיבים דו קשירים?"),
    (10, "מהו מסלול משפר ברשת זרימה?"),
    (11, "מהי הסיבוכיות של אדמונדס קארפ?"),
]


def evaluate(retriever):
    rows = []
    for expected, query in CASES:
        sources = retriever.search(query)
        rows.append({"query": query, "expected_lecture": expected,
                     "retrieved_lectures": [s["lecture"] for s in sources],
                     "hit_at_6": any(s["lecture"] == expected for s in sources),
                     "top_score": sources[0]["score"] if sources else None})
    return {"cases": rows, "lecture_recall_at_6": sum(r["hit_at_6"] for r in rows) / len(rows),
            "scope": "11 explicit queries; lecture recall only, not answer accuracy or an unbiased benchmark."}


if __name__ == "__main__":
    settings = Settings()
    if settings.demo:
        raise SystemExit("Use full semantic mode for this evaluation (ALGO_DEMO=0).")
    print(json.dumps(evaluate(Retriever(settings)), ensure_ascii=False, indent=2))

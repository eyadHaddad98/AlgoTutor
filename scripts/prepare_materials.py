"""Extract each physical PDF quadrant in Hebrew reading order using Poppler.

Run: python scripts/prepare_materials.py --source data/lectures
Uses the actual printed slide footer, not an inferred slide number.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOPICS = {1: "מושג הגרף, ייצוג גרפים ומסלולים", 2: "BFS וחישוב מרחקים בגרף לא ממושקל",
          3: "דייקסטרה Dijkstra", 4: "בלמן–פורד Bellman-Ford", 5: "פלויד–וורשל Floyd-Warshall",
          6: "עץ פורש מינימלי ופרים Prim", 7: "קרוסקל Kruskal ו־Union-Find",
          8: "חיפוש לעומק DFS", 9: "צמתי הפרדה ורכיבים דו־קשירים",
          10: "רשתות זרימה ופורד–פולקרסון Ford-Fulkerson", 11: "זרימה מקסימלית ואדמונדס–קארפ Edmonds-Karp"}
SYMBOLS = dict(zip("", "=(),-+∞∈∉→≤≥≠∅∪∩⊆Σδαπ"))


def normalize(text):
    text = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text).replace("ð", "נ")
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.translate(str.maketrans(SYMBOLS)).splitlines()).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "data/lectures")
    args = parser.parse_args()
    records, manifest = [], []
    for lecture in range(1, 12):
        path = args.source / f"lecture-{lecture:02}.pdf"
        info = subprocess.check_output(["pdfinfo", str(path)], text=True)
        pages = int(re.search(r"Pages:\s+(\d+)", info)[1])
        count = 0
        for page in range(1, pages + 1):
            for position, x, y in [("top-right", 306, 0), ("top-left", 0, 0), ("bottom-right", 306, 396), ("bottom-left", 0, 396)]:
                text = normalize(subprocess.check_output(["pdftotext", "-f", str(page), "-l", str(page), "-r", "72",
                    "-x", str(x), "-y", str(y), "-W", "306", "-H", "396", "-layout", str(path), "-"], text=True))
                lines = [line for line in text.splitlines() if line.strip()]
                if not lines:
                    continue
                footer = re.fullmatch(r"\d{1,4}", lines[-1])
                slide = int(lines.pop()) if footer else None
                lines = [line for line in lines if not ("פרופסור עמוס ישראלי" in line or "כל הזכויות שמורות" in line)]
                body = "\n".join(lines).strip()
                if len(body) < 15:
                    continue
                count += 1
                records.append({"id": f"lecture-{lecture:02}-page-{page}-{position}", "lecture": lecture,
                    "page": page, "slide": slide, "position": position, "file": path.name,
                    "topic": TOPICS[lecture], "title": lines[0][:120], "text": body})
        manifest.append({"lecture": lecture, "topic": TOPICS[lecture], "file": path.name,
                         "pdf_pages": pages, "extracted_slides": count,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    output = ROOT / "data/processed"
    output.mkdir(parents=True, exist_ok=True)
    (output / "slides.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"lectures": len(manifest), "slides": len(records), "missing_slide_number": sum(r["slide"] is None for r in records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

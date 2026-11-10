# AlgoTutor

עוזר לימודי לקורס אלגוריתמים ב׳: שאלות על **כל 11 ההרצאות**, הפניות למקורות ו־**12 כלי חישוב** עם פירוט צעדים. הממשק בעברית ובנוי ב־HTML, CSS ו־JavaScript רגיל; השרת ב־Flask.

**English instructions:** [README.md](README.md). מדריך קצר למתחילים: [START_HERE.md](START_HERE.md).

## מה כלול

- תמיכה ב־11 הרצאות (מצגות המקור והתוכן המחולץ אינם כלולים בגרסת GitHub הציבורית).
- RAG עם `intfloat/multilingual-e5-small` שתומך בעברית, ו־Chroma כשירות נפרד.
- נתב שרץ בכל בקשת צ׳אט ובוחר `rag`,‏ `tools` או `direct`. ניתוב מודל עם חלופת כללים מתועדת.
- Anthropic tool calling אמיתי: הגדרות `name / description / input_schema`, ביצוע Python והחזרת `tool_result`.
- יצירת תשובה באמצעות LangChain LCEL, זיכרון שיחה, ניסיונות חוזרים ותשובת גיבוי מזוהה.
- PostgreSQL לשיחות, תשובות, החלטות הנתב וקלט/פלט של כל קריאת כלי.
- מעבדה עם קלט גרף, תרשים SVG, מעבר בין צעדים, טבלאות תוצאה והורדת JSON.

## הפעלה מלאה באמצעות Docker — המסלול להגשת הפרויקט

דרושים Docker Desktop פעיל עם Linux containers ו־Docker Compose, Python 3.12 להפעלת סקריפט ההכנה, אינטרנט בהפעלה הראשונה ומפתח Anthropic API פעיל. מפתח API נפרד ממינוי לממשק צ׳אט.

1. חלצו את התיקייה. פתחו Terminal **בתוך `AlgoTutor`**, ליד `compose.yaml`.
2. צרו הגדרות מקומיות:

   ```powershell
   python scripts/setup.py
   ```

   אם ב־Windows הפקודה `python` אינה מזוהה, השתמשו ב־`py -3.12` במקום `python`.

3. פתחו את `.env` בעורך והדביקו את המפתח **רק** אחרי `ANTHROPIC_API_KEY=`. הסקריפט כבר יצר סיסמת DB ו־SECRET_KEY אקראיים. הוא לא דורס `.env` קיים.
4. בנו והפעילו את שלושת השירותים:

   ```powershell
   docker compose up --build -d
   docker compose ps
   ```

5. אם עדיין לא הכנתם חומרי הרצאות מורשים, הוסיפו אותם והריצו `python scripts/prepare_materials.py`. לאחר מכן אנדקסו את ההרצאות:

   ```powershell
   docker compose exec app python scripts/ingest.py
   ```

   בפעם הראשונה המודל יורד מ־Hugging Face; ההורדה והאינדוקס עשויים לקחת כמה דקות. המודל נשמר ב־volume. בגרסת GitHub אין מצגות או תוכן מחולץ; יש להכינם מקומית קודם. אינדוקס חוזר עושה upsert ואינו יוצר כפילויות.

6. פתחו **http://localhost:5000**. לבדיקה טכנית פתחו http://localhost:5000/health. במצב מלא `status` יהיה `ready`, ‏`rag.status` יהיה `ready` ו־`llm` יהיה `configured`. זה מאשר קיום הגדרות — רק שליחת שאלה בודקת שהמפתח פעיל ושיש מכסה.

**עצירה:** `docker compose down`. המידע והמודל נשמרים ב־volumes. אין צורך למחוק volumes לצורך הפעלה מחדש.

```powershell
docker compose logs --tail 80 app
docker compose logs --tail 80 chroma
```

## עבודה ב־PyCharm עם שירותי DB ב־Docker

פתחו את תיקיית הפרויקט. הגדירו interpreter של Python 3.12 מתוך `.venv`. הריצו `scripts/setup.py` והגדירו את המפתח. ב־Terminal:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python -m pip install -r requirements.txt
docker compose up -d db chroma
.venv\Scripts\python scripts/ingest.py
.venv\Scripts\python run.py
```

ה־`.env` שנוצר כבר מכוון ל־PostgreSQL ב־`localhost:5433` ול־Chroma ב־`localhost:8000`. ב־Docker הכתובות מתחלפות אוטומטית בשמות השירותים. אין להפעיל במקביל גם את שירות `app` וגם `run.py` על פורט 5000.

## כלי החישוב

| הרצאה | כלי | הפלט העיקרי |
|---|---|---|
| 1 | `graph_scan` | צמתים, קשתות ורשימות שכנות |
| 2 | `bfs` | סדר ביקור, מרחקים במספר קשתות, מסלולים ועץ |
| 3 | `dijkstra` | מרחקים, מסלולים ושלבי קביעת מרחק |
| 4 | `bellman_ford` | מרחקים, הרפיות וצמתים המושפעים ממעגל שלילי |
| 5 | `floyd_warshall` | מטריצת מרחקים ומסלולים לכל זוג |
| 6 | `prim` | עץ פורש מינימלי ומשקלו |
| 7 | `kruskal` | עץ פורש, מיון קשתות ובדיקת מעגלים ב־Union–Find |
| 7 | `union_find` | נציגים וקבוצות לאחר פעולות union/find |
| 8 | `dfs` | יער חיפוש, הורים, זמני גילוי וסיום |
| 9 | `biconnected` | צמתי הפרדה, ערכי low ורכיבים דו־קשירים |
| 10 | `ford_fulkerson` | מסלולי הגדלה, זרימה מקסימלית וחתך מינימלי |
| 11 | `edmonds_karp` | זרימה מקסימלית עם מסלולי הגדלה באמצעות BFS |

הכלים הם מימושים לימודיים עצמאיים לנושאים במצגות, ולא העתקה שורה־לשורה של פסאודו־קוד מסוים. הם משתמשים בסדר הקלט לשבירת שוויון; BFS/DFS וסדר בחירת קשתות עשויים להיות שונים מדוגמה בהרצאה עם סדר שכנים אחר, גם כששתי התוצאות תקינות.

### הקלט והמגבלות

- גרף: 1–16 שמות צמתים כמחרוזות ועד 60 קשתות. ללא קשתות מקבילות. בגרף לא מכוון מזינים כל קשת פעם אחת.
- בשדות הפשוטים: צמתים מופרדים בפסיקים וקשתות בשורות `A B 4`. לשמות עם רווחים השתמשו ב־JSON.
- מקור/יעד צריכים להופיע ברשימת הצמתים. משקל ברירת מחדל בקוד הוא 1; סכמות המודל מבקשות משקל מפורש.
- דייקסטרה דוחה משקלים שליליים. BFS מתעלם ממשקלים. פרים וקרוסקל דורשים גרף לא מכוון וקשיר.
- Bellman–Ford מסמן רק מעגלים שליליים הנגישים מהמקור ואת הצמתים שבהמשך להם. Floyd–Warshall מסמן כל זוג שמסלולו יכול לעבור במעגל שלילי.
- `null` במרחקים = לא נגיש; `"-infinity"` = מרחק שאינו חסום מלמטה. אין מסלול מינימלי במצב האחרון.
- זרימה: גרף מכוון ללא לולאות עצמיות, מקור שונה מיעד, קיבולות **שלמות 0–50** בשדה `weight`. נתמכות קשתות נגדיות. התוצאה מלאה גם אם התיעוד נחתך אחרי 250 הגדלות.
- Union–Find: עד 30 איברים ו־100 פעולות. הרכיבים הדו־קשירים מיוצגים בקשתות; צמתים מבודדים מופיעים בנפרד.
- הקלט בגרסה זו טקסט/JSON. אין זיהוי אוטומטי של גרף מתמונה.

דוגמה:

```json
{"algorithm":"dijkstra","arguments":{"graph":{"vertices":["A","B","C"],"directed":true,"edges":[{"from":"A","to":"B","weight":4},{"from":"A","to":"C","weight":2},{"from":"C","to":"B","weight":1}]},"source":"A"}}
```

תוצאת מרחקים: A=0, C=2, B=3. המסלול ל־B: A→C→B.

## RAG ומקורות

`scripts/prepare_materials.py` חותך כל עמוד לארבעה אזורים בסדר הקריאה העברי: ימין עליון, שמאל עליון, ימין תחתון, שמאל תחתון. הוא מסיר תווי כיווניות, מתקן את שיבוש `ð` ל־נ ומנרמל חלק מסמלי המתמטיקה. אין איחוד של שקופיות משתי עמודות.

`data/processed/slides.jsonl` מכיל טקסט, הרצאה, מספר עמוד PDF, מספר שקופית מודפס ומיקום בעמוד. `manifest.json` כולל SHA-256 של כל PDF. מספר השקופית 268 מופיע בסוף הרצאה 6 ובתחילת 7; המזהה כולל גם הרצאה ועמוד כדי שלא יתנגש.

האינדוקס מחלק לפי tokenizer של E5, עם מקום שמור לכותרת ולקידומת `passage:` ומקטעים חופפים. השאלה מקבלת `query:`. הווקטורים מנורמלים ונשמרים ב־Chroma במרחק cosine. התשובה מחזירה עד 6 שקופיות שונות עם ציון `1 - distance`. **זהו ציון התאמה בחיפוש, לא הסתברות שההסבר נכון.**

הטקסט מכסה את ההרצאות, אך איורי גרפים ונוסחאות מסוימות אינם נחלצים במלואם. קישור ה־PDF מאפשר לבדוק את המקור; הפרומפט מחייב לציין חוסר מידע ולא להמציא קשתות מאיור. אין OCR של תמונות. אין להניח שכל קטע שחולץ נקי משגיאות טיפוגרפיות במקור.

להפקת הטקסט מחדש, התקינו Poppler או הריצו בתוך השירות:

```powershell
docker compose exec app python scripts/prepare_materials.py
docker compose exec app python scripts/ingest.py
```

אם משנים את מודל ה־embedding, יש לבחור גם `CHROMA_COLLECTION` חדש ולאנדקס מחדש. אל תשוו וקטורים משני מודלים שונים באותו אוסף.

## תכנון, API ומסד נתונים

ראו [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) לתרשים והחלטות תכנון ו־[docs/API.md](docs/API.md) לתיעוד הבקשות והתשובות. סרטון ההדגמה המקורי אינו מצורף לגרסה הציבורית.

לכל דפדפן מזהה שיחה בעוגייה חתומה, HttpOnly ו־SameSite=Lax. `GET /history` מחזיר רק את השיחה בעוגייה, עד 100 הודעות אחרונות. 12 הודעות אחרונות נכנסות לפרומפט, עם גבול אורך. שיחה חדשה יוצרת מזהה חדש; הישנה נשמרת ב־DB אך אין ממשק חזרה אליה בגרסה זו. אין מערכת חשבונות או פריסה ציבורית מוכנה.

הדפדפן פונה ל־Flask בלבד. `/chat` תמיד עובר בנתב. `/tools/run` הוא מחשבון מפורש נפרד, ללא יצירת תשובת LLM, וגם הוא נרשם במסד הנתונים. במצב מלא פרטי החיבור והמפתח נקראים ממשתני סביבה; `.env` אינו נכלל ב־Git או ב־Docker image.

Gunicorn מוגדר עם worker יחיד ו־4 threads. נעילות קצרות לפי שיחה מונעות שתי בקשות צ׳אט מקבילות לאותה שיחה. מעבר למספר workers מחייב מנגנון נעילה משותף. המסד מוכן להיסטוריה מתמשכת; אין לשנות את הגדרת ה־workers בלי לטפל בכך.

## בדיקות והערכה

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

הבדיקות כוללות מימושי ייחוס עצמאיים ב־NetworkX, גרפים אקראיים עם seed קבוע, קלטים לא תקינים, מסלולים, שימור זרימה, חתך מינימלי, בדיקות API וזיכרון, ובדיקות LCEL עם מודל מדומה. תחליפי המודל וה־SQLite בבדיקות אינם מוצגים כאילו נבדק Claude או PostgreSQL חי.

התוצאות המדויקות והמגבלות של בדיקות סביבת הפיתוח מתועדות ב־[docs/VALIDATION.md](docs/VALIDATION.md). להערכת retrieval נוספת לאחר האינדוקס:

```powershell
docker compose exec app python scripts/evaluate_retrieval.py
```

הערכת נתב ללא עלות API: `python scripts/evaluate_router.py`. הוסיפו `--live` כדי להעריך את הנתב באמצעות המפתח הפעיל (קריאות API בתשלום). בדיקת ממשק אופציונלית עם Node.js: `npm install`, הגדירו `ALGO_PYTHON` לנתיב Python של הסביבה ואז הריצו `npm run test:ui`. זו בדיקת פעולות DOM מול Flask, לא בדיקה חזותית בדפדפן.

## פתרון תקלות

| תקלה | פעולה |
|---|---|
| `docker` אינו מזוהה | התקינו והפעילו Docker Desktop, ואז פתחו Terminal חדש |
| `SECRET_KEY` / סיסמה חסרים | הריצו `python scripts/setup.py`; אם כבר יש `.env`, תקנו אותו לפי `.env.example` |
| מאגר ידע ריק | המתינו לשירות Chroma והריצו `scripts/ingest.py` |
| Chroma אינו זמין | בדקו `docker compose ps` ולוגים; בתוך Docker הכתובת היא `chroma`, מקומית `localhost` |
| הורדת המודל נכשלה | בדקו גישה ל־Hugging Face וחיבור אינטרנט; אפשר להריץ שוב את האינדוקס |
| `401` / `403` מ־Anthropic | בדקו שהמפתח הוא Anthropic API key ושיש הרשאות למודל; אל תדביקו מפתח בצ׳אט |
| `429` או שגיאת שירות | קיימים שני ניסיונות חוזרים; לאחריהם מוצגת תשובת גיבוי שמסומנת בממשק |
| פורט 5000 תפוס | עצרו את ההפעלה המקומית הקודמת או את שירות `app` לפני הפעלה נוספת |

## מבנה התיקיות וייחוס

`algotutor/` — קוד השרת, האלגוריתמים, הנתב, RAG והממשק. `data/` — המצגות והתוכן המעובד שנוצרים מקומית ולא מועלים ל־GitHub. `scripts/` — הכנה, חילוץ, אינדוקס והערכה. `migrations/` — סכמת SQL. `tests/` — בדיקות. `docs/` — ארכיטקטורה, API, תיעוד ובדיקות (רפלקציה אישית הוסרה מהגרסה הציבורית).

מצגות הקורס נכתבו בידי **פרופ׳ עמוס ישראלי**, וסופקו לצורך הפרויקט הלימודי; אינם מופצים עם גרסת GitHub זו. זכויות המצגות נשארות של מחברן. דוגמאות הגרפים בממשק נוצרו לפרויקט ואינן מוצגות כאיורים מקוריים מהמצגות.

מקורות טכניים: [LangChain ChatAnthropic](https://docs.langchain.com/oss/python/integrations/chat/anthropic), [Anthropic tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools), [E5 model card](https://huggingface.co/intfloat/multilingual-e5-small), [Chroma](https://docs.trychroma.com/), [Flask](https://flask.palletsprojects.com/).

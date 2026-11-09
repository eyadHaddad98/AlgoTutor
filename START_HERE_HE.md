# מתחילים כאן — AlgoTutor (גרסה ציבורית)

הקוד נמצא כאן, אבל מצגות הקורס והטקסט שחולץ מהן הוסרו מהגרסה הציבורית. אין להעלות ל־GitHub קובצי PDF ללא רשות, קובצי `.env` או מסדי נתונים.

## הפעלת המערכת המלאה

1. התקינו Python 3.12 ו־Docker Desktop והפעילו Docker.
2. הריצו `python scripts/setup.py` ליצירת `.env` וסיסמאות אקראיות.
3. פתחו `.env` והוסיפו את המפתח האישי שלכם אחרי `ANTHROPIC_API_KEY=` (אל תשתפו אותו).
4. אם יש לכם הרשאה להשתמש במצגות, העתיקו אותן **רק במחשב שלכם** אל `data/lectures/` בשם `lecture-01.pdf` עד `lecture-11.pdf`.
5. הריצו `python scripts/prepare_materials.py` כדי ליצור קובצי מקור מקומיים (דרוש Poppler: `pdfinfo` ו־`pdftotext`).
6. הריצו `docker compose up --build -d` ואחר כך `docker compose exec app python scripts/ingest.py`.
7. פתחו `http://localhost:5000`.

ללא קובצי הרצאות, יישום העזר מציג כלים לחישוב אלגוריתמים, אך לא יספק חיפוש RAG מבוסס מצגות עד להכנת החומר.

לפרטים נוספים: [README.md](README.md), [README_EN.md](README_EN.md).

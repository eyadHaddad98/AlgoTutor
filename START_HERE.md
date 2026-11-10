# Getting Started — AlgoTutor (Public Version)

This repository contains the project's source code. Course lecture PDFs and their extracted text are not included in the public version. Do not upload lecture materials without permission, `.env` files, or local databases to GitHub.

## Running the Full Application

1. Install **Python 3.12** and **Docker Desktop**, then start Docker.
2. Run `python scripts/setup.py` to create your local `.env` file and generate random passwords.
3. Open `.env` and enter your own API key after `ANTHROPIC_API_KEY=`. **Never share or commit your API key.**
4. If you have permission to use the course lectures, place the PDF files **on your local computer only** in `data/lectures/`, named `lecture-01.pdf` through `lecture-11.pdf`.
5. Run `python scripts/prepare_materials.py` to prepare the local course content. This requires **Poppler** (`pdfinfo` and `pdftotext`).
6. Start the services with `docker compose up --build -d`, then run `docker compose exec app python scripts/ingest.py` to ingest the lecture materials.
7. Open `http://localhost:5000` in your browser.

Without the lecture files, the application can still provide algorithm calculation tools. Lecture-based **Retrieval-Augmented Generation (RAG)** becomes available only after the materials have been prepared and ingested.

For more details, see [README.md](README.md) and [README_EN.md](README_EN.md).

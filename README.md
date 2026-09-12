# Past Paper POC

Independent FastAPI proof of concept for storing and processing past-paper PDFs.

## Run the skeleton

```bash
cp .env.example .env
python -m pip install -r requirements.txt
docker compose up -d
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://localhost:8000/health`. MinIO's console is at
`http://localhost:9001` using `minioadmin` / `minioadmins`.

To trace the text returned by Llama Cloud and the question splitting result,
set `PARSING_TRACE=true` in `.env` and restart Uvicorn. The trace is printed
to the Uvicorn log and includes only bounded text previews.

The API now stores papers, units, and questions in PostgreSQL. PDF upload
metadata is persisted, while the actual MinIO upload and PDF processing are
implemented in later steps.

## Structure

```text
app/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── minio_service.py
├── extractor.py
├── classifier.py
└── routes.py
migrations/
docker-compose.yml
requirements.txt
.env.example
README.md
```

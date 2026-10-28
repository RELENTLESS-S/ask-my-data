# Ask My Data

A locally hosted, Dockerized question-answering API for a book catalogue. Ask My Data combines **FastAPI**, **SQLite**, **ChromaDB**, **Ollama**, and **Nginx** to retrieve relevant book information and generate answers grounded in the retrieved context.

The project also has a separate local **MCP server** for connecting the book tools to Claude Desktop. The MCP server is not part of the Docker Compose HTTP API stack.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API endpoints](#api-endpoints)
- [Testing the API](#testing-the-api)
- [How retrieval-augmented generation works](#how-retrieval-augmented-generation-works)
- [Data and persistence](#data-and-persistence)
- [Backups and recovery](#backups-and-recovery)
- [Useful Docker commands](#useful-docker-commands)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)
- [Local MCP server and Claude Desktop](#local-mcp-server-and-claude-desktop)
- [Known limitations and future improvements](#known-limitations-and-future-improvements)

## Features

- Ask natural-language questions about books in the catalogue.
- Retrieve relevant book documents using vector similarity search.
- Generate answers with a local Ollama chat model.
- Return retrieved source documents with the answer.
- Expose health and catalogue statistics endpoints.
- Run the API, vector database, model service, and reverse proxy using Docker Compose.
- Keep the SQLite database and vector database data persistent across ordinary container restarts.
- Keep ChromaDB and Ollama ports internal to the Docker network; expose the API through Nginx on host port `8080`.
- Run a separate local MCP server for semantic search and predefined book statistics in Claude Desktop.

## Architecture

```text
                         Browser / API client
                                  |
                                  | http://localhost:8080
                                  v
                         +----------------+
                         |      Nginx     |
                         | reverse proxy  |
                         +----------------+
                                  |
                                  v
                         +----------------+
                         |    FastAPI     |
                         | /health        |
                         | /stats         |
                         | /ask           |
                         +----------------+
                           |      |      |
               SQLite file |      |      | HTTP requests
                           v      v      v
                     +---------+ +-----------+
                     | SQLite  | |  Ollama   |
                     | books   | | chat +    |
                     | database| | embeddings|
                     +---------+ +-----------+
                                      |
                                      | query vector
                                      v
                               +-------------+
                               |   ChromaDB  |
                               | vector index|
                               +-------------+
```

### Request flow for `/ask`

1. The client sends a question to Nginx on port `8080`.
2. Nginx forwards the request to FastAPI inside the Docker network.
3. FastAPI asks Ollama to embed the question using `nomic-embed-text`.
4. FastAPI queries the existing ChromaDB collection, `books_semantic`, for similar documents.
5. The retrieved documents are inserted into `prompts/answer.txt` with the user's question.
6. FastAPI sends that prompt to the configured Ollama chat model.
7. The API returns the generated answer and the retrieved sources.

The API uses explicit query embeddings when searching the existing Chroma collection. This avoids attaching a different embedding function to a collection that already contains vectors.

### Services and ports

| Component | Purpose | Access |
|---|---|---|
| Nginx | Public entry point / reverse proxy | Host port `8080` |
| FastAPI | API and RAG orchestration | Internal Docker network |
| ChromaDB | Vector storage and similarity search | Internal Docker network, port `8000` |
| Ollama | Local chat and embedding inference | Internal Docker network, port `11434` |
| SQLite | Relational book catalogue and statistics | File mounted into the API container |

Only Nginx publishes a host port in the current Compose configuration. ChromaDB and Ollama are intended to be accessed by other containers on the `backend` network.

## Technology stack

- **Python 3.11**
- **FastAPI** — HTTP API
- **Uvicorn** — ASGI server
- **SQLite** — structured book data and statistics
- **ChromaDB** — vector database
- **Ollama** — local language model and embedding model runtime
- **Nginx** — reverse proxy
- **Docker Compose** — multi-container orchestration
- **PowerShell** — example commands for the Windows development environment

## Repository layout

The main files and directories are expected to look similar to this:

```text
ask-my-data/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .dockerignore
├── README.md
├── nginx/
│   └── default.conf
├── prompts/
│   └── answer.txt
├── databases/
│   └── books_database.db
├── chroma_db/                  # original local Chroma data (not copied into image)
├── chroma_db_backup/           # backup of original local Chroma data
├── migrate_chroma.py           # migration helper used for Docker Chroma
└── src/
    ├── api/
    │   ├── main.py
    │   ├── rag.py
    │   └── database.py
    ├── mcp_server/
    │   └── server.py
    └── index_books.py           # original local indexing script; use cautiously
```

Some generated, temporary, or data files may not be present in every checkout. The `.dockerignore` file excludes local virtual environments, raw data, SQLite files, and the local Chroma directory from the Docker build context. The SQLite file is mounted into the API container at runtime.

> **Important:** Do not rerun `src/index_books.py` casually. The existing script creates/recreates the local index, and running it may overwrite the local index. Back up the data and review the script before re-indexing.

## Requirements

Install or set up the following before starting:

- Docker Desktop with the Linux container engine enabled.
- Docker Compose (included with current Docker Desktop installations).
- Enough RAM and disk space for the containers and local models.
- The repository and the SQLite database at the expected paths.

This project was developed on Windows with Docker Desktop and PowerShell. Commands below use PowerShell syntax.

## Quick start

### 1. Open the project directory

```powershell
cd "S:\Ask_my _data\ask-my-data"
```

### 2. Check Docker

```powershell
docker --version
docker compose version
docker info
```

If Docker commands cannot connect to the daemon, start Docker Desktop and wait until its engine is ready.

### 3. Confirm the required files exist

```powershell
Test-Path .\Dockerfile
Test-Path .\docker-compose.yml
Test-Path .\requirements.txt
Test-Path .\nginx\default.conf
Test-Path .\prompts\answer.txt
Test-Path .\databases\books_database.db
```

Each command should return `True`. If the database is missing, do not start with an empty database without understanding the impact on the application.

### 4. Start the stack

```powershell
docker compose up -d --build
```

The first build may take time because Python dependencies and container images need to be downloaded.

### 5. Check service status

```powershell
docker compose ps
```

All four services should be running: `app`, `chromadb`, `ollama`, and `nginx`.

### 6. Check the health endpoint

```powershell
Invoke-RestMethod http://localhost:8080/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "Ask My Data API"
}
```

### 7. Open interactive API documentation

Visit:

- Swagger UI: <http://localhost:8080/docs>
- OpenAPI schema: <http://localhost:8080/openapi.json>

### 8. Confirm Ollama models are available

The working Docker setup uses:

- Chat model: `llama3.2:1b`
- Embedding model: `nomic-embed-text`

Check the Ollama container logs:

```powershell
docker compose logs ollama
```

To list models inside the Ollama container:

```powershell
docker compose exec ollama ollama list
```

If a model is missing, pull it into the Docker Ollama service:

```powershell
docker compose exec ollama ollama pull llama3.2:1b
docker compose exec ollama ollama pull nomic-embed-text
```

Model downloads require an internet connection. These are models in the **Docker Ollama volume**; they are separate from models installed in Windows Ollama.

## Configuration

The Docker Compose `app` service is configured with these environment variables:

| Variable | Docker value | Purpose |
|---|---|---|
| `DB_PATH` | `/app/databases/books_database.db` | SQLite database file path inside the container |
| `CHROMA_HOST` | `chromadb` | ChromaDB service name on the Docker network |
| `CHROMA_PORT` | `8000` | ChromaDB internal port |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL inside Docker |
| `CHAT_MODEL` | `llama3.2:1b` | Model used to generate answers |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Model used to embed questions |

The API code falls back to local defaults if certain environment variables are absent. Inside Docker, use the service hostname `ollama`, not `localhost`, to reach the Ollama container.

The Compose file mounts:

```yaml
volumes:
  - ./databases:/app/databases
```

This makes the host database available at `/app/databases` inside the API container. ChromaDB and Ollama data are stored in named Docker volumes.

If you change a model name or environment variable in `docker-compose.yml`, recreate the affected service:

```powershell
docker compose up -d --force-recreate app
```

If you change Python dependencies or application code copied into the image, rebuild the image:

```powershell
docker compose up -d --build app
```

## API endpoints

Base URL:

```text
http://localhost:8080
```

### `GET /health`

Checks that the API is responding.

```powershell
Invoke-RestMethod http://localhost:8080/health
```

Example response:

```json
{
  "status": "ok",
  "service": "Ask My Data API"
}
```

This is an application health check; it does not necessarily prove that every downstream service can successfully answer a question.

### `GET /stats`

Returns statistics about the book catalogue. Current working database statistics include:

- Total books: `732`
- Books with descriptions: `240`
- Books with subjects: `664`
- Unique authors represented in the books table: `603`

These values describe the database at the time they were checked and may change if the database is updated.

```powershell
Invoke-RestMethod http://localhost:8080/stats
```

The endpoint also returns publication-year statistics. See the live response for its exact JSON shape.

### `POST /ask`

Accepts a natural-language question, retrieves relevant book records, and returns an answer with sources.

Request:

```powershell
$body = @{
    question = "What is The Dragons of Eden about?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri http://localhost:8080/ask `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

Example response shape (the source text and exact answer vary by question):

```json
{
  "answer": "The Dragons of Eden is a non-fiction book by Carl Sagan, which explores the evolution of human intelligence.",
  "sources": [
    {
      "text": "Title: The Dragons of Eden\nAuthor: Carl Sagan\n...",
      "metadata": {
        "title": "The Dragons of Eden",
        "author": "Carl Sagan"
      }
    }
  ]
}
```

The `sources` array contains retrieved documents and their metadata. The metadata fields can vary depending on the indexed record.

The application is intended to answer from retrieved book context and to say when the available information is insufficient. Retrieval quality depends on the content available in the database and vector index.

## Testing the API

Run these checks after startup or a deployment change.

### Health

```powershell
Invoke-RestMethod http://localhost:8080/health
```

### Statistics

```powershell
Invoke-RestMethod http://localhost:8080/stats
```

### Question answering

```powershell
$body = @{
    question = "What is The Dragons of Eden about?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri http://localhost:8080/ask `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### Check HTTP status and errors

For a quick endpoint check:

```powershell
try {
    Invoke-RestMethod http://localhost:8080/health
} catch {
    Write-Host "Request failed:"
    Write-Host $_.Exception.Message
}
```

### Run a service's logs while testing

In a separate PowerShell window:

```powershell
docker compose logs -f app
```

Use `Ctrl+C` to stop following logs; this does not stop the container.

## How retrieval-augmented generation works

This application uses a pattern called **retrieval-augmented generation (RAG)**:

1. **Question embedding:** Ollama converts the user's question into a numeric vector using `nomic-embed-text`.
2. **Vector search:** ChromaDB compares that vector with the stored book vectors and returns the nearest documents.
3. **Context construction:** The retrieved documents are assembled into a context block.
4. **Prompting:** `prompts/answer.txt` provides instructions and receives the context and question.
5. **Answer generation:** Ollama's `llama3.2:1b` model generates a response.
6. **Source return:** The API returns the answer and the retrieved source documents.

The vector collection is named `books_semantic`. The migrated index was checked at **732 records** with **768-dimensional vectors**. If you replace or rebuild the index, ensure the query embedding model and vector dimensions remain compatible with the stored vectors.

RAG is not guaranteed to be correct. A retrieved document may be only loosely related to the question, and a small local chat model can misinterpret context. Always inspect the sources when evaluating an answer.

## Data and persistence

| Data | Location | Persistence mechanism |
|---|---|---|
| SQLite book catalogue | `./databases/books_database.db` on host | Bind mount into the API container |
| ChromaDB vectors and metadata | Named volume `chroma_data` (Compose-managed name may be prefixed by the project name) | Persistent Docker volume |
| Ollama models | Named volume `ollama_data` (Compose-managed name may be prefixed by the project name) | Persistent Docker volume |
| API code and prompt | Repository files copied into the app image | Rebuild image after changes |

An ordinary `docker compose restart` or `docker compose down` keeps named volumes. However, deleting volumes, deleting the database file, or rebuilding/re-indexing incorrectly can cause data loss.

### Commands that need care

- `docker compose down -v` removes Compose-managed named volumes and can delete ChromaDB data and downloaded Ollama models.
- Removing the SQLite database from `databases/` affects the host copy used by the container.
- Running the original indexing script may recreate the local Chroma index. Review it and back up data first.
- `docker compose up -d --build` rebuilds the app image; it does not, by itself, delete named volumes.

## Backups and recovery

A backup is useful only if it can be restored. Keep copies outside the project folder or on another disk when possible. Avoid copying a live database or volume while it is actively being written unless using a safe database/volume backup method.

### 1. Back up SQLite

From the project root in PowerShell:

```powershell
New-Item -ItemType Directory -Force .\backups | Out-Null

Copy-Item `
    .\databases\books_database.db `
    .\backups\books_database_$(Get-Date -Format 'yyyyMMdd_HHmmss').db
```

For a database that may be actively modified, prefer SQLite's backup API or stop writes before copying. The simple file copy is suitable for this project's normal local workflow when the database is not being written.

### 2. Back up the ChromaDB named volume

First, discover the exact volume name created by Compose:

```powershell
docker volume ls
```

The volume will commonly be named something like `ask-my-data_chroma_data`, depending on the Compose project name. Substitute the **exact name shown on your machine** in the command below. Run this from the project root so the backup file lands in `.\backups`:

```powershell
New-Item -ItemType Directory -Force .\backups | Out-Null

docker run --rm `
    -v ask-my-data_chroma_data:/data:ro `
    -v "${PWD}\backups:/backup" `
    alpine `
    sh -c "tar -czf /backup/chroma_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data ."
```

If Docker reports that the volume does not exist, re-check `docker volume ls` and replace `ask-my-data_chroma_data` with the exact Chroma volume name. For a consistent backup, stop the app and ChromaDB first so no requests write to the index:

```powershell
docker compose stop app chromadb
```

Run the archive command, then start the services again:

```powershell
docker compose start chromadb app
```

The Ollama volume can be large because it contains model files. It can be backed up using the same method, replacing the volume name with the exact Ollama volume name and the archive name with `ollama_data_...tar.gz`.

### 3. Back up the original local Chroma index

The repository also has a local `chroma_db_backup` directory that was created before the Docker migration. Keep it until the Docker Chroma volume has been backed up and verified. It is separate from the Docker named volume.

### 4. Restore the SQLite database

1. Stop the API to avoid writes:

   ```powershell
   docker compose stop app
   ```

2. Preserve the current file before restoring:

   ```powershell
   Copy-Item .\databases\books_database.db .\backups\books_database_before_restore.db
   ```

3. Copy the chosen backup to `.\databases\books_database.db`.
4. Start the app and validate `/health` and `/stats`:

   ```powershell
   docker compose start app
   Invoke-RestMethod http://localhost:8080/health
   Invoke-RestMethod http://localhost:8080/stats
   ```

### 5. Restore the ChromaDB volume

Restoring a volume replaces vector-store state. Do this only after identifying the correct volume and keeping a backup of its current contents.

1. Stop the app and ChromaDB:

   ```powershell
   docker compose stop app chromadb
   ```

2. Extract the archive into the correct named volume. Replace the volume and archive names with the actual names on your system:

   ```powershell
   docker run --rm `
       -v ask-my-data_chroma_data:/data `
       -v "${PWD}\backups:/backup" `
       alpine `
       sh -c "tar -xzf /backup/chroma_data_BACKUP_TIMESTAMP.tar.gz -C /data"
   ```

3. Start the services and test `/ask`:

   ```powershell
   docker compose start chromadb app
   docker compose logs --tail 100 chromadb
   docker compose logs --tail 100 app
   ```

Do not restore an archive over a volume containing data you want to preserve. For an important recovery, restore into a fresh volume or keep a separate copy of the current volume first.

## Useful Docker commands

Run these from the repository root.

| Task | Command |
|---|---|
| Start and build | `docker compose up -d --build` |
| Show services | `docker compose ps` |
| Follow all logs | `docker compose logs -f` |
| Follow API logs | `docker compose logs -f app` |
| View recent errors | `docker compose logs --tail 100 app` |
| Restart services | `docker compose restart` |
| Restart one service | `docker compose restart app` |
| Rebuild API image | `docker compose up -d --build app` |
| Stop services but keep data | `docker compose stop` |
| Start stopped services | `docker compose start` |
| Stop and remove containers/network | `docker compose down` |
| Inspect volumes | `docker volume ls` |
| Inspect disk use | `docker system df` |
| Validate Compose config | `docker compose config` |
| Test Nginx config | `docker compose run --rm --no-deps nginx nginx -t` |

**Warning:** `docker compose down -v` removes named volumes. Avoid it unless you intentionally want to delete the persistent ChromaDB and Ollama data.

## Troubleshooting

### 1. `localhost:8080` does not respond

Check that Docker Desktop is running, then:

```powershell
docker compose ps
docker compose logs --tail 100 nginx
docker compose logs --tail 100 app
```

If Nginx is stopped or its configuration is invalid:

```powershell
docker compose run --rm --no-deps nginx nginx -t
docker compose up -d nginx
```

Confirm that port `8080` is not already being used by another application.

### 2. `/health` works but `/ask` returns HTTP 500

The health endpoint may respond even if a dependency needed for RAG is unavailable. Inspect logs:

```powershell
docker compose logs --tail 200 app
docker compose logs --tail 100 chromadb
docker compose logs --tail 100 ollama
```

Check that:
- ChromaDB is running and the `books_semantic` collection exists.
- Ollama is running and both required models are present.
- The API's `CHROMA_HOST`, `CHROMA_PORT`, and `OLLAMA_BASE_URL` use Docker service names and internal ports.
- `prompts/answer.txt` exists in the image.
- The SQLite file is present at `databases/books_database.db`.

### 3. Ollama model not found

List available models:

```powershell
docker compose exec ollama ollama list
```

Pull the required models if needed:

```powershell
docker compose exec ollama ollama pull llama3.2:1b
docker compose exec ollama ollama pull nomic-embed-text
```

The Docker Ollama service has its own model storage, separate from the Windows Ollama installation.

### 4. ChromaDB collection not found

The API expects a collection named `books_semantic`. Check the ChromaDB logs and confirm that the correct persistent volume is mounted. Do not run the local indexing script as a first troubleshooting step; first check the collection and back up existing data.

### 5. Embedding dimension or retrieval errors

The existing index was created with `nomic-embed-text` and checked at 768 dimensions. The query embedding model must be compatible with those stored vectors. If changing embedding models, plan a deliberate re-index and backup; changing only the model name may make the existing index unusable for queries.

### 6. Answers are vague or say there is not enough information

Possible causes:
- The relevant book has no description or subject metadata.
- The top retrieved documents are not relevant to the question.
- The question is too broad.
- The chat model is small and may not synthesize the retrieved context well.

Try a specific question about a known title or author and inspect `sources`. Improving retrieval may require better document text, metadata filtering, a different `top_k`, reranking, or a stronger local model. Do not assume that a fluent answer is necessarily grounded or correct.

### 7. Statistics are incorrect or fail

Check the mounted SQLite database and API logs:

```powershell
Test-Path .\databases\books_database.db
docker compose logs --tail 200 app
```

Confirm that the database schema matches the queries in `src/api/database.py`, especially the `books` and `authors` tables. A stale or different database file can cause misleading counts.

### 8. Container changes do not appear

If application code is copied into the image, rebuild it:

```powershell
docker compose up -d --build app
```

If only environment variables changed:

```powershell
docker compose up -d --force-recreate app
```

If you changed the Nginx config, validate it and recreate or restart Nginx:

```powershell
docker compose run --rm --no-deps nginx nginx -t
docker compose up -d --force-recreate nginx
```

### 9. Docker runs out of memory or is very slow

Local model inference can consume significant RAM and CPU. Close unnecessary applications, check Docker Desktop resource allocation, and use a smaller model if needed. Allow extra time for the first model load and first request.

### 10. `docker compose down` and `up` changed something

`docker compose down` removes containers and the Compose network but ordinarily keeps named volumes. If the data appears missing, inspect volume names and the Compose project name before creating new data or re-indexing. Do not use `down -v` as a routine reset command.

## Security notes

This is a local development project, not a hardened production deployment.

- The current host-published entry point is Nginx on port `8080`.
- ChromaDB and Ollama are internal to the Compose network in the current setup.
- There is no authentication or authorization documented for the API. Do not expose it to an untrusted network as-is.
- Do not commit secrets, `.env` files, private datasets, or database backups to a public repository.
- Review Nginx, CORS, request limits, authentication, logging, and data retention before deployment outside a trusted local environment.
- Keep Docker images and Python dependencies updated, and pin dependency versions for reproducible builds.
- Back up the SQLite database and named volumes before migrations or destructive operations.

## Local MCP server and Claude Desktop

The project has a separate MCP server at `src/mcp_server/server.py` for Claude Desktop. It exposes tools such as semantic book search and book statistics using predefined, safe operations.

This is separate from the Docker HTTP API:
- The Docker Compose stack serves FastAPI through Nginx at `http://localhost:8080`.
- Claude Desktop launches/connects to the local MCP server using its MCP configuration.
- The MCP server may require its own Python environment and dependencies.
- Changing Docker Compose does not automatically change the Claude Desktop MCP configuration.

Keep the MCP server's configured interpreter path, working directory, database path, and Chroma connection settings aligned with the local environment it is intended to use. Avoid changing its configuration while troubleshooting the Docker API unless you intend to work on both components.

## Known limitations and future improvements

- Retrieval quality depends on the completeness and quality of the book descriptions and subjects.
- The API returns retrieved sources, but the model may still produce inaccurate interpretations.
- Current model choices prioritize local resource usage over maximum answer quality.
- Health checks can be extended to verify ChromaDB and Ollama connectivity.
- Dependency versions should be pinned for repeatable builds.
- Automated tests should cover API validation, database statistics, retrieval, source formatting, and dependency failures.
- Production deployments should add authentication, stronger operational monitoring, structured logging, and a tested backup/restore process.

## Current verified baseline

The following were confirmed during local testing:

- The four Docker Compose services (`app`, `chromadb`, `ollama`, `nginx`) were running.
- Nginx exposed the application on host port `8080`.
- `/health` and `/stats` responded successfully.
- `/ask` answered a question about *The Dragons of Eden* and returned sources.
- A normal `docker compose restart` completed, after which health, stats, and question answering worked again.
- The migrated Chroma collection contained 732 records with 768-dimensional vectors.

This baseline is a record of the development environment, not a guarantee that a fresh machine will have the same data or model volumes.

## License

Add your chosen license here before publishing the repository. If this is an academic or portfolio project, also review the source and licensing terms for the dataset and any third-party metadata used.

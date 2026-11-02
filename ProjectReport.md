# ASK MY DATA

A self-hosted question-answering assistant over a messy dataset.

Building a small service that answers plain-English questions about a dataset. We start with a messy CSV file, enrich it from a public API, clean it, store it in a database and make it searchable by meaning. A language model running on our own machine then uses that search to answer questions.

The project also has a separate local **MCP server** for connecting the book tools to Claude Desktop.

## CONTENTS

- GitHub repository containing source codes & enviornment
- Clean csv enriched data
- A Vecor database
- RAG API (with 3 endpoints) 
- MCP server 
- Docker Image

## About data

- A messy CSV with at least a thousand rows and visible problems such as duplicates, gaps and inconsistent formats.
- A free public API that returns JSON and adds something the CSV lacks, such as descriptions or subjects.

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

![alt text](image.png)
### Request flow for `/ask`

1. The client sends a question to Nginx on port `8080`.
2. Nginx forwards the request to FastAPI inside the Docker network.
3. FastAPI asks Ollama to embed the question using `nomic-embed-text`.
4. FastAPI queries the existing ChromaDB collection, `books_semantic`, for similar documents.
5. The retrieved documents are inserted into `prompts/answer.txt` with the user's question.
6. FastAPI sends that prompt to the configured Ollama chat model.
7. The API returns the generated answer and the retrieved sources.

### Services and ports

| Component | Purpose | Access |
|---|---|---|
| Nginx | Public entry point / reverse proxy | Host port `8080` |
| FastAPI | API and RAG orchestration | Internal Docker network |
| ChromaDB | Vector storage and similarity search | Internal Docker network, port `8000` |
| Ollama | Local chat and embedding inference | Internal Docker network, port `11434` |
| SQLite | Relational book catalogue and statistics | File mounted into the API container |

Only Nginx publishes a host port in the current Compose configuration. ChromaDB and Ollama are intended to be accessed by other containers on the `backend` network.

## PROJECT FLOW on what was done

1. Repository and environment.
    - A github repository named “ask-my-data” which contains raw & cleaned data, scripts, source code, venv, README and gitignore. 
    - Ran git commands init, commit, push the pipeline and code to the github repository.
![alt text](image-1.png)

2. Extract and clean.
    - A clean.py file that cleans the messy csv.
    - A enrich.py that calls the api and adds description and subject to the missing csv file.
    - A clean csv with subject and description which later gonna use for semantic search.
![alt text](image-2.png)
![alt text](image-3.png)

3.	Store and query with SQL
    - A sqlite database with two diff tables authors and books. 
    - The database using primary and foreign keys.
![alt text](image-4.png)

4.	 Embeddings and retrieval
    - Ollama running on pc with a chat model gemma4:e2b or llama3.2:1b
    - A python script that runs Nordic-embedding-text to create embeddings for the vector database.
    - A search_books.py file that returns the top-k results back during retrieval.

5.	The RAG API
    - A Fast API application with three endpoints: one that answers a question (POST /ask), one that returns figures from SQL (GET /stats), and one that reports whether the service is up (GET /health).
    - The ask endpoint retrieves the top chunks, places them in a prompt with the question, calls the chat model, and returns the answer.
![alt text](image-5.png)

6.	MCP server
    - A mcp server that runs on own machine with two tools: one for semantic search over the data and one for statistics.
![alt text](image-6.png)
![alt text](image-7.png)

## What I made:
- A GitHub repository that tracks and stores the code files and virtual environments.
- A clean dataset with added description and subjects to enrich what’s missing in the csv file.
- Converting the csv data into a SQLite database. 
- A python script that makes vector embeddings and saves them to a vector database.
- RAG API with 3 endpoints for (Post/ask), (Get/stats), (Get/health) to query rag in backend and returns.
- A MCP server that connects MCP client, exposes tools & resources to connect it to.
- A docker image use to generate and make the whole project deliverable and usable on other devices.

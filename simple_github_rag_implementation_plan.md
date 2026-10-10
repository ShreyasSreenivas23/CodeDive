# Simple GitHub Repository RAG — Implementation Plan

## 1. Project Goal

Build a simple AI-powered GitHub repository question-answering application.

A user provides a public GitHub repository URL. The application:

1. Clones the repository.
2. Reads relevant source-code and documentation files.
3. Splits files into chunks.
4. Generates embeddings.
5. Stores the chunks and embeddings in a vector database.
6. Retrieves relevant chunks when the user asks a question.
7. Sends the retrieved context and question to an LLM.
8. Displays the answer with basic source-file references.

The goal is to build a small, understandable RAG project from scratch — not a large code-intelligence platform.

---

# 2. Final Architecture

```text
                 React Frontend
                       │
                       ▼
                  FastAPI API
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     GitHub Service              RAG Service
          │                         │
          ▼                         ▼
     Clone Repository          Vector Database
          │                         │
          ▼                         ▼
      Read Files               Similarity Search
          │                         │
          ▼                         ▼
       Chunking               Retrieved Chunks
          │                         │
          ▼                         ▼
      Embeddings              Context Builder
          │                         │
          └────────────┬────────────┘
                       ▼
                       LLM
                       │
                       ▼
                    Answer
```

---

# 3. Recommended Tech Stack

## Backend

- Python
- FastAPI
- Uvicorn

## Repository

- Git / GitPython

## RAG

- ChromaDB
- Embedding model/API
- LLM API

## Frontend

- React
- Vite

## Development

- Git
- `.env` for API keys

Keep the stack small. Do not introduce PostgreSQL, Redis, Celery, Kubernetes, or other infrastructure unless there is a concrete reason later.

---

# 4. Project Structure

```text
codedive/
│
├── backend/
│   ├── main.py
│   ├── github.py
│   ├── loader.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── rag.py
│   ├── requirements.txt
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── main.jsx
│   └── package.json
│
├── .env
├── .env.example
├── .gitignore
└── README.md
```

---

# 5. Phase 1 — Backend Setup

## Goal

Create a minimal FastAPI application.

## Tasks

- [ ] Create Python virtual environment
- [ ] Install FastAPI
- [ ] Install Uvicorn
- [ ] Create `main.py`
- [ ] Create `/health` endpoint
- [ ] Create `.env`
- [ ] Create `.env.example`
- [ ] Create `.gitignore`
- [ ] Verify the backend starts

## Endpoint

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

## Definition of Done

The FastAPI server starts successfully and `/health` returns `200 OK`.

---

# 6. Phase 2 — GitHub Repository Cloning

## Goal

Convert a GitHub URL into a local repository.

Input:

```text
https://github.com/user/project
```

Output:

```text
/tmp/codedive/project/
```

## Tasks

- [ ] Accept a GitHub URL
- [ ] Validate the URL
- [ ] Clone the repository
- [ ] Use a shallow clone
- [ ] Return repository information
- [ ] Handle invalid URLs
- [ ] Handle clone failures
- [ ] Clean up temporary repositories when appropriate

Use:

```bash
git clone --depth 1 <url>
```

or GitPython.

## Function

```python
def clone_repository(url):
    ...
```

## Definition of Done

A valid public GitHub URL can be cloned successfully.

---

# 7. Phase 3 — File Extraction

## Goal

Read useful files from the cloned repository.

## Include

Initially support common text/code files:

```text
.py
.js
.ts
.jsx
.java
.cpp
.c
.h
.go
.rs
.rb
.php
.md
.txt
.json
.yaml
.yml
.toml
.sql
```

You can add more later.

## Ignore

```text
.git/
node_modules/
venv/
.venv/
__pycache__/
dist/
build/
coverage/
target/
```

Also ignore binary files such as:

```text
.png
.jpg
.jpeg
.gif
.mp4
.zip
.exe
```

and very large files.

## Output

```python
[
    {
        "path": "src/main.py",
        "content": "..."
    },
    {
        "path": "src/database.py",
        "content": "..."
    }
]
```

## Function

```python
def load_repository(repo_path):
    ...
```

## Definition of Done

The application can turn a repository into a clean list of useful text/code files.

---

# 8. Phase 4 — Chunking

## Goal

Split repository files into pieces that can be embedded and retrieved.

Start with a basic recursive text splitter.

Suggested initial settings:

```text
Chunk size: ~1000 characters
Overlap: ~200 characters
```

Each chunk should preserve its source file.

## Output

```python
{
    "content": "...",
    "file": "src/main.py"
}
```

## Tasks

- [ ] Implement chunking
- [ ] Preserve file path
- [ ] Handle small files
- [ ] Handle empty files
- [ ] Handle large files
- [ ] Test overlap
- [ ] Test that no content is accidentally lost

## Definition of Done

Every repository file can be converted into manageable chunks.

---

# 9. Phase 5 — Embeddings

## Goal

Convert every chunk into a vector.

Pipeline:

```text
Chunk
  ↓
Embedding Model
  ↓
Vector
```

## Tasks

- [ ] Choose an embedding model/API
- [ ] Add API key to `.env`
- [ ] Create `embeddings.py`
- [ ] Implement single-text embedding
- [ ] Implement batch embedding if supported
- [ ] Handle API failures

Example interface:

```python
class EmbeddingService:

    def embed_text(self, text):
        ...

    def embed_documents(self, documents):
        ...
```

## Definition of Done

The application can reliably turn chunks into embeddings.

---

# 10. Phase 6 — ChromaDB

## Goal

Store the chunks and embeddings in a vector database.

Use ChromaDB because it keeps the project simple.

## Store

For each chunk:

```text
embedding
content
file path
```

Example metadata:

```python
{
    "file": "src/auth.py"
}
```

## Tasks

- [ ] Initialize ChromaDB
- [ ] Create a collection
- [ ] Add chunks
- [ ] Add embeddings
- [ ] Add metadata
- [ ] Persist the database
- [ ] Associate indexed data with a repository

## Definition of Done

After indexing, the repository's chunks and embeddings remain available for retrieval.

---

# 11. Phase 7 — Semantic Retrieval

## Goal

Given a question, retrieve the most relevant repository chunks.

Example:

```text
Question:
How does authentication work?
```

Pipeline:

```text
Question
   ↓
Question Embedding
   ↓
ChromaDB Similarity Search
   ↓
Top 5 Chunks
```

Start with:

```text
top_k = 5
```

## Function

```python
def retrieve(question, repository_id, k=5):
    ...
```

## Result

```python
[
    {
        "content": "...",
        "file": "src/auth.py",
        "score": 0.87
    },
    ...
]
```

## Definition of Done

Questions return relevant pieces of repository code.

---

# 12. Phase 8 — RAG Context

## Goal

Prepare retrieved chunks for the LLM.

Format the context clearly:

```text
Repository: user/project

FILE: src/auth.py

<code>

---

FILE: src/middleware.py

<code>
```

## Tasks

- [ ] Combine retrieved chunks
- [ ] Include file names
- [ ] Limit context size
- [ ] Remove obvious duplicates
- [ ] Preserve retrieval order

## Definition of Done

The LLM receives clean repository context.

---

# 13. Phase 9 — LLM Integration

## Goal

Use retrieved repository context to answer questions.

Prompt structure:

```text
You are an assistant analyzing a GitHub repository.

Answer the user's question using the provided repository
context.

Do not invent information that is not supported by the
context.

If the context is insufficient, say that you do not have
enough information.

Repository context:

{context}

User question:

{question}
```

## Tasks

- [ ] Create LLM service
- [ ] Add API key to `.env`
- [ ] Send context
- [ ] Send question
- [ ] Receive response
- [ ] Handle API errors
- [ ] Limit output length appropriately

## Definition of Done

The application can answer repository questions using retrieved context.

---

# 14. Phase 10 — FastAPI RAG Endpoints

Create two main endpoints.

## Analyze Repository

```http
POST /analyze
```

Request:

```json
{
  "url": "https://github.com/user/project"
}
```

Response:

```json
{
  "status": "success",
  "files": 42,
  "chunks": 317
}
```

The endpoint should:

```text
URL
 ↓
Clone
 ↓
Read files
 ↓
Chunk
 ↓
Embed
 ↓
Store in ChromaDB
```

## Ask Question

```http
POST /chat
```

Request:

```json
{
  "repository_id": "...",
  "question": "How does authentication work?"
}
```

Response:

```json
{
  "answer": "Authentication is handled..."
}
```

The endpoint should:

```text
Question
 ↓
Embed
 ↓
Retrieve
 ↓
Build context
 ↓
LLM
 ↓
Answer
```

---

# 15. Phase 11 — Basic Source References

Do not build complicated citation handling yet.

Every retrieved chunk already knows its file.

If the LLM says:

```text
Authentication is implemented using JWT...
```

display:

```text
Sources:
- src/auth.py
- src/middleware/auth.py
```

## Later

You can store:

```text
start_line
end_line
```

and show:

```text
src/auth.py:42-81
```

But this is optional for the first version.

---

# 16. Phase 12 — React Frontend

Create one simple page.

```text
┌──────────────────────────────────────────────┐
│                 codedive                    │
│                                              │
│ GitHub Repository                            │
│ ┌──────────────────────────────────────────┐ │
│ │ https://github.com/user/project          │ │
│ └──────────────────────────────────────────┘ │
│                              [Analyze]        │
│                                              │
│ Status: ✓ Repository indexed                 │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ How does authentication work?            │ │
│ └──────────────────────────────────────────┘ │
│                                    [Ask]     │
│                                              │
│ ──────────────────────────────────────────── │
│                                              │
│ Authentication is implemented using...      │
│                                              │
│ Sources:                                     │
│ • src/auth.py                                │
│ • src/middleware/auth.py                     │
└──────────────────────────────────────────────┘
```

## Components

```text
App
├── RepositoryInput
├── AnalyzeButton
├── Status
├── Chat
├── Message
└── ChatInput
```

## Definition of Done

A user can enter a repository URL and ask questions through the browser.

---

# 17. Phase 13 — Conversation History

Add basic conversation history.

Example:

```text
User:
Where is authentication implemented?

AI:
Authentication is implemented in src/auth.py.

User:
How is the token generated?

AI:
The token is generated using...
```

Initially, conversation history can simply live in React state.

No database is required.

---

# 18. Phase 14 — Streaming

Once the normal request/response flow works, optionally stream LLM responses.

Instead of:

```text
[wait]
[wait]
[wait]
complete answer
```

show:

```text
Authentication is implemented...
Authentication is implemented using JWT...
Authentication is implemented using JWT middleware...
```

This improves the UX but is not required for the core RAG functionality.

---

# 19. Testing

## Unit Tests

Test:

- GitHub URL validation
- File filtering
- Chunking
- Empty files
- Large files
- Retrieval
- Context construction

## Integration Test

Test the complete pipeline:

```text
GitHub URL
 ↓
Clone
 ↓
Extract
 ↓
Chunk
 ↓
Embed
 ↓
ChromaDB
 ↓
Retrieve
 ↓
LLM
 ↓
Answer
```

## Manual RAG Tests

Use a known repository and ask:

```text
1. What framework does this project use?

2. Where is the main entry point?

3. How does authentication work?

4. Where is the database connection created?

5. What happens when the application receives a request?

6. What external APIs does the application use?
```

Check whether the retrieved files actually contain the answer.

---

# 20. Error Handling

The application should handle:

- Invalid GitHub URL
- Repository not found
- Private repository
- Git clone failure
- Empty repository
- Unsupported files
- Very large repository
- Embedding API failure
- LLM API failure
- ChromaDB failure
- Empty search results

Show simple user-friendly messages.

Example:

```text
Could not analyze this repository.
Please check that the GitHub URL is valid and public.
```

Do not expose stack traces or API keys.

---

# 21. Security

The application should **never execute repository code**.

Only:

```text
clone
→ read
→ parse
→ embed
```

Do not:

```text
run scripts
install dependencies
execute Dockerfiles
run Makefiles
execute repository commands
```

Keep LLM and embedding API keys on the backend.

Never put API keys in the React frontend.

---

# 22. Recommended Development Order

Follow this exact sequence:

```text
1. FastAPI setup
       ↓
2. GitHub cloning
       ↓
3. File extraction
       ↓
4. Chunking
       ↓
5. Embeddings
       ↓
6. ChromaDB
       ↓
7. Retrieval
       ↓
8. LLM
       ↓
9. RAG API
       ↓
10. React UI
       ↓
11. Source references
       ↓
12. Conversation history
       ↓
13. Streaming
```

Do not start the frontend before the basic RAG pipeline works.

---

# 23. MVP Definition

The project is complete when this workflow works:

## Step 1

User enters:

```text
https://github.com/user/project
```

## Step 2

Application shows:

```text
Analyzing repository...

✓ Repository cloned
✓ Files loaded
✓ Chunks created
✓ Embeddings generated
✓ Repository indexed
```

## Step 3

User asks:

```text
How does authentication work?
```

## Step 4

Backend performs:

```text
Question
 ↓
Embedding
 ↓
Vector Search
 ↓
Top 5 Chunks
 ↓
LLM
```

## Step 5

Frontend displays:

```text
Authentication is handled by...

Sources:
- src/auth.py
- src/middleware.py
```

That is enough for the first version.

---

# 24. What NOT to Build

Keep the project intentionally small.

Do NOT add these to the first version:

- AST parsing
- Tree-sitter
- Dependency graphs
- GraphRAG
- Hybrid search
- Reranking
- Agents
- Multi-agent systems
- Authentication
- User accounts
- Redis
- Celery
- Kubernetes
- Microservices
- PostgreSQL
- Complex evaluation frameworks
- Automatic code modification

These can be future improvements if you have time.

---

# 25. Optional Improvements After MVP

If the basic project works and you want one or two improvements, use this order:

### 1. Better metadata

Add:

```text
file
language
start_line
end_line
```

### 2. Better citations

Show:

```text
src/auth.py:42-81
```

### 3. Streaming

Stream the LLM answer.

### 4. Repository tree

Show:

```text
src/
├── auth/
├── api/
├── database/
└── services/
```

Stop after these unless there is a specific reason to go further.

---

# 26. Final Portfolio Description

A simple accurate description:

> **Built a GitHub repository RAG application that clones public repositories, extracts and chunks source code, generates vector embeddings, and uses semantic retrieval with an LLM to answer questions about the codebase with source-file references.**

Do not claim advanced retrieval or code intelligence features unless you actually implement them.

---

# 27. First Coding Session

Your first session should accomplish only this:

```text
Create FastAPI project
        ↓
Create /health
        ↓
Create POST /analyze
        ↓
Accept GitHub URL
        ↓
Clone repository
        ↓
Return:
    repository name
    number of files
```

For example:

```json
{
  "repository": "project",
  "files": 42
}
```

Once that works, commit:

```bash
git add .
git commit -m "feat: add GitHub repository ingestion"
```

Then move to file extraction.

The priority is:

**working pipeline > sophisticated architecture.**

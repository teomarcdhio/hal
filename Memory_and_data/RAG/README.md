## RAG Implementation for Meal Agent

This directory contains a progressive series of scripts demonstrating how to add Retrieval-Augmented Generation (RAG) and Learning capabilities to a Meal Planning Agent.

### Key Scripts

1.  **`meal_agent_no_butter.py`**
    *   **Base Agent:** The original meal planning agent that strictly enforces a "no butter" rule.
    *   **Functionality:** Generates meal plans based on user input, ensuring no ingredients contain butter.

2.  **`meal_agent_rag_storage.py`**
    *   **RAG + Disk Persistence:** Adds basic RAG using LlamaIndex.
    *   **Functionality:** Reads from `recipes.txt`. Stores the vector index locally on the filesystem (`./storage` folder) to avoid re-indexing on every run.

3.  **`meal_agent_rag_chromadb.py`**
    *   **RAG + ChromaDB:** Migrates the storage backend from local files to a dedicated Vector Database (ChromaDB).
    *   **Functionality:** Connects to a local ChromaDB instance (running via `chroma run`). Allows for more scalable vector storage and retrieval.

4.  **`meal_agent_rag_chromadb_learning.py`** (Best Version)
    *   **The "Learning" Agent:** Adds a feedback loop.
    *   **Functionality:**
        *   Retrieves recipes from ChromaDB.
        *   If the Inspector (Chef) approves a *newly generated* recipe, it is automatically saved back into the `recipes` collection in ChromaDB.
        *   This allows the agent to "remember" successful creations for future requests.

### Utilities

*   **`inspect_remote_chroma.py`**
    *   A utility script to connect to the running ChromaDB server (`localhost:8000`) and inspect stored collections and documents. Useful for verifying that new recipes have been saved.
*   **`inspect_chroma.py`**
    *   A utility script to inspect the local filesystem database directly (without server).

*   **`recipes.txt`**
    *   The initial source text file containing "Grandma's Secret Pancakes" and other seed data for the RAG system.

### How to Run

1.  **Start ChromaDB Server:**
    ```bash
    chroma run --path ./chroma_db --port 8000
    ```

2.  **Run the Learning Agent:**
    ```bash
    uv run meal_agent_rag_chromadb_learning.py
    ```

3.  **Inspect the Database:**
    You can use the python script:
    ```bash
    uv run inspect_remote_chroma.py
    ```
    Or use `curl` to fetch documents directly:
    ```bash
    # Get Collection ID first
    curl -s "http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections"
    
    # Fetch documents (replace ID)
    curl -X POST "http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/<COLLECTION_ID>/get" \
         -H "Content-Type: application/json" \
         -d '{"limit": 5, "include": ["documents", "metadatas"]}'
    ```

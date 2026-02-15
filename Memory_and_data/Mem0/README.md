# Meal Agent with Mem0 Memory

This project implements an intelligent meal planning agent using `LangGraph` for orchestration and `Mem0` (with ChromaDB) for long-term memory.

## Features

1.  **Specialized Chefs**:
    *   **Breakfast Chef**: Focuses on energetic, morning-friendly recipes.
    *   **Lunch Chef**: Focuses on balanced, quick midday meals.
    *   **Dinner Chef**: Focuses on comforting, substantial evening meals.
    *   **Router**: Intelligently routes user requests to the appropriate chef based on intent.

2.  **Strict Health Inspector**:
    *   **Butter Prohibition**: The inspector checks every generated recipe. If it contains "butter", the recipe is rejected, and the chef is forced to rewrite it.
    *   **Duplicate Detection**: The inspector checks the `Mem0` long-term memory. If a recipe is substantially similar to one offered previously, it is rejected as a duplicate, ensuring variety.

3.  **Long-Term Memory (Mem0)**:
    *   Recipes that pass inspection are stored in a local ChromaDB vector store.
    *   The agent "remembers" past recipes to avoid repetition.

## Setup

1.  **Install Dependencies**:
    Ensure you have `uv` installed, then run:
    ```bash
    uv sync
    ```
    (Or install `langgraph`, `langchain-openai`, `mem0ai[chroma]`, `python-dotenv` manually).

2.  **Environment Variables**:
    Create a `.env` file with your OpenAI API key:
    ```
    OPENAI_API_KEY=sk-...
    ```

## Usage

### Running the Agent
Start the interactive chat session:
```bash
uv run meal_agent_no_butter.py
```

**Example Interaction**:
- User: "I want pancakes."
- Chef: *Generates a pancake recipe.*
- Inspector: *Checks for butter and duplicates.*
- (If butter found): Inspector sends it back. Chef rewrites it.
- (If duplicate): Inspector sends it back. Chef generates a new variant.
- (If pass): Inspector saves it to memory.

### Inspecting Memory
View what the agent has currently stored in its memory:
```bash
uv run inspect_memory.py
```
This script lists all stored recipes with their IDs and creation timestamps.

## Project Structure

- `meal_agent_no_butter.py`: Main agent logic, graph definition, and memory integration.
- `inspect_memory.py`: Utility script to view stored memories.
- `.mem0/`: Local storage directory for ChromaDB (created automatically).

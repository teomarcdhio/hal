# Family Agent with Mem0 and LangGraph

This is a basic agent that stores family details in a persistent memory (Mem0) and retrieves them to answer questions.

## Setup

1.  Ensure you have `uv` installed.
2.  Install dependencies:
    ```bash
    uv sync
    ```
3.  Ensure your `.env` file has a valid `OPENAI_API_KEY`.

## Usage

Run the agent:

```bash
uv run family_agent.py
```

## How it works

1.  **Memory**: Uses `mem0` with a local ChromaDB vector store (`.mem0-family` folder).
2.  **Orchestration**: Uses `langgraph` to manage the interaction state.
3.  **LLM**: Uses `gpt-5-nano` via `langchain-openai`.

## Example Interaction

```text
You: My sister Alice was born on May 5th, 1990.
Agent: Got it. I've noted that down.

You: What is my mom's maiden name?
Agent: I don't have that information yet.

You: My mom's maiden name is Smith.
Agent: Okay, remembered.

You: When was my sister born?
Agent: Your sister Alice was born on May 5th, 1990.
```

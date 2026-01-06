# PydanticAI Agent

This project demonstrates a simple service using [PydanticAI](https://ai.pydantic.dev/) that relies on a remote agent running on OpenAI.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed
- Python 3.9+
- An OpenAI API Key

## Setup

1.  **Install Dependencies**

    This project uses `uv` for dependency management.

    ```bash
    uv sync
    ```

2.  **Configure Environment**

    Create a `.env` file in the root directory (or ensure one exists in the parent/root if running from there, but better to have one here) and add your OpenAI API key:

    ```bash
    echo "OPENAI_API_KEY=your_api_key_here" > .env
    ```

## Available Agents

### 1. Simple Agent (`agent.py`)

A basic single-agent chatbot.

**Run:**
```bash
uv run agent.py
```

### 2. Meal Orchestrator (`meal_agent.py`)

A routing-based multi-agent workflow using PydanticAI.
It uses a **Router Agent** to classify the user's request (Breakfast, Lunch, Dinner, Other) and then dispatches the task to a specialized **Chef Agent**.

**Run:**
```bash
uv run meal_agent.py
```

## Usage

For all agents, type your message and press Enter. Type `quit`, `exit`, or `q` to stop the script.

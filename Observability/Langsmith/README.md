# LangGraph OpenAI Agent

This project demonstrates a simple service using [LangGraph](https://langchain-ai.github.io/langgraph/) that relies on a remote agent running on OpenAI.

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

    Create a `.env` file in the root directory and add your OpenAI API key:

    ```bash
    echo "OPENAI_API_KEY=your_api_key_here" > .env
    ```

## Available Agents

This project contains three different examples of LangGraph agents, each demonstrating different orchestration patterns.

### 1. Simple Agent (`agent.py`)

A basic single-agent chatbot. It uses a single LLM node to respond to user inputs.

**Pattern:** Single Node
**Run:**
```bash
uv run agent.py
```

### 2. Recipe Agent (`recipe_agent.py`)

A sequential multi-agent workflow. It detects if you are asking for a recipe. If so, a "Master Chef" provides the standard recipe, which is then passed to a "Creative Chef" who suggests a unique variation or twist.

**Pattern:** Sequential Handoff (Router -> Chef -> Creative Chef)
**Run:**
```bash
uv run recipe_agent.py
```

### 3. Meal Orchestrator (`meal_agent.py`)

A routing-based multi-agent workflow. An orchestrator (Router) analyzes your request to determine if it's for Breakfast, Lunch, or Dinner, and routes it to a specialized chef agent.

**Pattern:** Conditional Routing / Orchestrator (Router -> [Breakfast | Lunch | Dinner])
**Run:**
```bash
uv run meal_agent.py
```

### 4. Multi-Model Meal Orchestrator (`meal_agent_multi_model.py`)

Similar to the Meal Orchestrator, but demonstrates using **different LLM models** for specific tasks to optimize for cost or capability.

- **Router & General Chat:** `gpt-5-nano` (Fast & Cheap)
- **Breakfast & Lunch Chefs:** `gpt-5-mini` (Balanced)
- **Dinner Chef:** `gpt-4.1-mini` (High Quality)

**Pattern:** Conditional Routing with Specialized Models
**Run:**
```bash
uv run meal_agent_multi_model.py
```

## Usage

For all agents, type your message and press Enter. Type `quit`, `exit`, or `q` to stop the script. 
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

## Observability (OTEL Example)

The `meal_agent_no_butter.py` example is instrumented with OpenTelemetry and exports data to OTLP/HTTP endpoints configured in `.env`.

The OpenTelemetry setup code is isolated in `observability.py`.

### What We Observe

#### 1. Traces

- `agent.turn`: one span per user request (end-to-end turn)
- `llm.invoke`: one span per LLM call (router, chefs, inspector, general chat)
- Span attributes include:
    - `llm.model`
    - `agent.node`
    - `llm.tokens.input`
    - `llm.tokens.output`
    - `llm.tokens.total`

#### 2. Metrics

- `agent_turns_total`: total turns processed
- `agent_turn_latency_ms`: end-to-end turn latency histogram
- `llm_requests_total`: total LLM calls (with status attributes)
- `llm_latency_ms`: LLM call latency histogram
- `llm_input_tokens_total`: total prompt/input tokens
- `llm_output_tokens_total`: total completion/output tokens
- `llm_total_tokens_total`: total token usage

#### 3. Logs

- Structured logs are exported through OTLP logs
- Logs include trace correlation fields:
    - `trace_id`
    - `span_id`
- Logs include turn start/end, LLM call summaries, token usage (when available), and errors

### Token Usage Collection

Token usage is extracted from model responses via:

- `response.usage_metadata`
- `response.response_metadata["token_usage"]`

If usage data is unavailable for a call, the app logs that tokens were not provided.

### Environment Variables

Typical `.env` values:

```env
OPENAI_API_KEY=...

OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.internal.nivetek.com
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://otel.internal.nivetek.com/v1/traces
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://otel.internal.nivetek.com/v1/metrics
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://otel.internal.nivetek.com/v1/logs

# Optional auth headers (comma-separated key=value pairs)
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer <token>

# Required for self-signed/internal TLS certs
OTEL_EXPORTER_OTLP_INSECURE=true

OTEL_SERVICE_NAME=meal-agent-no-butter
OTEL_SERVICE_VERSION=0.1.0
OTEL_ENVIRONMENT=dev
LOG_LEVEL=INFO
LOKI_URL=https://loki.internal.nivetek.com
```

### Run the OTEL Instrumented Agent

```bash
uv run meal_agent_no_butter.py
```
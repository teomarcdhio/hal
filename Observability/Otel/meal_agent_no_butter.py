import os
import uuid
from time import perf_counter
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from opentelemetry import metrics, trace
from observability import setup_observability


def extract_token_usage(response: AIMessage) -> dict[str, int] | None:
    usage: dict[str, int] = {}

    usage_meta = getattr(response, "usage_metadata", None)
    if isinstance(usage_meta, dict):
        usage.update(usage_meta)

    response_meta = getattr(response, "response_metadata", None)
    if isinstance(response_meta, dict):
        token_usage = response_meta.get("token_usage")
        if isinstance(token_usage, dict):
            usage.update(token_usage)

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
    total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

    if input_tokens == 0 and output_tokens == 0 and total_tokens == 0:
        return None

    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(total_tokens),
    }


def _is_true(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


LOG_LLM_OUTPUT = False
LOG_LLM_OUTPUT_MAX_CHARS = 800


def _response_text_for_logging(response: AIMessage) -> str:
    text = parse_output(response)
    if len(text) <= LOG_LLM_OUTPUT_MAX_CHARS:
        return text
    return f"{text[:LOG_LLM_OUTPUT_MAX_CHARS]}... [truncated]"


# --- Configuration ---
load_dotenv()

LOG_LLM_OUTPUT = _is_true(os.getenv("LOG_LLM_OUTPUT", "false"))
LOG_LLM_OUTPUT_MAX_CHARS = int(os.getenv("LOG_LLM_OUTPUT_MAX_CHARS", "800"))

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

tracer, meter, logger = setup_observability()
logger.info(
    "LLM output logging: enabled=%s max_chars=%s",
    LOG_LLM_OUTPUT,
    LOG_LLM_OUTPUT_MAX_CHARS,
)

llm_requests_total = meter.create_counter(
    "llm_requests_total",
    description="Total number of LLM requests",
)
llm_input_tokens_total = meter.create_counter(
    "llm_input_tokens_total",
    unit="token",
    description="Total prompt/input tokens sent to LLMs",
)
llm_output_tokens_total = meter.create_counter(
    "llm_output_tokens_total",
    unit="token",
    description="Total completion/output tokens returned by LLMs",
)
llm_total_tokens_total = meter.create_counter(
    "llm_total_tokens_total",
    unit="token",
    description="Total tokens consumed by LLMs",
)
llm_latency_ms = meter.create_histogram(
    "llm_latency_ms",
    unit="ms",
    description="LLM request latency",
)
agent_turns_total = meter.create_counter(
    "agent_turns_total",
    description="Total chat turns processed by the agent",
)
agent_turn_latency_ms = meter.create_histogram(
    "agent_turn_latency_ms",
    unit="ms",
    description="End-to-end latency for a user turn",
)


def format_prompt(system_text: str, messages: list[BaseMessage]) -> list[BaseMessage]:
    return [SystemMessage(content=system_text)] + messages


def parse_output(response: AIMessage) -> str:
    try:
        return str(response.content)
    except Exception:
        return str(response)


def invoke_llm(llm: ChatOpenAI | None, messages: list[BaseMessage], node_name: str) -> AIMessage:
    if llm is None:
        return AIMessage(content="")

    model_name = getattr(llm, "model_name", "unknown")
    attrs = {
        "model": model_name,
        "node": node_name,
    }

    with tracer.start_as_current_span("llm.invoke", attributes={"llm.model": model_name, "agent.node": node_name}) as span:
        start = perf_counter()
        try:
            response = llm.invoke(messages)
            elapsed_ms = (perf_counter() - start) * 1000
            llm_requests_total.add(1, attributes={**attrs, "status": "ok"})
            llm_latency_ms.record(elapsed_ms, attributes=attrs)

            usage = extract_token_usage(response)
            if usage:
                llm_input_tokens_total.add(usage["input_tokens"], attributes=attrs)
                llm_output_tokens_total.add(usage["output_tokens"], attributes=attrs)
                llm_total_tokens_total.add(usage["total_tokens"], attributes=attrs)
                span.set_attribute("llm.tokens.input", usage["input_tokens"])
                span.set_attribute("llm.tokens.output", usage["output_tokens"])
                span.set_attribute("llm.tokens.total", usage["total_tokens"])
                logger.info(
                    "LLM call completed: node=%s model=%s latency_ms=%.2f input_tokens=%s output_tokens=%s total_tokens=%s",
                    node_name,
                    model_name,
                    elapsed_ms,
                    usage["input_tokens"],
                    usage["output_tokens"],
                    usage["total_tokens"],
                )
            else:
                logger.info(
                    "LLM call completed: node=%s model=%s latency_ms=%.2f (token usage not available)",
                    node_name,
                    model_name,
                    elapsed_ms,
                )

            if LOG_LLM_OUTPUT:
                logger.info(
                    "LLM output: node=%s model=%s content=%s",
                    node_name,
                    model_name,
                    _response_text_for_logging(response),
                )

            return response
        except Exception:
            elapsed_ms = (perf_counter() - start) * 1000
            llm_requests_total.add(1, attributes={**attrs, "status": "error"})
            llm_latency_ms.record(elapsed_ms, attributes=attrs)
            logger.exception("LLM call failed: node=%s model=%s", node_name, model_name)
            raise


# --- State Definition ---
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    active_chef: str


# --- LLM Setup ---
try:
    llm_nano = ChatOpenAI(model="gpt-5-nano", temperature=0.7)
    llm_mini = ChatOpenAI(model="gpt-5-mini", temperature=0.7)
    llm_dinner = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)
except Exception as exc:
    logger.exception("Error initializing ChatOpenAI models: %s", exc)
    llm_nano = None
    llm_mini = None
    llm_dinner = None


# --- Node Definitions ---
def router_node(state: State) -> Literal["breakfast_chef", "lunch_chef", "dinner_chef", "general_chat"]:
    if llm_nano is None:
        return "general_chat"

    last_message = state["messages"][-1]
    prompt = format_prompt(
        """You are a routing assistant. Classify the user's request into one of the following categories:
        - BREAKFAST: If the user is asking for a breakfast recipe.
        - LUNCH: If the user is asking for a lunch recipe.
        - DINNER: If the user is asking for a dinner recipe.
        - OTHER: For any other request.

        Respond ONLY with the category name (BREAKFAST, LUNCH, DINNER, or OTHER).""",
        [last_message],
    )
    response = invoke_llm(llm_nano, prompt, "router")
    category = parse_output(response).strip().upper()
    logger.info("Router classified request as: %s", category)

    if "BREAKFAST" in category:
        return "breakfast_chef"
    if "LUNCH" in category:
        return "lunch_chef"
    if "DINNER" in category:
        return "dinner_chef"
    return "general_chat"


def breakfast_chef_node(state: State):
    if llm_mini is None:
        return {"messages": []}

    prompt = format_prompt(
        "You are a specialist Breakfast Chef. Provide a delicious and energetic breakfast recipe based on the user's request. Focus on morning ingredients.",
        state["messages"],
    )
    response = invoke_llm(llm_mini, prompt, "breakfast_chef")
    return {"messages": [AIMessage(content=f"**Breakfast Chef:**\n{parse_output(response)}")], "active_chef": "breakfast_chef"}


def lunch_chef_node(state: State):
    if llm_mini is None:
        return {"messages": []}

    prompt = format_prompt(
        "You are a specialist Lunch Chef. Provide a balanced and quick lunch recipe based on the user's request. Focus on midday sustenance.",
        state["messages"],
    )
    response = invoke_llm(llm_mini, prompt, "lunch_chef")
    return {"messages": [AIMessage(content=f"**Lunch Chef:**\n{parse_output(response)}")], "active_chef": "lunch_chef"}


def dinner_chef_node(state: State):
    if llm_dinner is None:
        return {"messages": []}

    prompt = format_prompt(
        "You are a specialist Dinner Chef. Provide a comforting and substantial dinner recipe based on the user's request. Focus on evening relaxation and flavor.",
        state["messages"],
    )
    response = invoke_llm(llm_dinner, prompt, "dinner_chef")
    return {"messages": [AIMessage(content=f"**Dinner Chef:**\n{parse_output(response)}")], "active_chef": "dinner_chef"}


def general_chat_node(state: State):
    if llm_nano is None:
        return {"messages": []}

    response = invoke_llm(llm_nano, state["messages"], "general_chat")
    return {"messages": [AIMessage(content=parse_output(response))], "active_chef": "general_chat"}


def inspector_feedback_node(state: State):
    return {
        "messages": [
            HumanMessage(content="The inspector found butter in your recipe. Please rewrite the recipe WITHOUT using butter."),
        ]
    }


# --- Graph Construction ---
graph_builder = StateGraph(State)
graph_builder.add_node("breakfast_chef", breakfast_chef_node)
graph_builder.add_node("lunch_chef", lunch_chef_node)
graph_builder.add_node("dinner_chef", dinner_chef_node)
graph_builder.add_node("general_chat", general_chat_node)
graph_builder.add_node("inspector_feedback", inspector_feedback_node)

graph_builder.add_conditional_edges(
    START,
    router_node,
    {
        "breakfast_chef": "breakfast_chef",
        "lunch_chef": "lunch_chef",
        "dinner_chef": "dinner_chef",
        "general_chat": "general_chat",
    },
)


def inspector_router(state: State):
    if llm_nano is None:
        return END

    last_message = state["messages"][-1]
    active_chef = state.get("active_chef")

    if active_chef == "general_chat":
        return END

    prompt = format_prompt(
        "You are a strict health inspector. Check the following recipe for the ingredient 'butter'. If it contains butter, respond with 'CONTAINS_BUTTER'. If it does not, respond with 'PASS'.",
        [last_message],
    )
    response = invoke_llm(llm_nano, prompt, "inspector")
    result = parse_output(response).strip().upper()

    if "CONTAINS_BUTTER" in result:
        logger.warning("Inspector detected butter. Requesting recipe rewrite from %s.", active_chef)
        return "inspector_feedback"

    logger.info("Inspector passed recipe with no butter.")
    return END


graph_builder.add_conditional_edges(
    "breakfast_chef",
    inspector_router,
    {"inspector_feedback": "inspector_feedback", END: END},
)
graph_builder.add_conditional_edges(
    "lunch_chef",
    inspector_router,
    {"inspector_feedback": "inspector_feedback", END: END},
)
graph_builder.add_conditional_edges(
    "dinner_chef",
    inspector_router,
    {"inspector_feedback": "inspector_feedback", END: END},
)

graph_builder.add_edge("general_chat", END)


def feedback_router(state: State):
    return state["active_chef"]


graph_builder.add_conditional_edges(
    "inspector_feedback",
    feedback_router,
    {
        "breakfast_chef": "breakfast_chef",
        "lunch_chef": "lunch_chef",
        "dinner_chef": "dinner_chef",
    },
)

graph = graph_builder.compile()


# --- Execution ---
if __name__ == "__main__":
    print("Starting No-Butter Meal Agent...")
    print("Ask for a recipe (try asking for something with butter, like croissants or mashed potatoes)!")

    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable.")

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            turn_id = str(uuid.uuid4())
            turn_attrs = {"entrypoint": "cli"}
            with tracer.start_as_current_span(
                "agent.turn",
                attributes={
                    "agent.turn_id": turn_id,
                    "agent.entrypoint": "cli",
                    "user.input_length": len(user_input),
                },
            ):
                turn_start = perf_counter()
                agent_turns_total.add(1, attributes=turn_attrs)
                logger.info("New user turn received: turn_id=%s", turn_id)

                for event in graph.stream({"messages": [HumanMessage(content=user_input)]}):
                    for value in event.values():
                        if "messages" in value:
                            for msg in value["messages"]:
                                print(f"\n{msg.content}")

                turn_latency_ms = (perf_counter() - turn_start) * 1000
                agent_turn_latency_ms.record(turn_latency_ms, attributes=turn_attrs)
                logger.info("User turn completed: turn_id=%s latency_ms=%.2f", turn_id, turn_latency_ms)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as exc:
            logger.exception("Unhandled error in main loop: %s", exc)
            print(f"An error occurred: {exc}")
            break

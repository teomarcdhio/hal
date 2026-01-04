import os
from typing import Annotated, TypedDict, Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# --- Configuration ---
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

# --- State Definition ---
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- LLM Setup ---
# We initialize different models for different tasks as requested.
try:
    # gpt-5-nano for routing and general chat
    llm_nano = ChatOpenAI(
        model="gpt-5-nano",
        temperature=0.7,
    )
    
    # gpt-5-mini for breakfast and lunch
    llm_mini = ChatOpenAI(
        model="gpt-5-mini",
        temperature=0.7,
    )
    
    # gpt-4.1-mini for dinner
    llm_dinner = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.7,
    )
    
except Exception as e:
    print(f"Error initializing ChatOpenAI models: {e}")
    llm_nano = None
    llm_mini = None
    llm_dinner = None

# --- Node Definitions ---

def router_node(state: State) -> Literal["breakfast_chef", "lunch_chef", "dinner_chef", "general_chat"]:
    """
    Acts as the Orchestrator. Analyzes the user's intent and routes to the appropriate chef.
    Uses gpt-5-nano.
    """
    if llm_nano is None:
        return "general_chat"
        
    messages = state["messages"]
    last_message = messages[-1]
    
    # We ask the LLM to classify the intent
    prompt = [
        SystemMessage(content="""You are a routing assistant. Classify the user's request into one of the following categories:
        - BREAKFAST: If the user is asking for a breakfast recipe.
        - LUNCH: If the user is asking for a lunch recipe.
        - DINNER: If the user is asking for a dinner recipe.
        - OTHER: For any other request.
        
        Respond ONLY with the category name (BREAKFAST, LUNCH, DINNER, or OTHER)."""),
        last_message
    ]
    response = llm_nano.invoke(prompt)
    print(f"Router response: {response.content}")
    category = response.content.strip().upper()
    print(f"Router classified the request as: {category}")
    
    if "BREAKFAST" in category:
        return "breakfast_chef"
    elif "LUNCH" in category:
        return "lunch_chef"
    elif "DINNER" in category:
        return "dinner_chef"
    else:
        return "general_chat"

def breakfast_chef_node(state: State):
    """
    Uses gpt-5-mini.
    """
    if llm_mini is None: return {"messages": []}
    messages = state["messages"]
    prompt = [
        SystemMessage(content="You are a specialist Breakfast Chef. Provide a delicious and energetic breakfast recipe based on the user's request. Focus on morning ingredients."),
        messages[-1]
    ]
    response = llm_mini.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Breakfast Chef (gpt-5-mini):**\n{response.content}")]}

def lunch_chef_node(state: State):
    """
    Uses gpt-5-mini.
    """
    if llm_mini is None: return {"messages": []}
    messages = state["messages"]
    prompt = [
        SystemMessage(content="You are a specialist Lunch Chef. Provide a balanced and quick lunch recipe based on the user's request. Focus on midday sustenance."),
        messages[-1]
    ]
    response = llm_mini.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Lunch Chef (gpt-5-mini):**\n{response.content}")]}

def dinner_chef_node(state: State):
    """
    Uses gpt-4.1-mini.
    """
    if llm_dinner is None: return {"messages": []}
    messages = state["messages"]
    prompt = [
        SystemMessage(content="You are a specialist Dinner Chef. Provide a comforting and substantial dinner recipe based on the user's request. Focus on evening relaxation and flavor."),
        messages[-1]
    ]
    response = llm_dinner.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Dinner Chef (gpt-4.1-mini):**\n{response.content}")]}

def general_chat_node(state: State):
    """
    Uses gpt-5-nano.
    """
    if llm_nano is None: return {"messages": []}
    messages = state["messages"]
    response = llm_nano.invoke(messages)
    return {"messages": [response]}

# --- Graph Construction ---
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("breakfast_chef", breakfast_chef_node)
graph_builder.add_node("lunch_chef", lunch_chef_node)
graph_builder.add_node("dinner_chef", dinner_chef_node)
graph_builder.add_node("general_chat", general_chat_node)

# Add conditional edges from START using the router logic
graph_builder.add_conditional_edges(
    START,
    router_node,
    {
        "breakfast_chef": "breakfast_chef",
        "lunch_chef": "lunch_chef",
        "dinner_chef": "dinner_chef",
        "general_chat": "general_chat"
    }
)

# All nodes go to END
graph_builder.add_edge("breakfast_chef", END)
graph_builder.add_edge("lunch_chef", END)
graph_builder.add_edge("dinner_chef", END)
graph_builder.add_edge("general_chat", END)

graph = graph_builder.compile()

# --- Execution ---
if __name__ == "__main__":
    print("Starting Multi-Model Meal Orchestrator Agent...")
    print("Ask for a breakfast, lunch, or dinner recipe!")
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable.")

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            for event in graph.stream({"messages": [HumanMessage(content=user_input)]}):
                for key, value in event.items():
                    for msg in value["messages"]:
                        print(f"\n{msg.content}")
                    
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

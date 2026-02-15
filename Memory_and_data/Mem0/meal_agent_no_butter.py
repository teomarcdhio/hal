import os
from typing import Annotated, TypedDict, Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from mem0 import Memory
from mem0.configs.base import MemoryConfig

# --- Configuration ---
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

# --- Memory Setup ---
config_data = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "recipes",
            "path": ".mem0"
        }
    },
    "custom_fact_extraction_prompt": (
        "You are a Cooking Archive Assistant. Extract recipes as detailed memories. "
        "When you receive a recipe, extract the full recipe content (Title, Ingredients, Instructions) "
        "as a single fact if possible, or key facts about the dish. "
        "Do not leave out ingredients or steps. "
        "Return the facts in JSON format as follows: {\"facts\": [\"Recipe: Title... Ingredients: ... Method: ...\"]}"
    )
}
memory = Memory(config=MemoryConfig(**config_data))

# --- State Definition ---
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    active_chef: str # To track which chef is handling the request
    inspector_feedback_msg: str # Feedback from the inspector

# --- LLM Setup ---
try:
    # gpt-5-nano for routing, general chat, and inspection
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
    """
    if llm_nano is None:
        return "general_chat"
        
    messages = state["messages"]
    last_message = messages[-1]
    
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
    if llm_mini is None: return {"messages": []}
    messages = state["messages"]
    
    # If we are looping back, the last message will be from the inspector.
    # We need to ensure the context is preserved.
    
    prompt = [
        SystemMessage(content="You are a specialist Breakfast Chef. Provide a delicious and energetic breakfast recipe based on the user's request. Focus on morning ingredients."),
    ] + messages # Pass full history so the chef sees the critique
    
    response = llm_mini.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Breakfast Chef:**\n{response.content}")], "active_chef": "breakfast_chef"}

def lunch_chef_node(state: State):
    if llm_mini is None: return {"messages": []}
    messages = state["messages"]
    
    prompt = [
        SystemMessage(content="You are a specialist Lunch Chef. Provide a balanced and quick lunch recipe based on the user's request. Focus on midday sustenance."),
    ] + messages
    
    response = llm_mini.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Lunch Chef:**\n{response.content}")], "active_chef": "lunch_chef"}

def dinner_chef_node(state: State):
    if llm_dinner is None: return {"messages": []}
    messages = state["messages"]
    
    prompt = [
        SystemMessage(content="You are a specialist Dinner Chef. Provide a comforting and substantial dinner recipe based on the user's request. Focus on evening relaxation and flavor."),
    ] + messages
    
    response = llm_dinner.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Dinner Chef:**\n{response.content}")], "active_chef": "dinner_chef"}

def general_chat_node(state: State):
    if llm_nano is None: return {"messages": []}
    messages = state["messages"]
    response = llm_nano.invoke(messages)
    return {"messages": [response], "active_chef": "general_chat"}

def inspector_node(state: State):
    """
    Inspects the recipe for butter and duplicates.
    """
    if llm_nano is None: return {}
    
    messages = state["messages"]
    last_message = messages[-1]
    active_chef = state.get("active_chef")
    
    if active_chef == "general_chat":
        return {"inspector_feedback_msg": "PASS"}

    recipe_text = last_message.content

    # 1. Check for Butter using LLM
    prompt = [
        SystemMessage(content="You are a strict health inspector. Check the following recipe for the ingredient 'butter'. If it contains butter, respond with 'CONTAINS_BUTTER'. If it does not, respond with 'PASS'."),
        last_message
    ]
    response = llm_nano.invoke(prompt)
    result = response.content.strip().upper()
    
    if "CONTAINS_BUTTER" in result:
        print("\n[Inspector]: Butter detected! Sending back for revision...")
        return {"inspector_feedback_msg": "The inspector found butter in your recipe. Please rewrite the recipe WITHOUT using butter."}

    # 2. Check Memory for Duplicates using Mem0
    print("\n[Inspector]: Checking memory for duplicates...")
    try:
        # Search for similar recipes
        search_results = memory.search(recipe_text, user_id="hal_chef", limit=1)
        
        # Handle dict response
        existing_recipes = []
        if isinstance(search_results, dict):
            existing_recipes = search_results.get("results", [])
        elif isinstance(search_results, list):
            existing_recipes = search_results

        if existing_recipes:
             retrieved_text = existing_recipes[0].get('memory', '')
             # Double check with LLM if it is truly the same
             comparison_prompt = [
                 SystemMessage(content="Compare the following two recipes. If they are essentially the same recipe (same dish, similar ingredients), respond 'DUPLICATE'. If they are different, respond 'NEW'."),
                 HumanMessage(content=f"Recipe 1 (New): {recipe_text}\n\nRecipe 2 (Existing): {retrieved_text}")
             ]
             comp_response = llm_nano.invoke(comparison_prompt)
             if "DUPLICATE" in comp_response.content.strip().upper():
                 print("\n[Inspector]: Duplicate recipe detected in memory! Sending back for revision...")
                 return {"inspector_feedback_msg": f"You have already offered this recipe before (Inspector remembers: {retrieved_text[:50]}...). Please create a NEW and DIFFERENT recipe."}
    except Exception as e:
        print(f"Error checking memory: {e}")

    # 3. Pass & Verify
    print("\n[Inspector]: Recipe passed checks. Adding to memory.")
    try:
        memory.add(recipe_text, user_id="hal_chef")
    except Exception as e:
        print(f"Error adding to memory: {e}")
        
    return {"inspector_feedback_msg": "PASS"}

def inspector_feedback_node(state: State):
    # This node adds the feedback message to the state before routing back
    msg = state.get("inspector_feedback_msg", "Please revise the recipe.")
    return {"messages": [HumanMessage(content=msg)]}

# --- Graph Construction ---
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("breakfast_chef", breakfast_chef_node)
graph_builder.add_node("lunch_chef", lunch_chef_node)
graph_builder.add_node("dinner_chef", dinner_chef_node)
graph_builder.add_node("general_chat", general_chat_node)
graph_builder.add_node("inspector", inspector_node)
graph_builder.add_node("inspector_feedback", inspector_feedback_node)

# Add conditional edges from START
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

def inspector_edge(state: State):
    msg = state.get("inspector_feedback_msg")
    if msg == "PASS":
        return END
    return "inspector_feedback"

# Chefs go to the inspector
graph_builder.add_edge("breakfast_chef", "inspector")
graph_builder.add_edge("lunch_chef", "inspector")
graph_builder.add_edge("dinner_chef", "inspector")

# Inspector routes based on result
graph_builder.add_conditional_edges(
    "inspector",
    inspector_edge,
    {
        "inspector_feedback": "inspector_feedback",
        END: END
    }
)

# General chat goes to END
graph_builder.add_edge("general_chat", END)

# Inspector feedback routes back to the active chef
def feedback_router(state: State):
    return state["active_chef"]

graph_builder.add_conditional_edges(
    "inspector_feedback",
    feedback_router,
    {
        "breakfast_chef": "breakfast_chef",
        "lunch_chef": "lunch_chef",
        "dinner_chef": "dinner_chef"
    }
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

            for event in graph.stream({"messages": [HumanMessage(content=user_input)]}):
                for key, value in event.items():
                    if "messages" in value:
                        for msg in value["messages"]:
                            print(f"\n{msg.content}")
                    
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

import os
from typing import Annotated, TypedDict, Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, Document
from llama_index.llms.openai import OpenAI

# ChromaDB imports
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

# --- Configuration ---
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

# --- RAG Setup (LlamaIndex + ChromaDB) ---
rag_query_engine = None
index = None
try:
    # Set the LLM for LlamaIndex query engine to also use gpt-5-nano for speed/consistency
    Settings.llm = OpenAI(model="gpt-5-nano", temperature=0.7)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    recipes_path = os.path.join(script_dir, "recipes.txt")
    chroma_db_path = os.path.join(script_dir, "chroma_db")

    # Initialize Chroma client
    print(f"Initializing ChromaDB at {chroma_db_path}...")
    db = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = db.get_or_create_collection("recipes")
    
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Check if we need to load data (if empty)
    if chroma_collection.count() == 0:
        if os.path.exists(recipes_path):
             print(f"Loading recipes from {recipes_path} into ChromaDB...")
             documents = SimpleDirectoryReader(input_files=[recipes_path]).load_data()
             index = VectorStoreIndex.from_documents(
                 documents, storage_context=storage_context
             )
             print("Recipes loaded into ChromaDB.")
        else:
             print("recipes.txt not found and ChromaDB is empty. RAG disabled.")
             index = None
    else:
        print(f"Loading existing RAG index from ChromaDB ({chroma_collection.count()} items)...")
        index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context
        )
    
    if index:
        rag_query_engine = index.as_query_engine()

except Exception as e:
    print(f"Error initializing LlamaIndex RAG with ChromaDB: {e}")

# --- State Definition ---
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    active_chef: str # To track which chef is handling the request

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

# --- Helper ---
def get_rag_context(messages: list[BaseMessage]) -> str:
    """Retrieves relevant context from the RAG engine based on the last user message."""
    context = ""
    if rag_query_engine:
        try:
            # Find the last user message for query context
            last_human_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
            if last_human_msg:
                query_response = rag_query_engine.query(last_human_msg.content)
                if query_response and str(query_response).strip():
                    context = str(query_response)
        except Exception as e:
            print(f"Error querying RAG engine: {e}")
    return context

def breakfast_chef_node(state: State):
    if llm_mini is None: return {"messages": []}
    messages = state["messages"]
    
    # Retrieve relevant context from RAG if available
    context = get_rag_context(messages)

    prompt_content = "You are a specialist Breakfast Chef. Provide a delicious and energetic breakfast recipe based on the user's request. Focus on morning ingredients."
    if context:
        prompt_content += f"\n\nIMPORTANT: Use the following INTERNAL RECIPES found in the database. You MUST recommend one of these recipes as your primary suggestion if they match the user's request. Do not make up a new recipe if a suitable one exists here:\n{context}"
    else:
        prompt_content += "\nNo internal recipes found. You can suggest a recipe from your general knowledge."

    prompt = [
        SystemMessage(content=prompt_content),
    ] + messages # Pass full history so the chef sees the critique
    
    response = llm_mini.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Breakfast Chef:**\n{response.content}")], "active_chef": "breakfast_chef"}

def lunch_chef_node(state: State):
    if llm_mini is None: return {"messages": []}
    messages = state["messages"]
    
    context = get_rag_context(messages)
    
    prompt_content = "You are a specialist Lunch Chef. Provide a balanced and quick lunch recipe based on the user's request. Focus on midday sustenance."
    if context:
        prompt_content += f"\n\nIMPORTANT: Use the following INTERNAL RECIPES found in the database. You MUST recommend one of these recipes as your primary suggestion if they match the user's request. Do not make up a new recipe if a suitable one exists here:\n{context}"
    else:
        prompt_content += "\nNo internal recipes found. You can suggest a recipe from your general knowledge."

    prompt = [
        SystemMessage(content=prompt_content),
    ] + messages
    
    response = llm_mini.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Lunch Chef:**\n{response.content}")], "active_chef": "lunch_chef"}

def dinner_chef_node(state: State):
    if llm_dinner is None: return {"messages": []}
    messages = state["messages"]
    
    context = get_rag_context(messages)
    
    prompt_content = "You are a specialist Dinner Chef. Provide a comforting and substantial dinner recipe based on the user's request. Focus on evening relaxation and flavor."
    if context:
        prompt_content += f"\n\nIMPORTANT: Use the following INTERNAL RECIPES found in the database. You MUST recommend one of these recipes as your primary suggestion if they match the user's request. Do not make up a new recipe if a suitable one exists here:\n{context}"
    else:
        prompt_content += "\nNo internal recipes found. You can suggest a recipe from your general knowledge."

    prompt = [
        SystemMessage(content=prompt_content),
    ] + messages
    
    response = llm_dinner.invoke(prompt)
    return {"messages": [AIMessage(content=f"**Dinner Chef:**\n{response.content}")], "active_chef": "dinner_chef"}

def general_chat_node(state: State):
    if llm_nano is None: return {"messages": []}
    messages = state["messages"]
    response = llm_nano.invoke(messages)
    return {"messages": [response], "active_chef": "general_chat"}

def inspector_feedback_node(state: State):
    # This node just adds the feedback message to the state before routing back
    return {"messages": [HumanMessage(content="The inspector found butter in your recipe. Please rewrite the recipe WITHOUT using butter.")]}

def save_recipe_node(state: State):
    """
    Saves the approved recipe to the ChromaDB index.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if index and isinstance(last_message, AIMessage):
        try:
            # We treat the entire Chef's response as the document content
            # In a real app, we might want to parse out just the recipe part
            recipe_content = last_message.content
            
            # Create a Document
            # We can tag it with metadata like 'approved_by_inspector': True
            doc = Document(
                text=recipe_content,
                metadata={"category": "user_generated", "approved": True}
            )
            
            # Add to index
            index.insert(doc)
            print("\n[System]: New butter-free recipe saved to ChromaDB library!")
            
            # Persist changes not explicitly needed for Chroma (auto-persists), but good practice
            # index.storage_context.persist() 
            
        except Exception as e:
            print(f"\n[System]: Failed to save recipe: {e}")
            
    return {"messages": []} # No new messages added, just sidebar effect

# --- Graph Construction ---
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("breakfast_chef", breakfast_chef_node)
graph_builder.add_node("lunch_chef", lunch_chef_node)
graph_builder.add_node("dinner_chef", dinner_chef_node)
graph_builder.add_node("general_chat", general_chat_node)
graph_builder.add_node("inspector_feedback", inspector_feedback_node)
graph_builder.add_node("save_recipe", save_recipe_node)

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

# Define the routing logic for the inspector
def inspector_router(state: State):
    if llm_nano is None: return END
    
    messages = state["messages"]
    active_chef = state.get("active_chef")
    
    if active_chef == "general_chat":
        return END

    last_message = messages[-1]
    prompt = [
        SystemMessage(content="You are a strict health inspector. Check the following recipe for the ingredient 'butter'. If it contains butter, respond with 'CONTAINS_BUTTER'. If it does not, respond with 'PASS'."),
        last_message
    ]
    response = llm_nano.invoke(prompt)
    result = response.content.strip().upper()
    
    if "CONTAINS_BUTTER" in result:
        print("\n[Inspector]: Butter detected! Sending back for revision...")
        return "inspector_feedback"
    else:
        print("\n[Inspector]: Recipe passed (no butter). Saving to library...")
        return "save_recipe"

# Chefs go to the inspector router
graph_builder.add_conditional_edges("breakfast_chef", inspector_router, {"inspector_feedback": "inspector_feedback", "save_recipe": "save_recipe", END: END})
graph_builder.add_conditional_edges("lunch_chef", inspector_router, {"inspector_feedback": "inspector_feedback", "save_recipe": "save_recipe", END: END})
graph_builder.add_conditional_edges("dinner_chef", inspector_router, {"inspector_feedback": "inspector_feedback", "save_recipe": "save_recipe", END: END})

# General chat goes to END
graph_builder.add_edge("general_chat", END)

# Save recipe goes to END
graph_builder.add_edge("save_recipe", END)

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
    print("Starting Learning Meal Agent (ChromaDB Version)...")
    print("Recipes that pass inspection will be saved to the database for future use!")
    print("Ask for a recipe (try asking for 'mashed potatoes WITHOUT butter')!")
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable.")

    running_state = {"messages": []}

    while True:
        try:
            user_input = input("\nUser (q to quit): ")
            if user_input.lower() in ["q", "quit", "exit"]:
                print("Goodbye!")
                break

            input_message = HumanMessage(content=user_input)
            running_state["messages"].append(input_message)
            
            print(f"Processing...")
            for event in graph.stream({"messages": [input_message]}):
                for key, value in event.items():
                    if "messages" in value:
                        for msg in value["messages"]:
                            if isinstance(msg, AIMessage) and msg.content:
                                print(f"\n[{key}]: {msg.content}")
                            elif isinstance(msg, HumanMessage):
                                print(f"\n[{key}]: {msg.content}") 
                                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

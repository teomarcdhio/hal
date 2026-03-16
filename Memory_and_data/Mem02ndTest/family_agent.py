import os
from typing import Annotated, TypedDict

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
    print("WARNING: OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")

# --- Memory Setup ---
# Initialize Mem0 with a local vector store configuration for persistence
memory_config = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "family_facts",
            "path": ".mem0-family",  # Local folder to store the database
        }
    }
}
memory = Memory(config=MemoryConfig(**memory_config))


# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    context: str  # To store retrieved memories


# --- LLM Setup ---
try:
    llm = ChatOpenAI(
        model="gpt-5-nano",  # Using the specified model
        temperature=0,      # Low temperature for factual consistency
    )
except Exception as e:
    print(f"Error initializing ChatOpenAI: {e}")
    llm = None


# --- Core Logic ---

def call_model(state: AgentState):
    """
    Process the user's message:
    1. Search for relevant memories.
    2. Add the current interaction to memory (for future reference).
    3. Generate a response using the memories as context.
    """
    if llm is None:
        return {"messages": [AIMessage(content="Error: Check OPENAI_API_KEY.")]}
    
    messages = state["messages"]
    last_message = messages[-1]
    
    if not isinstance(last_message, HumanMessage):
         return {"messages": []}

    user_query = last_message.content
    user_id = "user_family_1"  # Identifier for the user session

    # 1. Search for relevant existing memories *before* adding the new one
    #    (so we answer based on what we already knew, plus context)
    relevant_memories = memory.search(user_query, user_id=user_id, limit=3)
    
    context_str = ""
    
    # Handle search results robustness (dict or list)
    mem_list = []
    if isinstance(relevant_memories, dict):
        mem_list = relevant_memories.get("results", [])
    elif isinstance(relevant_memories, list):
        mem_list = relevant_memories
        
    extracted_memories = []
    for mem in mem_list:
        # Each memory item is typically a dict with keys like 'memory', 'id', etc.
        if isinstance(mem, dict):
             # Try to get the memory content
            content = mem.get("memory") or mem.get("text") or str(mem)
            extracted_memories.append(f"- {content}")
        else:
             extracted_memories.append(f"- {str(mem)}")
    
    if extracted_memories:
        context_str = "\n".join(extracted_memories)

    # 2. Selectively add to memory (Only store family facts, ignore questions/chit-chat)
    #    We ask the LLM to extract relevant facts first.
    extraction_prompt = (
        f"Analyze the following user input: '{user_query}'. "
        "Extract any new factual details explicitly mentioned about the user's family, relatives, or their attributes (names, dates, relationships). "
        "Return ONLY the extracted facts as a clear statement. "
        "If no new family facts are present (e.g. if it's a question, a greeting, or unrelated), return 'NO_FACTS'."
    )
    
    extraction_res = llm.invoke([HumanMessage(content=extraction_prompt)])
    facts_to_store = extraction_res.content.strip()

    if "NO_FACTS" not in facts_to_store:
        # Only add to Mem0 if we actually found something worth remembering
        memory.add(facts_to_store, user_id=user_id)
        # Optional: Print to console for visibility
        print(f"\n[Memory] Storing new fact: {facts_to_store}")

    # 3. Construct the prompt with context
    system_prompt = (
        "You are a helpful family assistant. You remember details about the user's family. "
        "Use the following context (memories) to answer the user's question if relevant. "
        "If you don't know the answer based on the context or general knowledge, just say so. "
        "Don't explicitly mention 'I found this in my memory', just answer naturally."
        "\n\nContext from Memory:\n"
        f"{context_str}"
    )
    
    # We replace the system message instructions or append them
    # Simple approach: Create a temporary message list for the LLM call
    messages_for_llm = [SystemMessage(content=system_prompt)] + messages

    response = llm.invoke(messages_for_llm)
    
    return {"messages": [response], "context": context_str}


# --- Graph Construction ---
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

app = workflow.compile()


# --- Execution Loop ---
if __name__ == "__main__":
    print("Family Agent Started! (Type 'quit' to exit)")
    print("I can remember details about your family. Try telling me something first.")
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            
            # Run the graph
            inputs = {"messages": [HumanMessage(content=user_input)]}
            
            # Stream the output
            for output in app.stream(inputs):
                for key, value in output.items():
                    if "messages" in value:
                        last_msg = value["messages"][-1]
                        print(f"Agent: {last_msg.content}")
                        
                        # Debug: Show what context was used
                        # if "context" in value and value["context"]:
                        #    print(f"\n[Debug] Context used:\n{value['context']}\n")

        except Exception as e:
            print(f"An error occurred: {e}")
            break

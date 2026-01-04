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
try:
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
    )
except Exception as e:
    print(f"Error initializing ChatOpenAI: {e}")
    llm = None

# --- Node Definitions ---

def route_request(state: State) -> Literal["chef", "general_chat"]:
    if llm is None:
        return "general_chat" # Fallback
        
    messages = state["messages"]
    # Analyze the last message to determine intent
    last_message = messages[-1]
    
    prompt = [
        SystemMessage(content="Is the following user input asking for a cooking recipe? Respond with 'YES' or 'NO'."),
        last_message
    ]
    response = llm.invoke(prompt)
    
    if "YES" in response.content.strip().upper():
        return "chef"
    return "general_chat"

def chef_node(state: State):
    if llm is None:
        return {"messages": [SystemMessage(content="Error: LLM not initialized.")]}

    messages = state["messages"]
    # The chef responds to the user's request
    prompt = [
        SystemMessage(content="You are a master chef. Provide a detailed recipe for the user's request."),
        messages[-1]
    ]
    response = llm.invoke(prompt)
    
    # Format the output to indicate who is speaking
    content = f"**Master Chef:**\n{response.content}"
    return {"messages": [AIMessage(content=content)]}

def creative_chef_node(state: State):
    if llm is None:
        return {"messages": []}

    messages = state["messages"]
    # messages[-1] is the Master Chef's recipe
    # messages[-2] is the User's request (assuming simple turn)
    # We pass the context to the creative chef
    
    original_recipe = messages[-1].content
    # Find the last human message for context
    user_request = "Unknown request"
    for msg in reversed(messages[:-1]):
        if isinstance(msg, HumanMessage):
            user_request = msg.content
            break
            
    prompt = [
        SystemMessage(content="You are an experimental chef. The user asked for a recipe, and a master chef provided one. Your job is to suggest a creative, interesting variation or twist on that recipe. Be brief and focus on the modification."),
        HumanMessage(content=f"User Request: {user_request}\n\nOriginal Recipe: {original_recipe}")
    ]
    response = llm.invoke(prompt)
    
    content = f"**Creative Chef:**\n{response.content}"
    return {"messages": [AIMessage(content=content)]}

def general_chat_node(state: State):
    if llm is None:
        return {"messages": [SystemMessage(content="Error: LLM not initialized.")]}
        
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

# --- Graph Construction ---
graph_builder = StateGraph(State)

graph_builder.add_node("chef", chef_node)
graph_builder.add_node("creative_chef", creative_chef_node)
graph_builder.add_node("general_chat", general_chat_node)

# Conditional routing from START
graph_builder.add_conditional_edges(
    START,
    route_request,
    {
        "chef": "chef",
        "general_chat": "general_chat"
    }
)

# Chef always passes to Creative Chef
graph_builder.add_edge("chef", "creative_chef")

# Creative Chef and General Chat end the turn
graph_builder.add_edge("creative_chef", END)
graph_builder.add_edge("general_chat", END)

graph = graph_builder.compile()

# --- Execution ---
if __name__ == "__main__":
    print("Starting Recipe Agent...")
    print("Ask for a recipe to see the multi-agent interaction!")
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable.")

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            # Stream the output
            for event in graph.stream({"messages": [HumanMessage(content=user_input)]}):
                for key, value in event.items():
                    # value["messages"] is a list of new messages
                    for msg in value["messages"]:
                        print(f"\n{msg.content}")
                    
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

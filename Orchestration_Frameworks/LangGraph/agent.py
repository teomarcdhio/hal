import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
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
        model="gpt-5-nano",
        temperature=0.1,
    )
except Exception as e:
    print(f"Error initializing ChatOpenAI: {e}")
    llm = None

# --- Node Definitions ---
def chatbot(state: State):
    if llm is None:
        return {"messages": [SystemMessage(content="Error: LLM not initialized. Check API key.")]}
    
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

# --- Graph Construction ---
graph_builder = StateGraph(State)

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()

# --- Execution ---
if __name__ == "__main__":
    print("Starting OpenAI Agent...")
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable.")

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            for event in graph.stream({"messages": [HumanMessage(content=user_input)]}):
                for value in event.values():
                    # ChatOpenAI response content is directly accessible
                    print("Agent:", value["messages"][-1].content)
                    
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

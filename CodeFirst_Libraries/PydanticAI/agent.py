import os
import asyncio
from dotenv import load_dotenv
from pydantic_ai import Agent

# --- Configuration ---
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

# --- Agent Definition ---
# PydanticAI allows defining the model directly in the Agent constructor.
# We use 'openai:gpt-3.5-turbo' to match the previous examples.
agent = Agent(
    'openai:gpt-5-nano',
    system_prompt='You are a helpful assistant.',
)

# --- Execution ---
async def main():
    print("Starting PydanticAI Agent...")
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable.")

    # PydanticAI agents are stateless by default in terms of conversation history 
    # across run calls unless managed. 
    # However, for a simple "agent.py" equivalent which was just a loop in LangGraph 
    # (which maintained state via the graph), we might want to maintain history.
    # But the original agent.py in LangGraph *did* maintain history because it passed 
    # the state back into the graph.
    
    # PydanticAI's `run` method returns a result which contains new messages.
    # We can pass these messages back to the next run call to maintain context.
    
    messages = []

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            # Run the agent with the user input and the accumulated message history
            result = await agent.run(user_input, message_history=messages)
            
            # Print the response
            # Handle potential attribute differences in pydantic-ai versions
            if hasattr(result, 'data'):
                print(f"Agent: {result.data}")
            else:
                # Fallback for other versions or if result is different
                print(f"Agent: {result}")
            
            # Update history with the new messages from this turn
            # result.new_messages() returns the messages exchanged in this run (User + Model)
            if hasattr(result, 'new_messages'):
                print(f"Debug: New messages - {result.new_messages()}")
                messages.extend(result.new_messages())
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())

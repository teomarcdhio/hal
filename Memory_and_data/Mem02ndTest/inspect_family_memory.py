import os
from dotenv import load_dotenv
from mem0 import Memory
from mem0.configs.base import MemoryConfig

# --- Configuration ---
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")

# --- Memory Setup ---
# Must match the config in family_agent.py
memory_config = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "family_facts",
            "path": ".mem0-family",
        }
    }
}

def list_memories():
    print("Initializing Memory...")
    # Initialize Mem0
    try:
        memory = Memory(config=MemoryConfig(**memory_config))
    except Exception as e:
        print(f"Error initializing memory: {e}")
        return

    user_id = "user_family_1"
    print(f"\nRetrieving memories for user: {user_id}...")
    
    try:
        # Get all memories
        memories = memory.get_all(user_id=user_id)
        
        # Handle response structure (it can vary by version, usually a dict or list)
        if isinstance(memories, dict):
            results = memories.get("results", [])
        elif isinstance(memories, list):
            results = memories
        else:
            results = []

        if not results:
            print("No memories found.")
            return

        print(f"\nFound {len(results)} memories:\n")
        for i, mem in enumerate(results):
            # Extract text/content
            content = mem.get("memory") or mem.get("text") or str(mem)
            # Try to get timestamp if available
            created_at = mem.get("created_at") or mem.get("timestamp") or "N/A"
            
            print(f"[{i+1}] {content} {created_at}")
            # print(f"    ID: {mem.get('id', 'N/A')} | Created: {created_at}")
            
    except Exception as e:
        print(f"Error retrieving memories: {e}")

if __name__ == "__main__":
    list_memories()

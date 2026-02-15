import os
from dotenv import load_dotenv
from mem0 import Memory
from mem0.configs.base import MemoryConfig

load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found!")

# --- Memory Setup ---
config_data = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "recipes",
            "path": ".mem0"
        }
    }
}

def inspect_memories():
    try:
        memory = Memory(config=MemoryConfig(**config_data))
        
        print("\n=== Recipe Memory Inspector (User: hal_chef) ===")
        results = memory.get_all(user_id="hal_chef")
        
        # Handle different return types based on version/config
        if isinstance(results, dict):
            memories = results.get("results", [])
        elif isinstance(results, list):
            memories = results
        else:
            memories = []

        if not memories:
            print("No memories found for user 'hal_chef'.")
        else:
            print(f"Found {len(memories)} recipes in memory:\n")
            
            # Sort by creation date if available
            try:
                memories.sort(key=lambda x: x.get('created_at') or "", reverse=True)
            except: pass

            for i, mem in enumerate(memories):
                print(f"Recipe #{i+1}")
                print(f"ID: {mem.get('id')}")
                print(f"Created: {mem.get('created_at')}")
                
                text = mem.get("memory", "No text")
                # Indent text for better readability
                print("Content:")
                print(f"{text[:300]}..." if len(text) > 300 else f"{text}")
                print("-" * 60)

    except Exception as e:
        print(f"Error accessing memory: {e}")

if __name__ == "__main__":
    inspect_memories()

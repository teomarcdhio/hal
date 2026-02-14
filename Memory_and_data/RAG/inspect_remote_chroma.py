import chromadb
from chromadb.config import Settings
import logging
import http.client

# Enable HTTP connection debugging
http.client.HTTPConnection.debuglevel = 1

def list_remote_collections():
    print("Connecting to ChromaDB server at http://localhost:8000...")
    try:
        # Connect to server
        client = chromadb.HttpClient(host='localhost', port=8000)
        
        # List collections
        collections = client.list_collections()
        print(f"\nFound {len(collections)} collections:")
        
        for col in collections:
            print(f"  Name: {col.name}")
            print(f"  ID: {col.id}")
            print(f"  Metadata: {col.metadata}")
            
    except Exception as e:
        print(f"Error connecting/listing: {e}")

if __name__ == "__main__":
    list_remote_collections()

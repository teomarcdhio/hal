import os
import asyncio
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
import nest_asyncio

# Apply nest_asyncio to allow nested event loops if necessary
nest_asyncio.apply()

# --- Configuration ---
load_dotenv()

# --- Agent Definition ---
agent = Agent(
    'openai:gpt-5-nano',
    system_prompt='You are a helpful email assistant. You can send emails using the defined tools.',
    deps_type=str # We can use deps to pass dependencies if needed, or simple type
 
)

# --- Tool Definition ---
@agent.tool
def send_email(ctx: RunContext[str], recipient: str, subject: str, body: str) -> str:
    """
    Send an email using Gmail SMTP.
    
    Args:
        recipient: The email address receiving the email.
        subject: The subject/title of the email.
        body: The body content of the email.
        
    Returns:
        A success message or error description.
    """
    sender = os.getenv("GMAIL_SENDER") or os.getenv("GMAIL_USERNAME") or "mmarcolinionline@gmail.com" # Fallback/Configuration
    password = os.getenv("GMAIL_PASSWORD")
    
    if not password:
        return "Error: GMAIL_PASSWORD not set in environment variables."
        
    print(f"DEBUG: Attempting to send email to {recipient} with subject '{subject}'")

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return f"Email sent successfully to {recipient}"
    except Exception as e:
        return f"Error sending email: {str(e)}"

# --- Execution ---
async def main():
    print("Starting Email Agent...")
    print("Ensure GMAIL_PASSWORD is set in your .env file.")
    
    messages = []
    
    while True:
        try:
            user_input = input("\nUser (or 'q' to quit): ")
            if user_input.lower() in ["q", "quit", "exit"]:
                break
                
            # Run the agent
            result = await agent.run(user_input, message_history=messages)
            
            print(f"Agent: {result.data}")
            
            # Update history
            messages.extend(result.new_messages())
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())

import os

from dotenv import load_dotenv
import asyncio
from composio import Composio
from agents import Agent, Runner
from composio_openai_agents import OpenAIAgentsProvider

# Load environment variables
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

composio = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"), provider=OpenAIAgentsProvider())

# Id of the user in your system
externalUserId = "c3e00703-0478-4974-8873-bb6b6586f8bf"

# Create an auth config for gmail from the dashboard or programmatically
auth_config_id = os.environ.get("AUTH_CONFIG_ID")
connection_request = composio.connected_accounts.link(
    user_id=externalUserId,
    auth_config_id=auth_config_id,
)

# Redirect user to the OAuth flow
redirect_url = connection_request.redirect_url

print(
    f"Please authorize the app by visiting this URL: {redirect_url}"
)  # Print the redirect url to the user

# Wait for the connection to be established
connected_account = connection_request.wait_for_connection()
print(
    f"Connection established successfully! Connected account id: {connected_account.id}"
)

# Get Gmail tools that are pre-configured
tools = composio.tools.get(user_id=externalUserId, tools=["GMAIL_SEND_EMAIL"])

agent = Agent(
    name="Email Manager", instructions="You are a helpful assistant", tools=tools
)

# Run the agent
async def main():
    result = await Runner.run(
        starting_agent=agent,
        input="Send an email to mmarcolinishop@gmail.com with the subject 'Hello from composio 👋🏻' and the body 'Congratulations on sending your first email using AI Agents and Composio!'",
    )
    print(result.final_output)

asyncio.run(main())

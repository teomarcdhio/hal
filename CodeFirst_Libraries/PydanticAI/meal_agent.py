import os
import asyncio
from typing import Literal
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic import BaseModel

# --- Configuration ---
load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

# --- Agents Definition ---

# 1. Router Agent
# We can use a structured result type (Literal) to enforce the classification output.
router_agent = Agent(
    'openai:gpt-5-nano',
    system_prompt="""You are a routing assistant. Classify the user's request into one of the following categories:
    - BREAKFAST: If the user is asking for a breakfast recipe.
    - LUNCH: If the user is asking for a lunch recipe.
    - DINNER: If the user is asking for a dinner recipe.
    - OTHER: For any other request.""",
    output_type=Literal['BREAKFAST', 'LUNCH', 'DINNER', 'OTHER'],
)

# 2. Breakfast Chef Agent
class chefResponse(BaseModel):
    greeting: str
    recipe_name: str
    ingredients: list[str]
    instructions: list[str]
    energy_level: str

breakfast_chef_agent = Agent(
    'openai:gpt-5-mini',
    output_type=chefResponse,
    system_prompt="You are a specialist Breakfast Chef. Provide a delicious and energetic breakfast recipe based on the user's request. Focus on morning ingredients. Start your response with 'Hi, I'm your breakfast chef.'",
)

# 3. Lunch Chef Agent
lunch_chef_agent = Agent(
    'openai:gpt-5-mini',
    system_prompt="You are a specialist Lunch Chef. Provide a balanced and quick lunch recipe based on the user's request. Focus on midday sustenance. Start your response with 'Hi, I'm your lunch chef.'",
)

# 4. Dinner Chef Agent
dinner_chef_agent = Agent(
    'openai:gpt-4.1-mini',
    system_prompt="You are a specialist Dinner Chef. Provide a comforting and substantial dinner recipe based on the user's request. Focus on evening relaxation and flavor. Start your response with 'Hi, I'm your dinner chef.'",
)

# 5. General Chat Agent
general_chat_agent = Agent(
    'openai:gpt-5-nano',
    system_prompt="You are a helpful assistant.",
)

# --- Execution ---
async def main():
    print("Starting PydanticAI Meal Orchestrator Agent...")
    print("Ask for a breakfast, lunch, or dinner recipe!")
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable.")

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            # Step 1: Route the request
            # We run the router agent to classify the intent
            print("...Routing...")
            router_result = await router_agent.run(user_input)
            category = router_result.output
            print(f"Router classified the request as: {category}")

            # Step 2: Dispatch to the appropriate agent
            response_data = ""
            
            if category == 'BREAKFAST':
                result = await breakfast_chef_agent.run(user_input)
                chef = result.output
                response_data = f"{chef.greeting}\n\n**{chef.recipe_name}**\nIngredients: {', '.join(chef.ingredients)}\nEnergy: {chef.energy_level}"
                # response_data = f"**Breakfast Chef:**\n{result.output.greeting}\nRecipe Name: {result.output.recipe_name}\nIngredients: {', '.join(result.output.ingredients)}\nInstructions: {' '.join(result.output.instructions)}\nEnergy Level: {result.output.energy_level}"
                
            elif category == 'LUNCH':
                result = await lunch_chef_agent.run(user_input)
                response_data = f"**Lunch Chef:**\n{result.output.greeting}\nRecipe Name: {result.output.recipe_name}\nIngredients: {', '.join(result.output.ingredients)}\nInstructions: {' '.join(result.output.instructions)}\nEnergy Level: {result.output.energy_level}"
                
            elif category == 'DINNER':
                result = await dinner_chef_agent.run(user_input)
                response_data = f"**Dinner Chef:**\n{result.output.greeting}\nRecipe Name: {result.output.recipe_name}\nIngredients: {', '.join(result.output.ingredients)}\nInstructions: {' '.join(result.output.instructions)}\nEnergy Level: {result.output.energy_level}"
                
            else: # OTHER
                result = await general_chat_agent.run(user_input)
                response_data = f"**General Chat:**\n{result.output.content}"

            print(f"\n{response_data}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())

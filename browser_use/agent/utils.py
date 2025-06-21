import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

def get_model():
    """Initialize and return the chat model based on environment variables."""
    load_dotenv()
    
    try:
        model_provider = os.getenv("MODEL_PROVIDER")
        model_name = os.getenv("MODEL_NAME")
        
        if model_provider and model_name:
            return init_chat_model(f"{model_provider}:{model_name}")
        else:
            return init_chat_model("google_genai:gemini-2.0-flash")
    except Exception as e:
        print(f"Error initializing model: {e}")
        import traceback
        traceback.print_exc()
        raise
    
SYSTEM_MESSAGE = """
You are a browser automation agent. 
Your task is to perform actions in a web browser to achieve a user's goal.
You will be provided with the current screenshot of the browser, the user's goal.
You can use tools to click elements, type text etc.
"""
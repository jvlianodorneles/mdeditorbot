import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Convert API_ID to int if present
if API_ID is not None:
    try:
        API_ID = int(API_ID)
    except ValueError:
        pass

# Simple validation function to see if configuration is valid
def is_configured() -> bool:
    return bool(API_ID and API_HASH and BOT_TOKEN)

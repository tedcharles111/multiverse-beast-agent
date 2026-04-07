# config.py
import os
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEYS = [
    os.getenv("MISTRAL_API_KEY_1"),
    os.getenv("MISTRAL_API_KEY_2"),
    os.getenv("MISTRAL_API_KEY_3"),
]
# Remove any None values (in case not all keys are set)
MISTRAL_API_KEYS = [k for k in MISTRAL_API_KEYS if k]

DEPLOY_HOST = os.getenv("DEPLOY_HOST")
DEPLOY_USER = os.getenv("DEPLOY_USER")
DEPLOY_KEY_PATH = os.getenv("DEPLOY_KEY_PATH")
DEPLOY_WEB_ROOT = os.getenv("DEPLOY_WEB_ROOT")

# src/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api")

# App configuration
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
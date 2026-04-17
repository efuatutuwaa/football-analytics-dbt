import os
import time
import requests
from dotenv import load_dotenv
from databricks import sql

# -- 1. Config -----------------------------------

load_dotenv()
API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY')
DATABRICKS_HOST = os.getenv('DATABRICKS_HOST')
DATABRICKS_HTTP_PATH = os.getenv('DATABRICKS_HTTP_PATH')
DATABRICKS_TOKEN = os.getenv('DATABRICKS_TOKEN')


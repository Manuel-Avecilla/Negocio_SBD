import boto3
from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DOCKER_DIR = BASE_DIR / "Docker"
ENV_PATH = DOCKER_DIR / ".env"

load_dotenv(ENV_PATH)


session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    region_name=os.getenv("AWS_REGION"))


client = session.client('dynamodb')

print(client.list_tables())

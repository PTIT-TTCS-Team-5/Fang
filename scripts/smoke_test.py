import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi.testclient import TestClient

from app.main import app


def run_tests():
    with TestClient(app) as client:
        print("Testing /v2/healthz")
        resp = client.get("/v2/healthz")
        print("Healthz:", resp.status_code, resp.json())

        # We test ingestion API
        print("Testing /v2/ingestion/jobs")
        payload = {
            "jobAppId": 40,
            "cvSnapUrl": "https://res.cloudinary.com/dfwkw1guc/image/upload/v1775987977/sample_ml2jzo.pdf",
        }
        resp = client.post("/v2/ingestion/jobs", json=payload)
        print("Ingest:", resp.status_code, resp.json())
        # We test chat API
        print("Testing /v2/chat/query")
        chat_payload = {
            "jobAppId": 40,
            "hrId": 23,
            "prompt": "Hello",
            "modelMode": "auto-lite",
        }
        resp = client.post("/v2/chat/query", json=chat_payload)
        print("Chat:", resp.status_code, resp.json())


if __name__ == "__main__":
    run_tests()

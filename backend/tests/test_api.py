from fastapi.testclient import TestClient
import sys 
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from api.main import create_app


client = TestClient(create_app())

def test_factcheck_query_params():
    response = client.get(
        "/verify",
        params={"claim": "The sky is blue"},
    )

    assert response.status_code == 200
    assert response.json()["answer"]== "True"


test_factcheck_query_params()
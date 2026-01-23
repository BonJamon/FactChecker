import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL")

def test_root():
    url = f"{API_URL}/"
    resp = requests.get(url)
    print("GET / ->", resp.status_code, resp.text)

def test_health():
    url = f"{API_URL}/health"
    resp = requests.get(url)
    print("GET /health ->", resp.status_code, resp.text)

def test_verify(claim: str):
    url = f"{API_URL}/verify"
    params = {"claim": claim}
    resp = requests.get(url, params=params)
    print(f"GET /verify?claim={claim} ->", resp.status_code, resp.text)

if __name__ == "__main__":
    test_root()
    test_health()
    test_verify("pluto is a planet.")
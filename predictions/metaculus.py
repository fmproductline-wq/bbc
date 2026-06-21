"""Metaculus integration — browse questions and track forecasts."""
import requests
from loguru import logger
from config import cfg

BASE = "https://www.metaculus.com/api2"


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if cfg.METACULUS_TOKEN:
        h["Authorization"] = f"Token {cfg.METACULUS_TOKEN}"
    return h


def search_questions(query: str, limit: int = 5) -> list[dict]:
    """Search open Metaculus questions."""
    resp = requests.get(
        f"{BASE}/questions/",
        params={"search": query, "status": "open", "limit": limit},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [
        {
            "id": q["id"],
            "title": q["title"],
            "community_prediction": q.get("community_prediction", {}).get("full", {}).get("q2"),
            "close_time": q.get("close_time"),
            "resolve_time": q.get("resolve_time"),
            "url": f"https://www.metaculus.com/questions/{q['id']}/",
        }
        for q in results
    ]


def get_question(question_id: int) -> dict:
    resp = requests.get(f"{BASE}/questions/{question_id}/", headers=_headers(), timeout=10)
    resp.raise_for_status()
    q = resp.json()
    return {
        "id": q["id"],
        "title": q["title"],
        "community_prediction": q.get("community_prediction", {}).get("full", {}).get("q2"),
        "close_time": q.get("close_time"),
        "url": f"https://www.metaculus.com/questions/{q['id']}/",
    }


def submit_prediction(question_id: int, probability: float) -> dict:
    """Submit a probability forecast (0.0–1.0) to Metaculus."""
    resp = requests.post(
        f"{BASE}/questions/{question_id}/predict/",
        json={"prediction": probability},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()
    logger.info(f"Metaculus prediction submitted: q{question_id} = {probability}")
    return result

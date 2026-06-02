from __future__ import annotations
from typing import Any
import requests
from tools._shared import TIMEOUT, err


def get_github_trending(topic: str = "machine-learning", language: str = "", since: str = "daily") -> dict[str, Any]:
    try:
        since_map = {"daily": "d", "weekly": "w", "monthly": "m"}
        date_range = since_map.get(since, "d")
        params: dict[str, Any] = {
            "q": f"topic:{topic}" if topic else "stars:>100",
            "sort": "stars",
            "order": "desc",
            "per_page": 10,
        }
        if language:
            params["q"] += f" language:{language}"
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        resp = requests.get("https://api.github.com/search/repositories", params=params, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        repos = resp.json().get("items", [])
        items = []
        for r in repos[:10]:
            items.append({
                "title": r.get("full_name", ""),
                "url": r.get("html_url", ""),
                "source": "github.com",
                "summary": (r.get("description") or "") + f" | ⭐{r.get('stargazers_count', 0)} | Lang: {r.get('language') or 'N/A'}",
                "stars": r.get("stargazers_count", 0),
            })
        return {"tool": "get_github_trending", "topic": topic, "language": language, "items": items}
    except Exception as exc:
        return err("get_github_trending", exc)

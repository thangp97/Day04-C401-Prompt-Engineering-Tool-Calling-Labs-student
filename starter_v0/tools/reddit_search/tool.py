from __future__ import annotations
from typing import Any
import requests
from tools._shared import TIMEOUT, err


def search_reddit(query: str = "", subreddit: str = "", limit: int = 5, sort: str = "relevance") -> dict[str, Any]:
    try:
        base = f"https://www.reddit.com/r/{subreddit}/search.json" if subreddit else "https://www.reddit.com/search.json"
        params: dict[str, Any] = {"q": query, "limit": min(limit, 25), "sort": sort, "type": "link"}
        if subreddit:
            params["restrict_sr"] = "true"
        headers = {"User-Agent": "AI20k-Research-Agent/1.0 (educational lab)"}
        resp = requests.get(base, params=params, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        children = resp.json().get("data", {}).get("children", [])
        items = []
        for child in children[:limit]:
            p = child.get("data", {})
            items.append({
                "title": p.get("title", ""),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "source": f"r/{p.get('subreddit', 'reddit')}",
                "summary": (p.get("selftext") or p.get("title", ""))[:400],
                "score": p.get("score", 0),
            })
        return {"tool": "search_reddit", "query": query, "subreddit": subreddit, "sort": sort, "items": items}
    except Exception as exc:
        return err("search_reddit", exc)

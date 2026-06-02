from __future__ import annotations
from typing import Any
from tools._shared import err


def summarize_items(items: list[dict] = [], max_points: int = 5, headline: str = "") -> dict[str, Any]:
    try:
        if not items:
            return {"tool": "summarize_items", "error": "ValueError", "message": "items list is empty"}
        points = []
        for item in items[:max_points]:
            title = item.get("title", "").strip()
            summary = item.get("summary", "").strip()
            source = item.get("source", "").strip()
            url = item.get("url", "").strip()
            if title:
                text = f"**{title}**"
                if summary:
                    short = summary[:200].rstrip()
                    if len(summary) > 200:
                        short += "..."
                    text += f" — {short}"
                if source:
                    text += f" ({source})"
                if url:
                    text += f" [{url}]"
                points.append(text)
        body = "\n\n".join(f"{i+1}. {p}" for i, p in enumerate(points))
        if headline:
            body = f"## {headline}\n\n{body}"
        return {
            "tool": "summarize_items",
            "headline": headline,
            "point_count": len(points),
            "summary": body,
            "items": [{"title": headline or "Summary", "url": "", "source": "summarize", "summary": body}],
        }
    except Exception as exc:
        return err("summarize_items", exc)

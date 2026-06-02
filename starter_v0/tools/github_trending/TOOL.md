---
name: github_trending
description: Find trending/popular GitHub repositories by topic. Useful for discovering popular AI/ML repos and open-source projects.
api: GitHub REST API (no key required, 60 req/hour unauthenticated)
args:
  topic: GitHub topic tag (e.g. "machine-learning", "llm", "ai-agents"). Default: "machine-learning"
  language: filter by programming language (e.g. "python", "typescript"). Default: any
  since: daily | weekly | monthly (default daily)
---

No API key required. GitHub unauthenticated: 60 requests/hour.

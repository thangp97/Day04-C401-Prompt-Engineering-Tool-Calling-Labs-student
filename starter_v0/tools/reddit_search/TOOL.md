---
name: reddit_search
description: Search Reddit posts by keyword. Useful for community discussion, opinions, and informal signals on a topic.
api: Reddit public JSON API (no key required)
args:
  query: search keyword
  subreddit: optional subreddit name (without r/)
  limit: number of results (default 5, max 25)
  sort: relevance | new | top | hot (default relevance)
---

No API key required. Reddit rate-limits unauthenticated requests; use sparingly.

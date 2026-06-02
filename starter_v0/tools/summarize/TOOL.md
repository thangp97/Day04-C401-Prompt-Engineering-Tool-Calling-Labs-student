---
name: summarize
description: Condense a list of items (from lookup/timeline/papers/etc.) into a numbered briefing with title, excerpt, and source. Use after gathering data to create a clean digest before formatting or sending.
api: None (pure Python, no external call)
args:
  items: list of item dicts (each with title, url, source, summary)
  max_points: max number of points in summary (default 5)
  headline: optional headline for the digest
---

No API call. Input items come from other tools (lookup, timeline, papers, fetch, etc.).
Use this before `format` or `send` to condense large result sets.

from __future__ import annotations
from typing import Any
import requests
from tools._shared import TIMEOUT, err


def translate_text(text: str = "", target_lang: str = "vi", source_lang: str = "en") -> dict[str, Any]:
    try:
        if not text.strip():
            return {"tool": "translate_text", "error": "ValueError", "message": "text is empty"}
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:500], "langpair": f"{source_lang}|{target_lang}"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        return {
            "tool": "translate_text",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "original": text[:500],
            "translated": translated,
            "items": [{"title": "Translation", "url": "", "source": "mymemory.translated.net", "summary": translated}],
        }
    except Exception as exc:
        return err("translate_text", exc)

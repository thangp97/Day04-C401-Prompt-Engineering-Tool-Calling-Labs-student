from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from providers.base import Provider, ToolCall
from tools import TOOL_FUNCTIONS


@dataclass
class AgentRun:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


class ResearchAgent:
    def __init__(
        self,
        provider: Provider,
        *,
        system_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> None:
        self.provider = provider
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.model = model

    def run(self, user_messages: list[dict[str, str]], *, tool_choice: Any | None = None) -> AgentRun:
        messages = [{"role": "system", "content": self.system_prompt}, *user_messages]
        response = self.provider.complete(
            messages,
            self.tools,
            model=self.model,
            temperature=0.0,
            tool_choice=tool_choice,
        )
        results: list[dict[str, Any]] = []
        for call in response.tool_calls:
            func = TOOL_FUNCTIONS.get(call.name)
            if not func:
                results.append({"tool": call.name, "error": "unknown_tool"})
                continue
            try:
                result = func(**call.args)
            except Exception as exc:  # keep eval robust; failures are evidence
                result = {"error": type(exc).__name__, "message": str(exc)}
            results.append({"tool": call.name, "args": call.args, "result": result})

        summary_text = response.text

        # Second pass: send tool results back to get a text summary
        if response.tool_calls and results and response.raw:
            try:
                raw_msg = response.raw.choices[0].message
                second_messages = list(messages)
                assistant_dict: dict[str, Any] = {"role": "assistant", "content": raw_msg.content or ""}
                if raw_msg.tool_calls:
                    assistant_dict["tool_calls"] = [
                        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in raw_msg.tool_calls
                    ]
                second_messages.append(assistant_dict)
                for tc, res in zip(raw_msg.tool_calls or [], results):
                    second_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(res.get("result", res), ensure_ascii=False),
                    })
                summary_response = self.provider.complete(second_messages, tools=None, model=self.model, temperature=0.0)
                if summary_response.text:
                    summary_text = summary_response.text
            except Exception:
                pass

        return AgentRun(text=summary_text, tool_calls=response.tool_calls, tool_results=results)

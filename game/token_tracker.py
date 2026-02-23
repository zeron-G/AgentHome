"""Token usage tracking and session limit enforcement."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import config


@dataclass
class AgentTokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class TokenTracker:
    def __init__(self, session_limit: int = config.DEFAULT_TOKEN_LIMIT):
        self.session_limit = session_limit
        self._per_agent: dict[str, AgentTokenUsage] = {}
        self._total = AgentTokenUsage()
        self._paused = False
        self._lock = asyncio.Lock()

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def total_tokens(self) -> int:
        return self._total.total

    async def record(self, agent_id: str, usage_metadata) -> int:
        """Record token usage from a Gemini response. Returns tokens used."""
        prompt_t = getattr(usage_metadata, "prompt_token_count", 0) or 0
        completion_t = getattr(usage_metadata, "candidates_token_count", 0) or 0
        return await self.record_raw(agent_id, prompt_t, completion_t)

    async def record_raw(self, agent_id: str, prompt_tokens: int, completion_tokens: int) -> int:
        """Record token usage from raw counts (for OpenAI-compatible responses)."""
        total_t = prompt_tokens + completion_tokens

        async with self._lock:
            if agent_id not in self._per_agent:
                self._per_agent[agent_id] = AgentTokenUsage()
            self._per_agent[agent_id].prompt_tokens += prompt_tokens
            self._per_agent[agent_id].completion_tokens += completion_tokens
            self._total.prompt_tokens += prompt_tokens
            self._total.completion_tokens += completion_tokens

            if self._total.total >= self.session_limit and not self._paused:
                self._paused = True

        return total_t

    def resume(self, new_limit: int | None = None):
        if new_limit is not None and new_limit > 0:
            self.session_limit = new_limit
        self._paused = False

    def set_limit(self, new_limit: int):
        self.session_limit = new_limit
        if self._total.total < new_limit:
            self._paused = False

    def snapshot(self) -> dict:
        return {
            "total_tokens_used": self._total.total,
            "prompt_tokens": self._total.prompt_tokens,
            "completion_tokens": self._total.completion_tokens,
            "limit": self.session_limit,
            "paused": self._paused,
            "usage_pct": round(self._total.total / max(1, self.session_limit) * 100, 1),
            "per_agent": {
                aid: {"total": u.total, "prompt": u.prompt_tokens, "completion": u.completion_tokens}
                for aid, u in self._per_agent.items()
            },
        }

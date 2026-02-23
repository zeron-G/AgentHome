"""Base LLM agent: Gemini client wrapper with history and token tracking."""
from __future__ import annotations

import json
import logging
from typing import Any, Optional, Type

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

import config
from game.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class BaseAgent:
    """Wraps Gemini client with history management and token tracking."""

    def __init__(self, agent_id: str, token_tracker: TokenTracker):
        self.agent_id = agent_id
        self.token_tracker = token_tracker
        self._api_key: str = config.GEMINI_API_KEY
        self._client: Optional[genai.Client] = None  # lazy init

    def _get_client(self) -> genai.Client:
        """Return (or create) the Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def update_api_key(self, new_key: str):
        """Hot-reload the API key; forces client re-creation on next call."""
        self._api_key = new_key
        self._client = None

    async def call_llm(
        self,
        system_prompt: str,
        context_message: str,
        history: list[dict],
        response_schema: Type[BaseModel],
    ) -> Optional[BaseModel]:
        """Call Gemini with conversation history. Returns parsed Pydantic model or None."""

        # Build contents list from history + current context
        contents: list[genai_types.Content] = []
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=turn["text"])],
                )
            )

        # Add current context as the latest user message
        contents.append(
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=context_message)],
            )
        )

        gen_config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=config.LLM_TEMPERATURE,
            max_output_tokens=config.LLM_MAX_TOKENS,
        )

        try:
            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=config.MODEL_NAME,
                contents=contents,
                config=gen_config,
            )

            # Track token usage
            if response.usage_metadata:
                await self.token_tracker.record(self.agent_id, response.usage_metadata)

            # Parse response
            text = response.text
            if not text:
                return None

            data = json.loads(text)
            return response_schema(**data)

        except json.JSONDecodeError as e:
            logger.warning(f"[{self.agent_id}] JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"[{self.agent_id}] LLM call failed: {e}")
            return None

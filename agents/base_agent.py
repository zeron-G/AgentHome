"""Base LLM agent: supports Gemini (cloud) and any OpenAI-compatible local server."""
from __future__ import annotations

import json
import logging
import re
from typing import Optional, Type

from pydantic import BaseModel

import config
from game.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class BaseAgent:
    """Wraps LLM clients with history management and token tracking.

    Supports two providers (switchable at runtime via config):
    - "gemini"  → Google Gemini via google-genai SDK (structured JSON output)
    - "local"   → Any OpenAI-compatible server (Ollama, LM Studio, llama.cpp, vLLM, ...)
                  via the openai Python package
    """

    def __init__(self, agent_id: str, token_tracker: TokenTracker):
        self.agent_id = agent_id
        self.token_tracker = token_tracker
        self._api_key: str = config.GEMINI_API_KEY
        self._gemini_client = None   # lazy: google.genai.Client
        self._local_client = None    # lazy: openai.AsyncOpenAI

    # ── Client lifecycle ──────────────────────────────────────────────────────

    def _get_gemini_client(self):
        if self._gemini_client is None:
            from google import genai
            self._gemini_client = genai.Client(api_key=self._api_key)
        return self._gemini_client

    def _get_local_client(self):
        if self._local_client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise RuntimeError(
                    "openai 包未安装，请运行: pip install openai>=1.0.0"
                )
            self._local_client = AsyncOpenAI(
                base_url=config.LOCAL_LLM_BASE_URL,
                api_key="local",   # most local servers ignore the key
            )
        return self._local_client

    def update_api_key(self, new_key: str):
        """Hot-reload Gemini API key; forces client re-creation on next call."""
        self._api_key = new_key
        self._gemini_client = None

    def reset_local_client(self):
        """Force recreation of the local OpenAI client (after URL/model change)."""
        self._local_client = None

    # ── Main entry point ──────────────────────────────────────────────────────

    async def call_llm(
        self,
        system_prompt: str,
        context_message: str,
        history: list[dict],
        response_schema: Type[BaseModel],
    ) -> Optional[BaseModel]:
        """Dispatch to Gemini or local LLM based on current config."""
        if config.LLM_PROVIDER == "local":
            return await self._call_local(system_prompt, context_message, history, response_schema)
        else:
            return await self._call_gemini(system_prompt, context_message, history, response_schema)

    # ── Gemini (cloud) ────────────────────────────────────────────────────────

    async def _call_gemini(
        self,
        system_prompt: str,
        context_message: str,
        history: list[dict],
        response_schema: Type[BaseModel],
    ) -> Optional[BaseModel]:
        from google.genai import types as genai_types

        contents: list[genai_types.Content] = []
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=turn["text"])],
            ))
        contents.append(genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=context_message)],
        ))

        gen_config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=config.LLM_TEMPERATURE,
            max_output_tokens=config.LLM_MAX_TOKENS,
        )

        try:
            client = self._get_gemini_client()
            response = await client.aio.models.generate_content(
                model=config.MODEL_NAME,
                contents=contents,
                config=gen_config,
            )

            if response.usage_metadata:
                await self.token_tracker.record(self.agent_id, response.usage_metadata)

            # Prefer response.parsed (native structured output, already a Pydantic model)
            if getattr(response, "parsed", None) is not None:
                return response.parsed

            text = response.text
            if not text:
                return None

            data = json.loads(text)
            return response_schema(**data)

        except json.JSONDecodeError as e:
            logger.warning(f"[{self.agent_id}][gemini] JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"[{self.agent_id}][gemini] LLM call failed: {e}")
            return None

    # ── Local OpenAI-compatible server ────────────────────────────────────────

    async def _call_local(
        self,
        system_prompt: str,
        context_message: str,
        history: list[dict],
        response_schema: Type[BaseModel],
    ) -> Optional[BaseModel]:
        # Append JSON schema to system prompt so the model knows the format
        schema_json = json.dumps(
            response_schema.model_json_schema(), ensure_ascii=False, indent=2
        )
        full_system = (
            system_prompt
            + f"\n\n【输出格式】必须严格按照以下 JSON Schema 返回合法 JSON，不要包含任何解释文字：\n{schema_json}"
        )

        # Build OpenAI-style messages
        messages: list[dict] = [{"role": "system", "content": full_system}]
        for turn in history:
            role = "user" if turn["role"] == "user" else "assistant"
            messages.append({"role": role, "content": turn["text"]})
        messages.append({"role": "user", "content": context_message})

        try:
            client = self._get_local_client()
            response = await client.chat.completions.create(
                model=config.LOCAL_LLM_MODEL,
                messages=messages,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.LLM_MAX_TOKENS,
                # response_format={"type": "json_object"}, 最高兼容性
            )

            # Track tokens (OpenAI usage format)
            usage = getattr(response, "usage", None)
            if usage:
                await self.token_tracker.record_raw(
                    self.agent_id,
                    prompt_tokens=getattr(usage, "prompt_tokens", 0),
                    completion_tokens=getattr(usage, "completion_tokens", 0),
                )

            text = response.choices[0].message.content
            if not text:
                return None

            # Strip markdown code fences (some models wrap output in ```json ... ```)
            text = _strip_code_fences(text)

            data = json.loads(text)
            return response_schema(**data)

        except json.JSONDecodeError as e:
            logger.warning(f"[{self.agent_id}][local] JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"[{self.agent_id}][local] LLM call failed: {e}")
            return None


def _strip_code_fences(text: str) -> str:
    """Remove markdown ```json ... ``` wrappers that some models add."""
    text = text.strip()
    match = re.match(r"^```(?:json)?\s*\n?([\s\S]*?)\n?```$", text)
    if match:
        return match.group(1).strip()
    return text

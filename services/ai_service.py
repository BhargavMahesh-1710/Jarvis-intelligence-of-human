"""
AI Intelligence Service for MAHI JARVIS Mk-VIII.
Provides dedicated AI question answering and real-time knowledge synthesis
using the official OpenAI Python SDK (Responses API and Chat Completions fallback).
Zero OS/shell execution capability - strictly informational.
"""

import os
import re
from typing import Optional

try:
    from openai import (
        OpenAI,
        APIError,
        APIConnectionError,
        RateLimitError,
        AuthenticationError,
    )
except ImportError:
    OpenAI = None
    APIError = Exception
    APIConnectionError = Exception
    RateLimitError = Exception
    AuthenticationError = Exception

from config import OPENAI_API_KEY, USER_NAME, ASSISTANT_NAME
from services.tts_service import clean_text_for_speech

JARVIS_SYSTEM_INSTRUCTION = (
    f"You are {ASSISTANT_NAME}, an advanced, calm, polite, and highly capable personal AI assistant "
    f"created for {USER_NAME}. "
    f"You provide clear, technically accurate, student-friendly explanations and direct answers. "
    f"Keep answers concise, direct, and well-structured. "
    f"Do not invent facts. Maintain the calm, courteous persona of JARVIS at all times. "
    f"You have no system execution authority; your purpose is knowledge synthesis and query resolution."
)

OFFLINE_FALLBACK_MESSAGE = (
    "Sir, my online intelligence service is currently unavailable. I can still perform my local JARVIS commands."
)
NOT_CONFIGURED_MESSAGE = "Online AI intelligence is not configured yet."


class AIService:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = (api_key or OPENAI_API_KEY or "").strip()
        self.model = model
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> Optional[OpenAI]:
        key = (os.getenv("OPENAI_API_KEY") or self.api_key or OPENAI_API_KEY or "").strip()
        if not key:
            return None

        if self._client is None or getattr(self._client, "api_key", None) != key:
            if OpenAI is None:
                return None
            self._client = OpenAI(api_key=key)
        return self._client

    def is_configured(self) -> bool:
        """Returns True if an OpenAI API key is present."""
        key = (os.getenv("OPENAI_API_KEY") or self.api_key or OPENAI_API_KEY or "").strip()
        return bool(key)

    def ask_ai(self, prompt: str, context: Optional[str] = None, is_current: bool = False) -> str:
        """
        Synthesizes an informational response using OpenAI.
        Falls back cleanly to offline JARVIS messages if key is missing or API is unavailable.
        """
        # 1. Configuration check
        if not self.is_configured():
            return NOT_CONFIGURED_MESSAGE

        client = self._get_client()
        if not client:
            return NOT_CONFIGURED_MESSAGE

        # 2. Prepare instructions and prompt payload
        instructions = JARVIS_SYSTEM_INSTRUCTION
        if is_current:
            instructions += (
                "\nYou are synthesizing current, real-time facts based on verified web search results provided. "
                "Synthesize the answer accurately, directly, and concisely without speculative claims."
            )

        user_content = prompt
        if context:
            user_content = f"Question: {prompt}\n\nVerified Context:\n{context}\n\nPlease summarize and explain clearly."

        # 3. Attempt Responses API first, then chat completions
        raw_output = None
        try:
            # Primary: OpenAI Responses API
            if hasattr(client, "responses"):
                try:
                    response = client.responses.create(
                        model=self.model,
                        input=user_content,
                        instructions=instructions,
                    )
                    if hasattr(response, "output_text") and response.output_text:
                        raw_output = response.output_text.strip()
                    elif hasattr(response, "output") and response.output:
                        raw_output = str(response.output).strip()
                except Exception as resp_err:
                    # If Responses API fails (e.g. model or endpoint), fall through to chat completions
                    print(f"[AIService] Responses API attempt error: {resp_err}. Falling back to chat completions.")

            # Fallback: Chat Completions API
            if not raw_output and hasattr(client, "chat"):
                messages = [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": user_content}
                ]
                chat_res = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=20
                )
                if chat_res.choices and chat_res.choices[0].message:
                    raw_output = (chat_res.choices[0].message.content or "").strip()

            if not raw_output:
                return OFFLINE_FALLBACK_MESSAGE

            return raw_output

        except (APIError, APIConnectionError, RateLimitError, AuthenticationError) as api_err:
            print(f"[AIService] OpenAI API error: {api_err}")
            return OFFLINE_FALLBACK_MESSAGE
        except Exception as e:
            print(f"[AIService] Unexpected error: {e}")
            return OFFLINE_FALLBACK_MESSAGE

    def get_speech_friendly_text(self, text: str) -> str:
        """Sanitizes text for clean, natural speech synthesis."""
        return clean_text_for_speech(text)


ai_service = AIService()

"""Provider adapters. Provider-specific SDK details stay out of domain logic."""

from __future__ import annotations

import json
import os
import re

from .config import API_KEY_VARIABLES


def _decode_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    result = json.loads(cleaned)
    if not isinstance(result, dict):
        raise ValueError("Model response was not a JSON object.")
    return result


class LLMProvider:
    def generate_json(self, model: str, prompt: str) -> dict:
        raise NotImplementedError


class GeminiProvider(LLMProvider):
    def generate_json(self, model: str, prompt: str) -> dict:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ[API_KEY_VARIABLES["Google Gemini"]])
        response = client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
        )
        if not response.text:
            raise ValueError("Gemini returned an empty response.")
        return _decode_json(response.text)


class OpenAIProvider(LLMProvider):
    def generate_json(self, model: str, prompt: str) -> dict:
        from openai import OpenAI

        response = OpenAI(api_key=os.environ[API_KEY_VARIABLES["OpenAI"]]).chat.completions.create(
            model=model, temperature=0.2, response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response.")
        return _decode_json(content)


def get_provider(name: str) -> LLMProvider:
    if name == "Google Gemini":
        return GeminiProvider()
    if name == "OpenAI":
        return OpenAIProvider()
    raise ValueError(f"Unsupported provider: {name}")

# agent/mistral_client.py
import time
from typing import List, Dict, Any, Optional
from mistralai import Mistral
from config import MISTRAL_API_KEYS

class MistralClientPool:
    def __init__(self, api_keys: List[str]):
        if not api_keys:
            raise ValueError("No Mistral API keys provided.")
        self.api_keys = api_keys
        self.current_index = 0
        self.clients = [Mistral(api_key=key) for key in api_keys]

    def _rotate_key(self):
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        print(f"[Mistral] Rotated to API key index {self.current_index}")

    def chat(self, messages: List[Dict[str, str]], model: str = "mistral-large-latest", **kwargs) -> str:
        """
        Send a chat completion request with automatic key fallback.
        """
        errors = []
        for attempt in range(len(self.api_keys)):
            client = self.clients[self.current_index]
            try:
                response = client.chat.complete(
                    model=model,
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content
            except Exception as e:
                error_msg = f"Key {self.current_index} failed: {e}"
                errors.append(error_msg)
                print(f"[Mistral] {error_msg}")
                self._rotate_key()
                time.sleep(1)  # Brief pause before retry
        raise Exception(f"All Mistral API keys failed. Errors: {errors}")

    def chat_stream(self, messages: List[Dict[str, str]], model: str = "mistral-large-latest", **kwargs):
        """
        Streaming version (generator) with fallback.
        """
        errors = []
        for attempt in range(len(self.api_keys)):
            client = self.clients[self.current_index]
            try:
                stream = client.chat.stream(
                    model=model,
                    messages=messages,
                    **kwargs
                )
                for chunk in stream:
                    if chunk.data.choices[0].delta.content:
                        yield chunk.data.choices[0].delta.content
                return
            except Exception as e:
                errors.append(f"Key {self.current_index} failed: {e}")
                self._rotate_key()
                time.sleep(1)
        raise Exception(f"All keys failed during streaming. Errors: {errors}")

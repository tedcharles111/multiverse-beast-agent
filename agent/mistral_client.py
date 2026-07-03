import time
import requests
import json
from typing import List, Dict, Optional
from config import MISTRAL_API_KEYS

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Priority order of models to try
MODELS = [
    "mistral-large-2512",
    "mistral-large-latest",
    "pixtral-large-latest",
    "devstral-latest",
    "mistral-vibe-cli-latest",
]

class MistralClientPool:
    def __init__(self, api_keys: List[str]):
        if not api_keys:
            raise ValueError("No Mistral API keys provided.")
        self.api_keys = api_keys
        self.current_key_index = 0
        self.current_model_index = 0

    def _rotate_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"[Mistral] Rotated to API key index {self.current_key_index}")

    def _rotate_model(self):
        self.current_model_index = (self.current_model_index + 1) % len(MODELS)
        print(f"[Mistral] Rotated to model {MODELS[self.current_model_index]}")

    def _get_headers(self, key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages: List[Dict[str, str]], temperature=0.2, max_tokens=None, **kwargs) -> str:
        errors = []
        # Try each model with each key
        for model_attempt in range(len(MODELS)):
            model = MODELS[self.current_model_index]
            for key_attempt in range(len(self.api_keys)):
                key = self.api_keys[self.current_key_index]
                headers = self._get_headers(key)
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    **kwargs
                }
                if max_tokens:
                    payload["max_tokens"] = max_tokens
                try:
                    response = requests.post(
                        MISTRAL_API_URL,
                        json=payload,
                        headers=headers,
                        timeout=(30, 180)
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_msg = f"Model {model}, key {self.current_key_index} failed: HTTP {response.status_code} - {response.text}"
                        errors.append(error_msg)
                        print(f"[Mistral] {error_msg}")
                except Exception as e:
                    error_msg = f"Model {model}, key {self.current_key_index} exception: {e}"
                    errors.append(error_msg)
                    print(f"[Mistral] {error_msg}")
                self._rotate_key()
                time.sleep(1)
            self._rotate_model()
        raise Exception(f"All models and keys failed. Errors: {errors}")

    def deep_chat(self, messages: List[Dict[str, str]]) -> str:
        """Extended reasoning with higher token limit and lower temperature."""
        return self.chat(messages, temperature=0.1, max_tokens=4096)

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs):
        # Streaming is not needed for the current API, but kept for compatibility
        raise NotImplementedError("Streaming not implemented")

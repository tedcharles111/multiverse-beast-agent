import time
import requests
import json
from typing import List, Dict, Optional
from config import MISTRAL_API_KEYS

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

class MistralClientPool:
    def __init__(self, api_keys: List[str]):
        if not api_keys:
            raise ValueError("No Mistral API keys provided.")
        self.api_keys = api_keys
        self.current_index = 0

    def _rotate_key(self):
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        print(f"[Mistral] Rotated to API key index {self.current_index}")

    def _get_headers(self, key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages: List[Dict[str, str]], model: str = "mistral-large-latest", **kwargs) -> str:
        errors = []
        for attempt in range(len(self.api_keys) * 2):
            key = self.api_keys[self.current_index]
            headers = self._get_headers(key)
            payload = {
                "model": model,
                "messages": messages,
                **kwargs
            }
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
                    error_msg = f"Key {self.current_index} failed: HTTP {response.status_code} - {response.text}"
                    errors.append(error_msg)
                    print(f"[Mistral] {error_msg}")
            except Exception as e:
                error_msg = f"Key {self.current_index} failed: {e}"
                errors.append(error_msg)
                print(f"[Mistral] {error_msg}")
            wait = 2 ** (attempt % 2)
            time.sleep(wait)
            if attempt % 2 == 1:
                self._rotate_key()
        raise Exception(f"All Mistral API keys failed after retries. Errors: {errors}")

    def deep_chat(self, messages: List[Dict[str, str]], model: str = "mistral-large-latest") -> str:
        """
        Engage in deeper reasoning with higher token limit and lower temperature.
        """
        return self.chat(messages, model=model, temperature=0.1, max_tokens=4096)

    def chat_stream(self, messages: List[Dict[str, str]], model: str = "mistral-large-latest", **kwargs):
        errors = []
        for attempt in range(len(self.api_keys) * 2):
            key = self.api_keys[self.current_index]
            headers = self._get_headers(key)
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                **kwargs
            }
            try:
                response = requests.post(
                    MISTRAL_API_URL,
                    json=payload,
                    headers=headers,
                    stream=True,
                    timeout=(30, 180)
                )
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    delta = chunk["choices"][0]["delta"]
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                                except json.JSONDecodeError:
                                    continue
                    return
                else:
                    error_msg = f"Key {self.current_index} failed: HTTP {response.status_code} - {response.text}"
                    errors.append(error_msg)
                    print(f"[Mistral] {error_msg}")
            except Exception as e:
                error_msg = f"Key {self.current_index} failed: {e}"
                errors.append(error_msg)
                print(f"[Mistral] {error_msg}")
            wait = 2 ** (attempt % 2)
            time.sleep(wait)
            if attempt % 2 == 1:
                self._rotate_key()
        raise Exception(f"All keys failed during streaming. Errors: {errors}")

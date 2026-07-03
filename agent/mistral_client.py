import time, requests, json
from typing import List, Dict, Optional
from config import MISTRAL_API_KEYS

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

MODELS = [
    "mistral-large-2512",
    "mistral-large-latest",
    "pixtral-large-latest",
    "codestral-latest",
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

    def _rotate_model(self):
        self.current_model_index = (self.current_model_index + 1) % len(MODELS)

    def chat(self, messages, temperature=0.2, max_tokens=1024, **kwargs):
        errors = []
        for _ in range(len(MODELS)):
            model = MODELS[self.current_model_index]
            for _ in range(len(self.api_keys)):
                key = self.api_keys[self.current_key_index]
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
                try:
                    resp = requests.post(MISTRAL_API_URL, json=payload, headers=headers, timeout=(10, 60))
                    if resp.status_code == 200:
                        return resp.json()["choices"][0]["message"]["content"]
                    errors.append(f"{model} key {self.current_key_index} HTTP {resp.status_code}")
                except Exception as e:
                    errors.append(f"{model} key {self.current_key_index} {e}")
                self._rotate_key()
                time.sleep(0.5)
            self._rotate_model()
        raise Exception("All models/keys failed: " + "; ".join(errors))

    def deep_chat(self, messages):
        return self.chat(messages, temperature=0.1, max_tokens=2048)

    def chat_stream(self, messages, **kwargs):
        raise NotImplementedError("Streaming not implemented")

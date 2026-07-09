import time, requests, json
from typing import List, Dict, Optional
from config import MISTRAL_API_KEYS

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Priority order – exactly as requested
MODELS = [
    "mistral-code-agent-latest",
    "mistral-large-2512",
    "devstral-latest",
    "codestral-latest",
    "mistral-large-latest",
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

    def _get_headers(self, key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2,
             max_tokens: Optional[int] = 4096, **kwargs) -> str:
        errors = []
        # Try every model, every key (until first success)
        for _ in range(len(MODELS)):
            model = MODELS[self.current_model_index]
            for _ in range(len(self.api_keys)):
                key = self.api_keys[self.current_key_index]
                headers = self._get_headers(key)
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs
                }
                try:
                    resp = requests.post(MISTRAL_API_URL,
                                         json=payload,
                                         headers=headers,
                                         timeout=(30, 180))
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        msg = f"Model {model}, key {self.current_key_index}: HTTP {resp.status_code}"
                        errors.append(msg)
                        print(f"[Mistral] {msg}")
                except Exception as e:
                    msg = f"Model {model}, key {self.current_key_index}: {e}"
                    errors.append(msg)
                    print(f"[Mistral] {msg}")
                self._rotate_key()
                time.sleep(1)
            self._rotate_model()
        raise Exception("All models and keys failed: " + "; ".join(errors))

    def deep_chat(self, messages: List[Dict[str, str]]) -> str:
        """Extended reasoning with even larger context."""
        return self.chat(messages, temperature=0.1, max_tokens=8192)

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs):
        raise NotImplementedError("Streaming not implemented")

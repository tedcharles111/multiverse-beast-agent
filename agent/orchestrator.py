import json
from agent.mistral_client import MistralClientPool
from agent.prompts.system_prompts import ORCHESTRATOR_SYSTEM_PROMPT
from config import MISTRAL_API_KEYS

class Orchestrator:
    def __init__(self):
        self.client = MistralClientPool(MISTRAL_API_KEYS)
        self.history = [{"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT}]

    def plan_and_execute(self, prompt): 
        self.history.append({"role": "user", "content": prompt})
        resp = self.client.chat(self.history, temperature=0.2)
        self.history.append({"role": "assistant", "content": resp})
        return resp

    def plan_and_execute_deep(self, prompt): 
        self.history.append({"role": "user", "content": prompt})
        resp = self.client.deep_chat(self.history)
        self.history.append({"role": "assistant", "content": resp})
        return resp

    def generate_code(self, spec, ctx=""):
        msg = f"Context: {ctx}\n\nSpecification: {spec}\n\nGenerate the complete code."
        return self.client.chat([{"role":"system","content":ORCHESTRATOR_SYSTEM_PROMPT},{"role":"user","content":msg}], temperature=0.1)

    def self_improve(self, orig, prev):
        prompt = f"Original task: {orig}\nPrevious response:\n{prev}\n\nCritique and improve."
        return self.client.chat([{"role":"system","content":ORCHESTRATOR_SYSTEM_PROMPT},{"role":"user","content":prompt}], temperature=0.3)

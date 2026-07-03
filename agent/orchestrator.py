import json, re, logging
from typing import Dict, Any
from agent.mistral_client import MistralClientPool
from agent.prompts.system_prompts import ORCHESTRATOR_SYSTEM_PROMPT
from config import MISTRAL_API_KEYS

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.client = MistralClientPool(MISTRAL_API_KEYS)
        self.history = [{"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT}]
        self._tools = None

    def _get_tools(self):
        if self._tools is None:
            try:
                from agent.tools import advanced_tools
                self._tools = advanced_tools
            except Exception as e:
                logger.error(f"advanced_tools import failed: {e}")
                self._tools = False
        return self._tools if self._tools else None

    def _execute_tool(self, name: str, params: dict) -> str:
        tools = self._get_tools()
        if not tools:
            return "Deployment tools unavailable."
        func = getattr(tools, name, None)
        if not func:
            return f"Tool '{name}' not found."
        try:
            result = func(**params)
            return str(result)
        except Exception as e:
            return f"Tool '{name}' error: {str(e)}"

    def _extract_calls(self, text: str):
        pattern = r'<tool\s+name="([^"]+)"\s*>(.*?)</tool>'
        return re.findall(pattern, text, re.DOTALL)

    def plan_and_execute(self, prompt: str) -> str:
        self.history.append({"role": "user", "content": prompt})
        resp = self.client.chat(self.history, temperature=0.2)
        calls = self._extract_calls(resp)
        if not calls:
            self.history.append({"role": "assistant", "content": resp})
            return resp
        # Execute first tool call and append result to history
        tool_name, params_text = calls[0]
        params = {}
        for k, v in re.findall(r'(\w+)="([^"]*)"', params_text):
            params[k] = v
        tool_result = self._execute_tool(tool_name, params)
        final_output = f"{resp}\n\n[Tool execution result for {tool_name}]: {tool_result}"
        self.history.append({"role": "assistant", "content": resp})
        self.history.append({"role": "user", "content": f"Tool {tool_name} result: {tool_result}"})
        return final_output

    def plan_and_execute_deep(self, prompt: str) -> str:
        self.history.append({"role": "user", "content": prompt})
        resp = self.client.deep_chat(self.history)
        self.history.append({"role": "assistant", "content": resp})
        return resp

    def generate_code(self, spec: str, ctx: str = "") -> str:
        msg = f"Context: {ctx}\n\nSpecification: {spec}\n\nGenerate the complete code."
        return self.client.chat([{"role":"system","content":ORCHESTRATOR_SYSTEM_PROMPT},{"role":"user","content":msg}], temperature=0.1)

    def self_improve(self, orig: str, prev: str) -> str:
        prompt = f"Original task: {orig}\nPrevious response:\n{prev}\n\nCritique and improve."
        return self.client.chat([{"role":"system","content":ORCHESTRATOR_SYSTEM_PROMPT},{"role":"user","content":prompt}], temperature=0.3)

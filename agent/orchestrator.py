import json, re, logging
from typing import Dict, Any
from agent.mistral_client import MistralClientPool
from agent.prompts.system_prompts import ORCHESTRATOR_SYSTEM_PROMPT
from config import MISTRAL_API_KEYS

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.client = MistralClientPool(MISTRAL_API_KEYS)
        self.conversation_history = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT}
        ]
        # Tools will be imported on demand

    def _import_tools(self):
        """Lazy import to avoid startup crashes."""
        try:
            from agent.tools import advanced_tools
            return advanced_tools
        except Exception as e:
            logger.error(f"Failed to import advanced_tools: {e}")
            return None

    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        adv = self._import_tools()
        if not adv:
            return "Advanced tools unavailable."
        func = getattr(adv, tool_name, None)
        if not func:
            return f"Tool '{tool_name}' not found."
        try:
            result = func(**params)
            return str(result)
        except Exception as e:
            return f"Tool '{tool_name}' error: {str(e)}"

    def _extract_tool_calls(self, text: str):
        """Find <tool name="...">...</tool> blocks."""
        pattern = r'<tool\s+name="([^"]+)"\s*>(.*?)</tool>'
        return re.findall(pattern, text, re.DOTALL)

    def add_user_message(self, content: str):
        self.conversation_history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.conversation_history.append({"role": "assistant", "content": content})

    def plan_and_execute(self, user_request: str, max_turns=4) -> str:
        self.add_user_message(user_request)
        for turn in range(max_turns):
            response = self.client.chat(self.conversation_history, temperature=0.2)
            self.add_assistant_message(response)
            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                return response
            # Execute each tool and feed results back
            results = []
            for tool_name, params_text in tool_calls:
                params = {}
                for key, val in re.findall(r'(\w+)="([^"]*)"', params_text):
                    params[key] = val
                res = self._execute_tool(tool_name, params)
                results.append(f"<tool name=\"{tool_name}\"> result: {res}")
            feedback = "\n".join(results)
            self.conversation_history.append({"role": "user", "content": f"[Tool execution results]\n{feedback}\nContinue based on these results."})
        return response

    def plan_and_execute_deep(self, user_request: str) -> str:
        self.add_user_message(user_request)
        response = self.client.deep_chat(self.conversation_history)
        self.add_assistant_message(response)
        return response

    def self_improve(self, original_task: str, previous_response: str) -> str:
        prompt = f"""Original task: {original_task}

Your previous response:
{previous_response}

Please review your response. Identify any issues, missing details, or ways to enhance quality. Then provide an improved version."""
        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return self.client.chat(messages, temperature=0.3)

    def generate_code(self, specification: str, context: str = "") -> str:
        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"Context: {context}\n\nSpecification: {specification}\n\nGenerate the complete code."}
        ]
        return self.client.chat(messages, temperature=0.1)

# agent/orchestrator.py
import json
from typing import List, Dict, Any
from agent.mistral_client import MistralClientPool
from agent.prompts.system_prompts import ORCHESTRATOR_SYSTEM_PROMPT
from agent.tools import code_tools, deploy_tools, screenshot_tools
from config import MISTRAL_API_KEYS

class Orchestrator:
    def __init__(self):
        self.client = MistralClientPool(MISTRAL_API_KEYS)
        self.conversation_history = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT}
        ]
        self.tools = {
            "run_shell": code_tools.run_shell_command,
            "scaffold_react": code_tools.scaffold_react_project,
            "deploy_ssh": deploy_tools.deploy_via_ssh,
            "screenshot_desktop": screenshot_tools.capture_desktop_screen,
            "screenshot_web_element": screenshot_tools.capture_web_element,
            "screenshot_full_page": screenshot_tools.capture_full_page,
        }

    def add_user_message(self, content: str):
        self.conversation_history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.conversation_history.append({"role": "assistant", "content": content})

    def plan_and_execute(self, user_request: str) -> str:
        """
        Main entry point: given a user request, the agent plans and executes.
        """
        self.add_user_message(user_request)
        response = self.client.chat(self.conversation_history, temperature=0.2)
        self.add_assistant_message(response)

        # Simple tool-use parsing: if response contains a tool call (we can use function calling in production)
        # For brevity, we'll just return the response. In a full implementation, you'd parse tool calls.
        return response

    def generate_code(self, specification: str, context: str = "") -> str:
        """
        Generate code based on specification with UI/UX constraints.
        """
        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"Context: {context}\n\nSpecification: {specification}\n\nGenerate the complete code."}
        ]
        return self.client.chat(messages, temperature=0.1)

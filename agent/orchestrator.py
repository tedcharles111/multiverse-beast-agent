# agent/orchestrator.py
import json
import re
from typing import List, Dict, Any
from agent.mistral_client import MistralClientPool
from agent.prompts.system_prompts import ORCHESTRATOR_SYSTEM_PROMPT
from agent.tools import code_tools, deploy_tools, screenshot_tools
from agent.tools import advanced_tools
from config import MISTRAL_API_KEYS

class Orchestrator:
    def __init__(self):
        self.client = MistralClientPool(MISTRAL_API_KEYS)
        self.conversation_history = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT}
        ]
        # All available tools
        self.tools = {
            # Existing
            "run_shell": code_tools.run_shell_command,
            "force_command": code_tools.force_command,
            "scaffold_react": code_tools.scaffold_react_project,
            "deploy_ssh": deploy_tools.deploy_via_ssh,
            "screenshot_desktop": screenshot_tools.capture_desktop_screen,
            "screenshot_web_element": screenshot_tools.capture_web_element,
            "screenshot_full_page": screenshot_tools.capture_full_page,
            # Advanced
            "crawl_website": advanced_tools.crawl_website,
            "check_code_errors": advanced_tools.check_code_errors,
            "purchase_domain": advanced_tools.purchase_domain,
            "deploy_netlify": advanced_tools.deploy_netlify,
            "deploy_vercel": advanced_tools.deploy_vercel,
            "deploy_cloudflare": advanced_tools.deploy_cloudflare,
            "deploy_anonymous": advanced_tools.deploy_anonymous,
            "signup_and_get_api_key": advanced_tools.signup_and_get_api_key,
        }

    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Execute a registered tool and return its result as a string."""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found."
        try:
            result = self.tools[tool_name](**params)
            return str(result)
        except Exception as e:
            return f"Tool '{tool_name}' failed: {str(e)}"

    def add_user_message(self, content: str):
        self.conversation_history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.conversation_history.append({"role": "assistant", "content": content})

    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Find all <tool name="...">...</tool> blocks and return a list of calls."""
        pattern = r'<tool\s+name="([^"]+)"\s*>(.*?)</tool>'
        matches = re.findall(pattern, text, re.DOTALL)
        calls = []
        for tool_name, params_text in matches:
            params = {}
            # Simple param extraction: key="value"
            param_pattern = r'(\w+)="([^"]*)"'
            for key, val in re.findall(param_pattern, params_text):
                params[key] = val
            calls.append({"tool": tool_name, "params": params})
        return calls

    def plan_and_execute(self, user_request: str, max_turns: int = 5) -> str:
        """
        Main loop: sends user request to LLM, executes any tool calls found in the response,
        feeds results back, and continues until no more tool calls or max turns reached.
        """
        self.add_user_message(user_request)
        turn = 0
        while turn < max_turns:
            response = self.client.chat(self.conversation_history, temperature=0.2)
            self.add_assistant_message(response)
            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                # No more tools to execute, return final response
                return response
            # Execute tools and feed results back
            results = []
            for call in tool_calls:
                tool_name = call["tool"]
                params = call["params"]
                result = self._execute_tool(tool_name, params)
                results.append(f"Tool {tool_name} result: {result}")
            # Add tool results as a system message (or user message)
            feedback = "\n".join(results)
            self.conversation_history.append({"role": "user", "content": f"[Tool execution results]\n{feedback}\nContinue based on these results."})
            turn += 1
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

    def auto_fix_errors(self, project_path: str, max_attempts: int = 3) -> str:
        for attempt in range(max_attempts):
            errors = advanced_tools.check_code_errors(project_path)
            if errors.get("status") == "no errors detected":
                return "✅ All errors fixed. Your web app is error‑free."
            error_str = json.dumps(errors, indent=2)
            prompt = f"The following errors were found in the project at {project_path}:\n{error_str}\nPlease provide corrected file contents using <file path='...'>...</file> tags."
            response = self.client.chat([{"role": "user", "content": prompt}])
        return "❌ Could not fix all errors automatically. Manual review needed."

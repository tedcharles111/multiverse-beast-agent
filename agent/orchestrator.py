# agent/orchestrator.py
import json
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
        self.tools = {
            "run_shell": code_tools.run_shell_command,
            "force_command": code_tools.force_command,
            "scaffold_react": code_tools.scaffold_react_project,
            "deploy_ssh": deploy_tools.deploy_via_ssh,
            "screenshot_desktop": screenshot_tools.capture_desktop_screen,
            "screenshot_web_element": screenshot_tools.capture_web_element,
            "screenshot_full_page": screenshot_tools.capture_full_page,
            # New advanced tools
            "crawl_website": advanced_tools.crawl_website,
            "check_code_errors": advanced_tools.check_code_errors,
            "purchase_domain": advanced_tools.purchase_domain,
            "deploy_netlify": advanced_tools.deploy_netlify,
            "deploy_vercel": advanced_tools.deploy_vercel,
            "deploy_cloudflare": advanced_tools.deploy_cloudflare,
            "deploy_anonymous": advanced_tools.deploy_anonymous,
            "signup_and_get_api_key": advanced_tools.signup_and_get_api_key,
        }

    def add_user_message(self, content: str):
        self.conversation_history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.conversation_history.append({"role": "assistant", "content": content})

    def plan_and_execute(self, user_request: str) -> str:
        self.add_user_message(user_request)
        response = self.client.chat(self.conversation_history, temperature=0.2)
        self.add_assistant_message(response)
        return response

    def plan_and_execute_deep(self, user_request: str) -> str:
        """Execute a task with deeper reasoning (more tokens, lower temp)."""
        self.add_user_message(user_request)
        response = self.client.deep_chat(self.conversation_history)
        self.add_assistant_message(response)
        return response

    def self_improve(self, original_task: str, previous_response: str) -> str:
        """Critique and improve a previous answer."""
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
        """Iteratively fix code errors using the LLM."""
        for attempt in range(max_attempts):
            errors = advanced_tools.check_code_errors(project_path)
            if errors.get("status") == "no errors detected":
                return "✅ All errors fixed. Your web app is error‑free."
            error_str = json.dumps(errors, indent=2)
            prompt = f"The following errors were found in the project at {project_path}:\n{error_str}\nPlease provide corrected file contents using <file path='...'>...</file> tags."
            response = self.client.chat([{"role": "user", "content": prompt}])
        return "❌ Could not fix all errors automatically. Manual review needed."

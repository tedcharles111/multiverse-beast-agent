import re
import logging
from agent.mistral_client import MistralClientPool
from agent.prompts.system_prompts import ORCHESTRATOR_SYSTEM_PROMPT
from config import MISTRAL_API_KEYS

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.client = MistralClientPool(MISTRAL_API_KEYS)
        self.history = [{"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT}]
        self._tools = None

    # ------------------------------------------------------------------ #
    # Tool registry
    # ------------------------------------------------------------------ #
    def _get_tools(self):
        """Lazy-load every tool module and merge them into one dict."""
        if self._tools is not None:
            return self._tools

        registry = {}

        # --- code_tools (shell, scaffolding, force_command) ---
        try:
            from agent.tools import code_tools
            registry.update({
                "force_command": code_tools.force_command,
                "run_shell": code_tools.run_shell_command,
                "scaffold_react": code_tools.scaffold_react_project,
                "install_dependencies": code_tools.install_dependencies,
                "lint_code": code_tools.lint_code,
            })
        except Exception as e:
            logger.error(f"code_tools import failed: {e}")

        # --- advanced_tools (deployments, crawl, screenshots, domains) ---
        try:
            from agent.tools import advanced_tools
            registry.update({
                "crawl_website": advanced_tools.crawl_website,
                "screenshot_full_page": advanced_tools.screenshot_full_page,
                "check_code_errors": advanced_tools.check_code_errors,
                "purchase_domain": advanced_tools.purchase_domain,
                "deploy_netlify": advanced_tools.deploy_netlify,
                "deploy_vercel": advanced_tools.deploy_vercel,
                "deploy_cloudflare": advanced_tools.deploy_cloudflare,
                "deploy_anonymous": advanced_tools.deploy_anonymous,
                "signup_and_get_api_key": advanced_tools.signup_and_get_api_key,
            })
        except Exception as e:
            logger.error(f"advanced_tools import failed: {e}")

        # --- deploy_tools (SSH) ---
        try:
            from agent.tools import deploy_tools
            registry["deploy_ssh"] = deploy_tools.deploy_via_ssh
        except Exception as e:
            logger.error(f"deploy_tools import failed: {e}")

        # --- screenshot_tools (element + desktop) ---
        try:
            from agent.tools import screenshot_tools
            registry.update({
                "screenshot_web_element": screenshot_tools.capture_web_element,
                "screenshot_desktop": screenshot_tools.capture_desktop_screen,
            })
        except Exception as e:
            logger.error(f"screenshot_tools import failed: {e}")

        self._tools = registry
        logger.info(f"Loaded {len(registry)} tools: {list(registry.keys())}")
        return registry

    def _execute_tool(self, name: str, params: dict) -> str:
        tools = self._get_tools()
        func = tools.get(name)
        if not func:
            available = ", ".join(sorted(tools.keys())) or "(none loaded)"
            return f"Tool '{name}' not found. Available tools: {available}"
        try:
            result = func(**params)
            return str(result)
        except Exception as e:
            return f"Tool '{name}' error: {str(e)}"

    # ------------------------------------------------------------------ #
    # Parsing
    # ------------------------------------------------------------------ #
    def _extract_calls(self, text: str):
        """Find all <tool name="...">...</tool> blocks."""
        pattern = r'<tool\s+name="([^"]+)"\s*>(.*?)</tool>'
        return re.findall(pattern, text, re.DOTALL)

    def _parse_params(self, params_text: str) -> dict:
        """Parse key=\"value\" lines into a dict."""
        params = {}
        for k, v in re.findall(r'(\w+)\s*=\s*"([^"]*)"', params_text):
            params[k] = v.strip()
        return params

    # ------------------------------------------------------------------ #
    # Main entry points
    # ------------------------------------------------------------------ #
    def plan_and_execute(self, prompt: str) -> str:
        self.history.append({"role": "user", "content": prompt})
        resp = self.client.chat(self.history, temperature=0.2)
        calls = self._extract_calls(resp)

        if not calls:
            self.history.append({"role": "assistant", "content": resp})
            return resp

        # Execute EVERY tool call found (not just the first)
        results = []
        for tool_name, params_text in calls:
            params = self._parse_params(params_text)
            result = self._execute_tool(tool_name, params)
            results.append(f"[Tool {tool_name} result]: {result}")

        combined = "\n".join(results)
        final = f"{resp}\n\n{combined}"
        self.history.append({"role": "assistant", "content": resp})
        self.history.append({"role": "user", "content": combined})
        return final

    def plan_and_execute_deep(self, prompt: str) -> str:
        self.history.append({"role": "user", "content": prompt})
        resp = self.client.deep_chat(self.history)
        self.history.append({"role": "assistant", "content": resp})
        return resp

    def generate_code(self, spec: str, ctx: str = "") -> str:
        msg = f"Context: {ctx}\n\nSpecification: {spec}\n\nGenerate the complete code."
        return self.client.chat(
            [
                {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": msg},
            ],
            temperature=0.1,
        )

    def self_improve(self, orig: str, prev: str) -> str:
        prompt = f"Original task: {orig}\nPrevious response:\n{prev}\n\nCritique and improve."
        return self.client.chat(
            [
                {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

import re
import logging
import inspect
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
        if self._tools is not None:
            return self._tools

        registry = {}

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

        try:
            from agent.tools import deploy_tools
            registry["deploy_ssh"] = deploy_tools.deploy_via_ssh
        except Exception as e:
            logger.error(f"deploy_tools import failed: {e}")

        try:
            from agent.tools import screenshot_tools
            registry.update({
                "screenshot_web_element": screenshot_tools.capture_web_element,
                "screenshot_desktop": screenshot_tools.capture_desktop_screen,
            })
        except Exception as e:
            logger.error(f"screenshot_tools import failed: {e}")

        self._tools = registry
        logger.info(f"Loaded {len(registry)} tools: {sorted(registry.keys())}")
        return registry

    # ------------------------------------------------------------------ #
    # Parameter normalization
    # ------------------------------------------------------------------ #
    # Aliases the LLM commonly uses → canonical function param names
    PARAM_ALIASES = {
        "command": "cmd",
        "shell_command": "cmd",
        "shell": "cmd",
        "cwd": "cwd",
        "working_dir": "cwd",
        "working_directory": "cwd",
        "path": "project_path",
        "directory": "project_path",
        "dir": "project_path",
        "url": "url",
        "selector": "selector",
        "domain": "domain_name",
        "domain_name": "domain_name",
        "provider": "provider",
        "service": "service_name",
        "service_name": "service_name",
        "project": "project_name",
        "project_name": "project_name",
    }

    def _call_tool(self, func, params: dict, raw_text: str):
        """Call the tool with flexible argument handling."""
        try:
            sig = inspect.signature(func)
        except (TypeError, ValueError):
            return func(**params) if params else func(raw_text)

        # Normalize param names using aliases
        normalized = {}
        for k, v in params.items():
            key = k.strip().lower()
            normalized[self.PARAM_ALIASES.get(key, k)] = v

        # If no params were extracted but we have raw text, use it as the first param
        if not normalized and raw_text and raw_text.strip():
            positional = [
                name for name, p in sig.parameters.items()
                if p.default is inspect.Parameter.empty
                and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            if positional:
                normalized[positional[0]] = raw_text.strip()

        return func(**normalized)

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #
    def _execute_tool(self, name: str, params: dict, raw_text: str = "") -> str:
        tools = self._get_tools()
        func = tools.get(name)
        if not func:
            available = ", ".join(sorted(tools.keys())) or "(none loaded)"
            return f"Tool '{name}' not found. Available: {available}"
        try:
            result = self._call_tool(func, params, raw_text)
            return str(result)
        except Exception as e:
            return f"Tool '{name}' error: {str(e)}"

    # ------------------------------------------------------------------ #
    # Parsing
    # ------------------------------------------------------------------ #
    def _extract_calls(self, text: str):
        """Return list of (tool_name, inner_text)."""
        pattern = r'<tool\s+name="([^"]+)"\s*>(.*?)</tool>'
        return re.findall(pattern, text, re.DOTALL)

    def _parse_params(self, inner_text: str) -> dict:
        """Extract key=\"value\" pairs from inside the tool block."""
        return {
            k: v.strip()
            for k, v in re.findall(r'(\w+)\s*=\s*"([^"]*)"', inner_text)
        }

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

        results = []
        for tool_name, inner_text in calls:
            params = self._parse_params(inner_text)
            result = self._execute_tool(tool_name, params, raw_text=inner_text)
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

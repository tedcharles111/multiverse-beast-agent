# agent/tools/code_tools.py
import subprocess
import os
from typing import Tuple

def run_shell_command(cmd: str, cwd: str = None) -> Tuple[int, str, str]:
    """Execute shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr

def scaffold_react_project(project_name: str, template: str = "vite"):
    """Create a new React project with Vite."""
    return run_shell_command(f"npm create vite@latest {project_name} -- --template react")

def install_dependencies(project_path: str):
    """Run npm install."""
    return run_shell_command("npm install", cwd=project_path)

def lint_code(file_path: str):
    """Run eslint on a file."""
    return run_shell_command(f"npx eslint {file_path}")

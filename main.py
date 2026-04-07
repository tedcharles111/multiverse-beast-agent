# main.py
import argparse
from rich.console import Console
from rich.markdown import Markdown
from agent.orchestrator import Orchestrator

console = Console()

def main():
    parser = argparse.ArgumentParser(description="AI Coding Agent Orchestrator")
    parser.add_argument("--task", "-t", type=str, help="Task description")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    orchestrator = Orchestrator()

    if args.interactive:
        console.print("[bold green]AI Coding Agent[/] ready. Type 'exit' to quit.")
        while True:
            user_input = console.input("[bold cyan]You:[/] ")
            if user_input.lower() in ["exit", "quit"]:
                break
            with console.status("[bold yellow]Thinking...[/]"):
                response = orchestrator.plan_and_execute(user_input)
            console.print(Markdown(f"**Agent:** {response}"))
    elif args.task:
        with console.status("[bold yellow]Working on task...[/]"):
            response = orchestrator.plan_and_execute(args.task)
        console.print(Markdown(response))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

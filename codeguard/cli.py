import os
import keyring
from pathlib import Path
from codeguard.config import Config, load_config
from codeguard.llm import DeepSeekAdapter, MockLLM
from codeguard.tools import create_default_registry
from codeguard.governance import GuardrailEngine, HITLStateMachine
from codeguard.loop import Agent


def get_api_key() -> str:
    key = keyring.get_password("codeguard", "deepseek")
    if key:
        return key
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    raise RuntimeError("API key not found in keyring or DEEPSEEK_API_KEY environment variable")


def create_agent_from_config(config: Config, project_root: Path):
    api_key = get_api_key()
    llm = DeepSeekAdapter(api_key=api_key, config=config)
    tool_registry = create_default_registry()
    guardrail = GuardrailEngine()
    for rule in config.guardrails.custom_rules:
        guardrail.add_rule(rule.pattern, rule.risk_level, rule.description)
    hitl = HITLStateMachine(timeout=config.agent.hitl_timeout)
    return Agent(
        config=config,
        llm=llm,
        tool_registry=tool_registry,
        guardrail=guardrail,
        hitl=hitl,
        project_root=project_root,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CodeGuard CLI")
    parser.add_argument("--task", "-t", help="Task description", default="")
    parser.add_argument("--project", "-p", help="Project root", default=".")
    parser.add_argument("--serve", action="store_true", help="Start web server")
    parser.add_argument("--host", default="127.0.0.1", help="Web server host")
    parser.add_argument("--port", type=int, default=8000, help="Web server port")
    args = parser.parse_args()

    if args.serve:
        import uvicorn
        from codeguard.web import create_app
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port)
        return

    config = load_config()
    project_root = Path(args.project).resolve()
    agent = create_agent_from_config(config, project_root)
    result = agent.run(args.task)
    print(f"Status: {result['status']}")
    print(f"Turns: {result['turns']}")
    if "summary" in result:
        print(f"Summary: {result['summary']}")


if __name__ == "__main__":
    main()
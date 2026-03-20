"""调试 agent 工作流，检查 assistant_response content。"""
import asyncio
import json
import tempfile
from pathlib import Path

from agent import load_agent_config, create_agent_state_from_config, create_stream_fn_from_agent_config, Agent, AgentOptions


async def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(__file__).parent / "python-packages"
        llm_config_path = str(project_root / "ai" / "config" / "friday.json")

        config_file = Path(tmpdir) / "test_config.json"
        config_data = {
            "system_prompt": "You are a helpful assistant that can execute bash commands.",
            "model": {"api": "friday-responses", "provider": "friday", "id": "gpt-4o"},
            "thinking_level": "off",
            "tool_module_path": "tools",
            "tools": ["bash"],
            "llm_config_path": llm_config_path,
        }
        config_file.write_text(json.dumps(config_data, indent=2))

        config = load_agent_config(config_file)
        agent_state = create_agent_state_from_config(config)
        stream_fn = create_stream_fn_from_agent_config(config)

        agent = Agent(AgentOptions(
            initial_state={
                "system_prompt": agent_state.system_prompt,
                "model": agent_state.model,
                "thinking_level": agent_state.thinking_level,
            },
            stream_fn=stream_fn,
        ))
        agent.set_tools(agent_state.tools)

        events = []
        agent.subscribe(lambda e: events.append(e))

        await agent.prompt("Say 'Hello from agent test' and nothing else")

        print("\n=== messages in state ===")
        for i, m in enumerate(agent.state.messages):
            role = m.get("role") if isinstance(m, dict) else getattr(m, "role", "?")
            content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
            print(f"  [{i}] role={role}, content={content!r}")

        print("\n=== message_end events ===")
        for e in events:
            if e.get("type") == "message_end":
                print(f"  message_end: {e['message']!r}")


asyncio.run(main())


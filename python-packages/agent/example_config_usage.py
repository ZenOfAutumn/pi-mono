"""
配置加载使用示例

展示如何使用 config_loader 模块加载和使用 agent 配置
"""
import asyncio
from pathlib import Path

from src import (
    load_agent_config,
    create_agent_state_from_config,
)


async def example_load_config():
    """
    示例 1: 加载配置文件并创建 Agent
    """
    # 配置文件路径（相对于 python-packages/agent）
    config_path = Path(__file__).parent / "config" / "agent_config.json"

    # 加载配置（自动从文件读取 system_prompt）
    config = load_agent_config(config_path)

    print("加载的配置:")
    print(f"  系统提示词: {config['system_prompt'][:50]}...")
    print(f"  模型: {config['model']['id']}")
    print(f"  温度: {config['temperature']}")
    print(f"  最大 tokens: {config['max_tokens']}")

    # 从配置创建 Agent 状态
    agent_state = create_agent_state_from_config(config)
    print(f"\nAgent 状态:")
    print(f"  系统提示词已设置: {len(agent_state.system_prompt) > 0}")
    print(f"  模型: {agent_state.model.id}")
    print(f"  思考级别: {agent_state.thinking_level}")


async def example_custom_config():
    """
    示例 2: 使用自定义 JSON 配置
    """
    import json
    import tempfile

    # 创建临时配置文件
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 创建提示词文件
        prompts_dir = tmpdir / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "custom_system.txt"
        prompt_file.write_text(
            "你是一个编程助手。请帮助用户解决编程问题。",
            encoding="utf-8"
        )

        # 创建配置文件
        config_file = tmpdir / "my_config.json"
        config = {
            "system_prompt": "prompts/custom_system.txt",
            "model": {
                "api": "openai-chat",
                "provider": "openai",
                "id": "gpt-4"
            },
            "thinking_level": "medium",
            "temperature": 0.5,
            "max_tokens": 4000,
            "tools": []
        }
        config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

        # 加载配置
        from src import load_agent_config
        loaded_config = load_agent_config(config_file)

        print("\n自定义配置加载结果:")
        print(f"  系统提示词: {loaded_config['system_prompt']}")
        print(f"  模型: {loaded_config['model']['id']}")
        print(f"  思考级别: {loaded_config['thinking_level']}")


async def example_loop_config():
    """
    示例 3: 从配置创建 AgentLoopConfig
    """
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 创建配置文件
        config_file = tmpdir / "loop_config.json"
        config = {
            "model": {
                "api": "anthropic-messages",
                "provider": "anthropic",
                "id": "claude-3-opus-20240229"
            },
            "temperature": 0.7,
            "max_tokens": 8000,
            "thinking_budgets": {
                "minimal": 1000,
                "low": 2000,
            }
        }
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

        # 加载配置并创建 AgentLoopConfig
        from src import load_agent_config, create_agent_loop_config_from_config
        loaded_config = load_agent_config(config_file)
        loop_config = create_agent_loop_config_from_config(loaded_config)

        print("\nAgentLoopConfig 创建结果:")
        print(f"  模型 API: {loop_config.model.api}")
        print(f"  模型 ID: {loop_config.model.id}")
        print(f"  温度: {loop_config.temperature}")
        print(f"  最大 tokens: {loop_config.max_tokens}")
        print(f"  思考预算: {loop_config.thinking_budgets}")


async def main():
    """主入口点。"""
    print("=" * 60)
    print("Agent 配置加载示例")
    print("=" * 60)

    await example_load_config()
    await example_custom_config()
    await example_loop_config()

    print("\n" + "=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


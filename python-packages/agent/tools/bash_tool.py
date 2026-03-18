"""
Shell 命令执行工具。

提供执行 shell 命令的功能，支持超时控制和输出捕获。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

# 添加父目录到路径
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from src.types import AgentTool, AgentToolResult, TextContent


async def execute_bash(
    command: str,
    timeout: Optional[int] = 60,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
) -> AgentToolResult:
    """
    执行 shell 命令。

    Args:
        command: 要执行的 shell 命令
        timeout: 超时时间（秒），默认 60 秒
        cwd: 工作目录，默认为当前目录
        env: 环境变量字典，默认为 None

    Returns:
        AgentToolResult 包含命令输出

    Raises:
        RuntimeError: 命令执行失败或超时
    """
    try:
        # 创建子进程执行命令
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        # 等待命令完成，带超时
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError(f"Command timed out after {timeout} seconds")

        # 解码输出
        stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
        stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

        # 构建输出文本
        output_parts = []
        if stdout_text:
            output_parts.append(f"stdout:\n{stdout_text}")
        if stderr_text:
            output_parts.append(f"stderr:\n{stderr_text}")

        output = "\n\n".join(output_parts) if output_parts else "(no output)"

        # 如果返回码非零，抛出错误
        if process.returncode != 0:
            raise RuntimeError(
                f"Command failed with exit code {process.returncode}:\n{output}"
            )

        return AgentToolResult(
            content=[TextContent(text=output)],
            details={
                "command": command,
                "exit_code": process.returncode,
                "stdout_length": len(stdout_text),
                "stderr_length": len(stderr_text),
            },
        )

    except Exception as e:
        raise RuntimeError(f"Failed to execute command: {str(e)}")


async def bash_execute(
    tool_call_id: str,
    params: dict,
    signal: Optional[asyncio.Event] = None,
    on_update: Optional[callable] = None,
) -> AgentToolResult:
    """
    Bash 工具执行函数。

    Args:
        tool_call_id: 工具调用 ID
        params: 工具参数，包含 command, timeout, cwd, env
        signal: 中止信号
        on_update: 进度更新回调

    Returns:
        AgentToolResult
    """
    command = params.get("command", "")
    if not command:
        raise RuntimeError("Command is required")

    timeout = params.get("timeout", 60)
    cwd = params.get("cwd")
    env = params.get("env")

    # 发送进度更新
    if on_update:
        on_update(
            AgentToolResult(
                content=[TextContent(text=f"Executing: {command}")],
                details={"status": "started"},
            )
        )

    result = await execute_bash(command, timeout=timeout, cwd=cwd, env=env)

    # 发送完成更新
    if on_update:
        on_update(
            AgentToolResult(
                content=[TextContent(text="Command completed")],
                details={"status": "completed"},
            )
        )

    return result


# 工具实例
bash_tool = AgentTool(
    name="bash",
    label="Bash",
    description="Execute shell commands with optional timeout and working directory",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 60)",
                "default": 60,
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command (optional)",
            },
            "env": {
                "type": "object",
                "description": "Environment variables as key-value pairs (optional)",
            },
        },
        "required": ["command"],
    },
    execute=bash_execute,
)


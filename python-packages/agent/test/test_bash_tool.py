"""
bash_tool.py 模块的单元测试。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.bash_tool import execute_bash, bash_execute, bash_tool


class TestExecuteBash:
    """execute_bash 函数的测试。"""

    @pytest.mark.asyncio
    async def test_execute_simple_command(self):
        """测试执行简单命令。"""
        result = await execute_bash("echo hello")

        assert "hello" in result.content[0].text
        assert result.details["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_output(self):
        """测试执行命令并捕获输出。"""
        result = await execute_bash("echo stdout_text && echo stderr_text >&2")

        output = result.content[0].text
        assert "stdout_text" in output
        assert "stderr_text" in output

    @pytest.mark.asyncio
    async def test_execute_with_cwd(self):
        """测试在指定工作目录执行命令。"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await execute_bash("pwd", cwd=tmpdir)

            assert tmpdir in result.content[0].text or os.path.basename(tmpdir) in result.content[0].text

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """测试命令超时。"""
        with pytest.raises(RuntimeError, match="timed out"):
            await execute_bash("sleep 10", timeout=0.1)

    @pytest.mark.asyncio
    async def test_execute_invalid_command(self):
        """测试执行无效命令。"""
        with pytest.raises(RuntimeError):
            await execute_bash("nonexistent_command_xyz")

    @pytest.mark.asyncio
    async def test_execute_with_env(self):
        """测试设置环境变量。"""
        result = await execute_bash("echo $TEST_VAR", env={"TEST_VAR": "test_value"})

        assert "test_value" in result.content[0].text


class TestBashTool:
    """bash_tool 的测试。"""

    @pytest.mark.asyncio
    async def test_bash_tool_execute(self):
        """测试 bash_tool 执行。"""
        result = await bash_tool.execute(
            "test-call-id",
            {"command": "echo hello world"},
            None,
            None,
        )

        assert "hello world" in result.content[0].text

    @pytest.mark.asyncio
    async def test_bash_tool_with_timeout(self):
        """测试 bash_tool 带超时参数。"""
        result = await bash_tool.execute(
            "test-call-id",
            {"command": "echo test", "timeout": 5},
            None,
            None,
        )

        assert "test" in result.content[0].text

    @pytest.mark.asyncio
    async def test_bash_tool_empty_command_raises(self):
        """测试空命令抛出错误。"""
        with pytest.raises(RuntimeError, match="Command is required"):
            await bash_tool.execute(
                "test-call-id",
                {"command": ""},
                None,
                None,
            )

    def test_bash_tool_properties(self):
        """测试 bash_tool 属性。"""
        assert bash_tool.name == "bash"
        assert bash_tool.label == "Bash"
        assert "shell" in bash_tool.description.lower()
        assert "command" in bash_tool.parameters["properties"]

    def test_bash_tool_parameters_schema(self):
        """测试参数 schema。"""
        params = bash_tool.parameters

        assert params["type"] == "object"
        assert "command" in params["properties"]
        assert "timeout" in params["properties"]
        assert "cwd" in params["properties"]
        assert "env" in params["properties"]
        assert "command" in params["required"]


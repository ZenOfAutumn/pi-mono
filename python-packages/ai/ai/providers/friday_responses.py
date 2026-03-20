"""
Friday Responses API 流式调用实现。

本模块实现 Friday Responses API 的流式调用功能，
支持文本生成、工具调用和思考模型。
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .friday_config import (
    FRIDAY_RESPONSES_API_URL,
    FridayAuthConfig,
    FridayResponsesOptions,
    build_friday_request_params,
)
from .simple_options import build_base_options
from .transform_messages import transform_messages
from ..core_types import (
    AssistantMessage,
    Usage,
    UsageCost,
    StopReason,
    StartEvent,
    TextStartEvent,
    TextDeltaEvent,
    TextEndEvent,
    ToolCallStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    DoneEvent,
    ErrorEvent,
)
from ..utils.event_stream import AssistantMessageEventStream
from ..utils.json_parse import parse_streaming_json
from ..utils.sanitize_unicode import sanitize_surrogates

if TYPE_CHECKING:
    from ..core_types import (
        Context,
        Model,
        SimpleStreamOptions,
        Tool,
        ToolCall,
        ToolResultMessage,
    )


# ============================================================================
# 消息转换
# ============================================================================

def convert_messages_to_friday(
    context: "Context",
    model: "Model",
) -> List[Dict[str, Any]]:
    """
    将内部消息格式转换为 Friday Responses API 格式。

    Friday Responses API 使用 input 字段接收消息，
    格式类似于 OpenAI Responses API。

    Args:
        context: 对话上下文
        model: 目标模型

    Returns:
        Friday API 格式的消息列表
    """
    messages: List[Dict[str, Any]] = []

    # 转换消息（处理跨提供商兼容性）
    transformed = transform_messages(context.messages, model)

    # 添加系统提示
    if context.systemPrompt:
        messages.append({
            "role": "developer",
            "content": [{"type": "input_text", "text": sanitize_surrogates(context.systemPrompt)}],
        })

    for msg in transformed:
        if msg.role == "user":
            if isinstance(msg.content, str):
                messages.append({
                    "role": "user",
                    "content": [{"type": "input_text", "text": sanitize_surrogates(msg.content)}],
                })
            else:
                # 处理多模态内容
                content_parts = []
                for item in msg.content:
                    if item.type == "text":
                        content_parts.append({
                            "type": "input_text",
                            "text": sanitize_surrogates(item.text),
                        })
                    elif item.type == "image":
                        # Friday 要求图片为外网可访问的 URL 或 base64 数据 URL
                        content_parts.append({
                            "type": "input_image",
                            "image_url": f"data:{item.mimeType};base64,{item.data}",
                        })
                if content_parts:
                    messages.append({"role": "user", "content": content_parts})

        elif msg.role == "assistant":
            assistant_msg = msg  # type: AssistantMessage
            for block in assistant_msg.content:
                if block.type == "text":
                    messages.append({
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": sanitize_surrogates(block.text)}],
                    })
                elif block.type == "toolCall":
                    tool_call = block  # type: ToolCall
                    call_id, item_id = _split_tool_call_id(tool_call.id)
                    messages.append({
                        "type": "function_call",
                        "id": item_id,
                        "call_id": call_id,
                        "name": tool_call.name,
                        "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
                    })

        elif msg.role == "toolResult":
            tool_result = msg  # type: ToolResultMessage
            call_id, _ = _split_tool_call_id(tool_result.toolCallId)
            # 提取文本结果
            text_result = "\n".join(
                item.text for item in tool_result.content if item.type == "text"
            )
            messages.append({
                "type": "function_call_output",
                "call_id": call_id,
                "output": sanitize_surrogates(text_result) if text_result else "(no result)",
            })

    return messages


def _split_tool_call_id(tool_call_id: str) -> tuple:
    """
    分割工具调用 ID。

    工具调用 ID 格式为 "call_id|item_id"，
    如果没有分隔符，则整个作为 call_id。

    Args:
        tool_call_id: 工具调用 ID

    Returns:
        (call_id, item_id) 元组
    """
    if "|" in tool_call_id:
        parts = tool_call_id.split("|", 1)
        return parts[0], parts[1]
    return tool_call_id, None


def convert_tools_to_friday(tools: List["Tool"]) -> List[Dict[str, Any]]:
    """
    将内部工具定义转换为 Friday API 格式。

    Args:
        tools: 工具定义列表

    Returns:
        Friday API 格式的工具列表
    """
    friday_tools = []
    for tool in tools:
        friday_tools.append({
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        })
    return friday_tools


# ============================================================================
# 流式响应处理
# ============================================================================

async def process_friday_stream(
    response: Any,  # aiohttp response
    output: "AssistantMessage",
    stream: AssistantMessageEventStream,
) -> None:
    """
    处理 Friday Responses API 的流式响应。

    Friday 支持 SSE (Server-Sent Events) 流式响应，
    事件类型包括：
    - response.created
    - response.in_progress
    - response.output_text.delta
    - response.function_call_arguments.delta
    - response.function_call_arguments.done
    - response.completed

    Args:
        response: aiohttp 响应对象
        output: 输出消息对象
        stream: 事件流
    """
    current_item_type: Optional[str] = None
    current_block: Optional[Dict[str, Any]] = None
    partial_json: str = ""

    async for line in response.content:
        line_text = line.decode("utf-8").strip()

        # 跳过空行和注释
        if not line_text or line_text.startswith(":"):
            continue

        # 解析 SSE 事件
        if line_text.startswith("data: "):
            data_str = line_text[6:]  # 移除 "data: " 前缀

            # 跳过 [DONE] 标记
            if data_str == "[DONE]":
                break

            try:
                event = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            current_item_type, current_block, partial_json = await _process_event(
                event,
                output,
                stream,
                current_item_type,
                current_block,
                partial_json,
            )


async def _process_event(
    event: Dict[str, Any],
    output: "AssistantMessage",
    stream: AssistantMessageEventStream,
    current_item_type: Optional[str],
    current_block: Optional[Dict[str, Any]],
    partial_json: str,
) -> tuple:
    """
    处理单个流式事件。

    Args:
        event: 事件数据
        output: 输出消息
        stream: 事件流
        current_item_type: 当前项目类型
        current_block: 当前内容块
        partial_json: 部分 JSON 字符串

    Returns:
        更新后的 (current_item_type, current_block, partial_json)
    """
    event_type = event.get("type", "")
    blocks = output.content

    # 响应创建事件
    if event_type == "response.created":
            stream.push(StartEvent(partial=output))

    # 输出项添加事件
    elif event_type == "response.output_item.added":
        item = event.get("item", {})
        item_type = item.get("type", "")
        current_item_type = item_type

        if item_type == "message":
            current_block = {"type": "text", "text": ""}
            blocks.append(current_block)
            stream.push(TextStartEvent(
                contentIndex=len(blocks) - 1,
                partial=output,
            ))
        elif item_type == "function_call":
            current_block = {
                "type": "toolCall",
                "id": f"{item.get('call_id', '')}|{item.get('id', '')}",
                "name": item.get("name", ""),
                "arguments": {},
            }
            partial_json = ""
            blocks.append(current_block)
            stream.push(ToolCallStartEvent(
                contentIndex=len(blocks) - 1,
                partial=output,
            ))

    # 文本增量事件
    elif event_type == "response.output_text.delta":
        delta = event.get("delta", "")
        # 如果 current_block 未初始化（API 可能跳过了 output_item.added），自动创建文本块
        if not current_block or current_block.get("type") != "text":
            current_block = {"type": "text", "text": ""}
            blocks.append(current_block)
            stream.push(TextStartEvent(
                contentIndex=len(blocks) - 1,
                partial=output,
            ))
        current_block["text"] += delta
        stream.push(TextDeltaEvent(
            contentIndex=len(blocks) - 1,
            delta=delta,
            partial=output,
        ))

    # 函数调用参数增量事件
    elif event_type == "response.function_call_arguments.delta":
        delta = event.get("delta", "")
        if current_block and current_block.get("type") == "toolCall":
            partial_json += delta
            current_block["arguments"] = parse_streaming_json(partial_json)
            stream.push(ToolCallDeltaEvent(
                contentIndex=len(blocks) - 1,
                delta=delta,
                partial=output,
            ))

    # 函数调用参数完成事件
    elif event_type == "response.function_call_arguments.done":
        arguments_str = event.get("arguments", "{}")
        if current_block and current_block.get("type") == "toolCall":
            try:
                current_block["arguments"] = json.loads(arguments_str)
            except json.JSONDecodeError:
                current_block["arguments"] = parse_streaming_json(arguments_str)

    # 输出项完成事件
    elif event_type == "response.output_item.done":
        item = event.get("item", {})

        if item.get("type") == "message" and current_block:
            # 合并所有文本内容
            content = item.get("content", [])
            text = "".join(
                c.get("text", "") for c in content if c.get("type") == "output_text"
            )
            current_block["text"] = text
            stream.push(TextEndEvent(
                contentIndex=len(blocks) - 1,
                content=text,
                partial=output,
            ))
            current_block = None

        elif item.get("type") == "function_call" and current_block:
            tool_call = ToolCall(
                type="toolCall",
                id=f"{item.get('call_id', '')}|{item.get('id', '')}",
                name=item.get("name", ""),
                arguments=json.loads(item.get("arguments", "{}")),
            )
            stream.push(ToolCallEndEvent(
                contentIndex=len(blocks) - 1,
                toolCall=tool_call,
                partial=output,
            ))
            current_block = None

    # 响应完成事件
    elif event_type == "response.completed":
        response_data = event.get("response", {})

        # 处理 usage
        usage_data = response_data.get("usage", {})
        if usage_data:
            details = usage_data.get("input_tokens_details") or {}
            cached_tokens = details.get("cached_tokens") or 0
            output.usage = Usage(
                input=(usage_data.get("input_tokens") or 0) - cached_tokens,
                output=usage_data.get("output_tokens", 0),
                cacheRead=cached_tokens,
                cacheWrite=0,
                totalTokens=usage_data.get("total_tokens", 0),
                cost=UsageCost(),
            )

        # 映射停止原因
        status = response_data.get("status", "completed")
        output.stopReason = _map_stop_reason(status)

        # 如果有工具调用，停止原因为 toolUse
        if any(b.get("type") == "toolCall" for b in blocks):
            output.stopReason = "toolUse"

    # 错误事件
    elif event_type == "error":
        error_code = event.get("code", "unknown")
        error_message = event.get("message", "Unknown error")
        raise Exception(f"Error {error_code}: {error_message}")

    elif event_type == "response.failed":
        error = event.get("response", {}).get("error", {})
        raise Exception(f"{error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}")

    elif not event_type and event.get("code"):
        # 裸 JSON 错误（无 type 字段，但有 code/message），如 {"code":400002,"message":"..."}
        raise Exception(f"Error {event['code']}: {event.get('message', 'Unknown error')}")

    return current_item_type, current_block, partial_json


def _map_stop_reason(status: str) -> "StopReason":
    """
    将 Friday 响应状态映射到内部停止原因。

    Args:
        status: Friday 响应状态

    Returns:
        内部停止原因
    """
    status_map = {
        "completed": "stop",
        "incomplete": "length",
        "failed": "error",
        "cancelled": "error",
    }
    return status_map.get(status, "stop")


# ============================================================================
# 流函数实现
# ============================================================================

def stream_friday_responses(
    model: "Model",
    context: "Context",
    options: Optional[FridayResponsesOptions] = None,
) -> AssistantMessageEventStream:
    """
    Friday Responses API 流式调用函数。

    这是主要的流式接口，发送请求到 Friday Responses API
    并返回事件流。

    Args:
        model: 模型配置
        context: 对话上下文
        options: 可选的流式选项

    Returns:
        助手消息事件流
    """
    stream = AssistantMessageEventStream()

    # 初始化输出消息
    output = AssistantMessage(
        role="assistant",
        content=[],
        api=model.api if isinstance(model.api, str) else "friday-responses",
        provider=model.provider if isinstance(model.provider, str) else "friday",
        model=model.id,
        usage=Usage(
            input=0,
            output=0,
            cacheRead=0,
            cacheWrite=0,
            totalTokens=0,
            cost=UsageCost(),
        ),
        stopReason="stop",
        timestamp=int(time.time() * 1000),
    )

    async def _process():
        """异步处理函数。"""
        try:
            # 获取认证配置
            auth_config = _get_auth_config(options)
            if not auth_config:
                raise ValueError(
                    "Friday 认证配置缺失。请设置 FRIDAY_BILLING_ID 环境变量 "
                    "或在 options 中提供 billingId。"
                )

            # 构建请求参数
            messages = convert_messages_to_friday(context, model)
            tools = convert_tools_to_friday(context.tools) if context.tools else None
            params = build_friday_request_params(model.id, messages, tools, options)

            # 发送请求
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    FRIDAY_RESPONSES_API_URL,
                    headers=auth_config.to_headers(),
                    json=params,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Friday API 错误 ({response.status}): {error_text}")

                    await process_friday_stream(response, output, stream)

            print(json.dumps({
                "content": [{"type": b.get("type"), "text": b.get("text", "")} for b in output.content],
                "stopReason": output.stopReason,
            }, ensure_ascii=False, indent=2))

            # 发送完成事件
            if output.stopReason not in ("error", "aborted"):
                stream.push(DoneEvent(reason=output.stopReason, message=output))
            stream.end()

        except Exception as e:
            output.stopReason = "error"
            output.errorMessage = str(e)
            stream.push(ErrorEvent(reason="error", error=output))
            stream.end()

    # 启动异步处理
    asyncio.create_task(_process())

    return stream


def stream_simple_friday_responses(
    model: "Model",
    context: "Context",
    options: Optional["SimpleStreamOptions"] = None,
) -> AssistantMessageEventStream:
    """
    Friday Responses API 简化流式调用函数。

    使用统一的选项格式，自动映射到 Friday 特有选项。

    Args:
        model: 模型配置
        context: 对话上下文
        options: 简化的流式选项

    Returns:
        助手消息事件流
    """
    # 构建基础选项
    base_options = build_base_options(model, options)

    # 映射 reasoning 参数
    friday_options: FridayResponsesOptions = {}
    friday_options.update(base_options)

    if options and options.get("reasoning") is not None:
        friday_options["reasoning"] = options["reasoning"]

    return stream_friday_responses(model, context, friday_options)


def _get_auth_config(options: Optional[FridayResponsesOptions]) -> Optional[FridayAuthConfig]:
    """
    获取认证配置。

    配置来源优先级：
    1. 代码中直接传入的 options 参数
    2. 配置文件（通过 options.configPath 指定或默认路径）
    3. 环境变量

    Args:
        options: 流式选项

    Returns:
        认证配置，如果缺失必需信息则返回 None
    """
    # 获取 options 中的自定义 headers
    custom_headers = options.get("headers") if options else None

    if options:
        billing_id = options.get("billingId")
        if billing_id:
            return FridayAuthConfig(
                billing_id=billing_id,
                agent_id=options.get("agentId"),
                context_token=options.get("contextToken"),
                user_id=options.get("userId"),
                headers=custom_headers,
            )

        # 如果指定了配置文件路径，从指定路径加载
        config_path = options.get("configPath")
        if config_path:
            from .friday_config import FridayConfigManager
            config_manager = FridayConfigManager(Path(config_path))
            config = FridayAuthConfig.from_config(config_manager)
            if config:
                # 合并 options 中的 headers（优先级更高）
                if custom_headers:
                    if config.headers:
                        config.headers.update(custom_headers)
                    else:
                        config.headers = custom_headers
                return config

    # 从默认配置文件获取
    from .friday_config import get_config_manager
    config = FridayAuthConfig.from_config(get_config_manager())
    if config:
        # 合并 options 中的 headers（优先级更高）
        if custom_headers:
            if config.headers:
                config.headers.update(custom_headers)
            else:
                config.headers = custom_headers
        return config

    # 从环境变量获取（向后兼容）
    return FridayAuthConfig.from_env()


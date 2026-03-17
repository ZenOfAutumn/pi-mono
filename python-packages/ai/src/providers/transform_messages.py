"""
跨提供商兼容的消息转换工具。

本模块提供在不同 LLM 提供商格式之间转换消息的功能，
处理思考块、工具调用 ID 和孤立的工具调用。
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from ..core_types import (
        AssistantMessage,
        Message,
        Model,
        TextContent,
        ToolCall,
        ToolResultMessage,
    )


def transform_messages(
    messages: List["Message"],
    model: "Model",
    normalize_tool_call_id: Optional[
        Callable[[str, "Model", "AssistantMessage"], str]
    ] = None,
) -> List["Message"]:
    """
    规范化和转换消息以实现跨提供商兼容。

    此函数处理：
    - 跨提供商重放时的思考块转换
    - 工具调用 ID 规范化（某些提供商有长度/字符限制）
    - 为孤立的工具调用插入合成工具结果

    Args:
        messages: 要转换的消息列表
        model: 目标模型
        normalize_tool_call_id: 可选的工具调用 ID 规范化函数

    Returns:
        转换后的消息列表
    """
    # 构建原始工具调用 ID 到规范化 ID 的映射
    tool_call_id_map: Dict[str, str] = {}

    # 第一遍：转换消息（思考块、工具调用 ID 规范化）
    transformed: List["Message"] = []
    for msg in messages:
        # 用户消息直接通过
        if msg.role == "user":
            transformed.append(msg)
            continue

        # 处理 toolResult 消息 - 如果有映射则规范化 toolCallId
        if msg.role == "toolResult":
            normalized_id = tool_call_id_map.get(msg.toolCallId)
            if normalized_id and normalized_id != msg.toolCallId:
                # 创建带有规范化 ID 的新消息
                from ..core_types import ToolResultMessage
                new_msg = ToolResultMessage(
                    role="toolResult",
                    toolCallId=normalized_id,
                    toolName=msg.toolName,
                    content=msg.content,
                    details=msg.details,
                    isError=msg.isError,
                    timestamp=msg.timestamp,
                )
                transformed.append(new_msg)
            else:
                transformed.append(msg)
            continue

        # 助手消息需要转换检查
        if msg.role == "assistant":
            assistant_msg = msg  # type: AssistantMessage
            is_same_model = (
                assistant_msg.provider == model.provider
                and assistant_msg.api == model.api
                and assistant_msg.model == model.id
            )

            transformed_content = []
            for block in assistant_msg.content:
                if block.type == "thinking":
                    # 已编辑的思考是加密的不透明内容，仅对同一模型有效。
                    # 跨模型时丢弃以避免 API 错误。
                    if block.redacted:
                        if is_same_model:
                            transformed_content.append(block)
                        continue

                    # 同一模型：保留带签名的思考块（重放需要）
                    # 即使思考文本为空（OpenAI 加密推理）
                    if is_same_model and block.thinkingSignature:
                        transformed_content.append(block)
                        continue

                    # 跳过空思考块，其他转换为纯文本
                    if not block.thinking or block.thinking.strip() == "":
                        continue

                    if is_same_model:
                        transformed_content.append(block)
                    else:
                        from ..core_types import TextContent
                        transformed_content.append(
                            TextContent(
                                type="text",
                                text=block.thinking,
                            )
                        )
                    continue

                if block.type == "text":
                    if is_same_model:
                        transformed_content.append(block)
                    else:
                        from ..core_types import TextContent
                        transformed_content.append(
                            TextContent(
                                type="text",
                                text=block.text,
                                textSignature=block.textSignature,
                            )
                        )
                    continue

                if block.type == "toolCall":
                    tool_call = block  # type: ToolCall
                    normalized_tool_call = tool_call

                    if not is_same_model and tool_call.thoughtSignature:
                        # 创建不带 thoughtSignature 的副本
                        from ..core_types import ToolCall
                        normalized_tool_call = ToolCall(
                            type="toolCall",
                            id=tool_call.id,
                            name=tool_call.name,
                            arguments=tool_call.arguments,
                        )

                    if not is_same_model and normalize_tool_call_id:
                        normalized_id = normalize_tool_call_id(
                            tool_call.id, model, assistant_msg
                        )
                        if normalized_id != tool_call.id:
                            tool_call_id_map[tool_call.id] = normalized_id
                            from ..core_types import ToolCall
                            normalized_tool_call = ToolCall(
                                type="toolCall",
                                id=normalized_id,
                                name=normalized_tool_call.name,
                                arguments=normalized_tool_call.arguments,
                            )

                    transformed_content.append(normalized_tool_call)
                    continue

                # 未知块类型，直接通过
                transformed_content.append(block)

            # 创建带有转换内容的新助手消息
            from ..core_types import AssistantMessage
            new_assistant = AssistantMessage(
                role="assistant",
                content=transformed_content,
                api=assistant_msg.api,
                provider=assistant_msg.provider,
                model=assistant_msg.model,
                usage=assistant_msg.usage,
                stopReason=assistant_msg.stopReason,
                errorMessage=assistant_msg.errorMessage,
                timestamp=assistant_msg.timestamp,
            )
            transformed.append(new_assistant)
            continue

        # 未知消息类型，直接通过
        transformed.append(msg)

    # 第二遍：为孤立的工具调用插入合成空工具结果
    # 这保留了思考签名并满足 API 要求
    result: List["Message"] = []
    pending_tool_calls: List["ToolCall"] = []
    existing_tool_result_ids: set = set()

    for msg in transformed:
        if msg.role == "assistant":
            # 如果前一个助手有待处理的孤立工具调用，
            # 现在插入合成结果
            if pending_tool_calls:
                for tc in pending_tool_calls:
                    if tc.id not in existing_tool_result_ids:
                        from ..core_types import ToolResultMessage
                        result.append(
                            ToolResultMessage(
                                role="toolResult",
                                toolCallId=tc.id,
                                toolName=tc.name,
                                content=[{"type": "text", "text": "No result provided"}],
                                isError=True,
                                timestamp=int(time.time() * 1000),
                            )
                        )
                pending_tool_calls = []
                existing_tool_result_ids = set()

            # 完全跳过错误/中止的助手消息。
            # 这些是不完整的对话轮次，不应重放：
            # - 可能有部分内容（无消息的推理、不完整的工具调用）
            # - 重放可能导致 API 错误
            # - 模型应从最后有效状态重试
            assistant_msg = msg  # type: AssistantMessage
            if assistant_msg.stopReason in ("error", "aborted"):
                continue

            # 追踪此助手消息中的工具调用
            tool_calls = [b for b in assistant_msg.content if b.type == "toolCall"]
            if tool_calls:
                pending_tool_calls = tool_calls  # type: List[ToolCall]
                existing_tool_result_ids = set()

            result.append(msg)

        elif msg.role == "toolResult":
            existing_tool_result_ids.add(msg.toolCallId)
            result.append(msg)

        elif msg.role == "user":
            # 用户消息中断工具流 - 为孤立调用插入合成结果
            if pending_tool_calls:
                for tc in pending_tool_calls:
                    if tc.id not in existing_tool_result_ids:
                        from ..core_types import ToolResultMessage
                        result.append(
                            ToolResultMessage(
                                role="toolResult",
                                toolCallId=tc.id,
                                toolName=tc.name,
                                content=[{"type": "text", "text": "No result provided"}],
                                isError=True,
                                timestamp=int(time.time() * 1000),
                            )
                        )
                pending_tool_calls = []
                existing_tool_result_ids = set()
            result.append(msg)

        else:
            result.append(msg)

    return result


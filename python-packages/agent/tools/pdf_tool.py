"""
PDF 文档读取工具。

提供读取 PDF 文档内容的功能，支持文本提取和页面范围选择。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# 添加父目录到路径
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from agent.types import AgentTool, AgentToolResult, TextContent


def _extract_pdf_text(file_path: str, start_page: int = 0, end_page: Optional[int] = None) -> str:
    """
    从 PDF 文件中提取文本内容。

    Args:
        file_path: PDF 文件路径
        start_page: 起始页码（从 0 开始），默认为 0
        end_page: 结束页码（不包含），默认为 None 表示到最后一页

    Returns:
        提取的文本内容

    Raises:
        RuntimeError: PDF 处理失败
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError(
            "PyMuPDF is required to read PDF files. "
            "Install it with: pip install pymupdf"
        )

    path = Path(file_path)
    if not path.exists():
        raise RuntimeError(f"PDF file not found: {file_path}")

    if not path.suffix.lower() == ".pdf":
        raise RuntimeError(f"File is not a PDF: {file_path}")

    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)

        if total_pages == 0:
            return ""

        # 验证页码范围
        if start_page < 0:
            start_page = 0
        if start_page >= total_pages:
            raise RuntimeError(
                f"Start page {start_page} exceeds total pages {total_pages}"
            )

        if end_page is None or end_page > total_pages:
            end_page = total_pages
        if end_page <= start_page:
            raise RuntimeError(
                f"End page {end_page} must be greater than start page {start_page}"
            )

        # 提取文本
        text_parts = []
        for page_num in range(start_page, end_page):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

        doc.close()

        return "\n\n".join(text_parts) if text_parts else ""

    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {str(e)}")


async def read_pdf(
    file_path: str,
    start_page: int = 0,
    end_page: Optional[int] = None,
    max_chars: int = 100000,
    search_query: Optional[str] = None,
) -> AgentToolResult:
    """
    读取 PDF 文档内容。

    Args:
        file_path: PDF 文件路径
        start_page: 起始页码（从 1 开始），默认为 1
        end_page: 结束页码（包含），默认为 None 表示到最后一页
        max_chars: 最大返回字符数，默认为 100000
        search_query: 搜索查询字符串，如果提供则会自动搜索相关内容

    Returns:
        AgentToolResult 包含提取的文本内容

    Raises:
        RuntimeError: PDF 读取失败
    """
    # 如果提供了搜索查询，优先使用智能搜索
    if search_query:
        text, found_start_page, found_end_page = _search_pdf_content(file_path, search_query, max_chars)
        if text:
            return AgentToolResult(
                content=[TextContent(text=text)],
                details={
                    "file_path": file_path,
                    "start_page": found_start_page,
                    "end_page": found_end_page,
                    "text_length": len(text),
                    "search_query": search_query,
                    "truncated": len(text) > max_chars,
                    "max_chars": max_chars,
                },
            )
        # 如果搜索失败，回退到常规提取

    # 确保参数有正确的默认值
    if start_page is None:
        start_page = 1
    if end_page is None:
        end_page = None
    if max_chars is None:
        max_chars = 100000

    # 转换页码（用户输入是 1-based，内部使用 0-based）
    internal_start = start_page - 1 if start_page > 0 else 0
    internal_end = end_page if end_page is not None else None

    text = _extract_pdf_text(file_path, internal_start, internal_end)

    if not text:
        return AgentToolResult(
            content=[TextContent(text="(PDF contains no text content)")],
            details={
                "file_path": file_path,
                "start_page": start_page,
                "end_page": end_page,
                "text_length": 0,
            },
        )

    # 截断过长的内容
    truncated = False
    original_length = len(text)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n... (content truncated)"
        truncated = True

    return AgentToolResult(
        content=[TextContent(text=text)],
        details={
            "file_path": file_path,
            "start_page": start_page,
            "end_page": end_page,
            "text_length": original_length,
            "truncated": truncated,
            "max_chars": max_chars,
        },
    )


async def pdf_read(
    tool_call_id: str,
    params: dict,
    signal: Optional[object] = None,
    on_update: Optional[callable] = None,
) -> AgentToolResult:
    """
    PDF 读取工具执行函数。

    Args:
        tool_call_id: 工具调用 ID
        params: 工具参数，包含 file_path, start_page, end_page, max_chars
        signal: 中止信号
        on_update: 进度更新回调

    Returns:
        AgentToolResult
    """
    file_path = params.get("file_path", "")
    if not file_path:
        raise RuntimeError("file_path is required")

    start_page = params.get("start_page", 1)
    end_page = params.get("end_page")
    max_chars = params.get("max_chars", 100000)
    search_query = params.get("search_query")

    # 发送进度更新
    if on_update:
        on_update(
            AgentToolResult(
                content=[TextContent(text=f"Reading PDF: {file_path}")],
                details={"status": "started"},
            )
        )

    result = await read_pdf(
        file_path=file_path,
        start_page=start_page,
        end_page=end_page,
        max_chars=max_chars,
        search_query=search_query,
    )

    # 发送完成更新
    if on_update:
        on_update(
            AgentToolResult(
                content=[TextContent(text="PDF reading completed")],
                details={"status": "completed"},
            )
        )

    return result


def _search_pdf_content(file_path: str, search_query: str, max_chars: int = 100000) -> tuple[str, int, int]:
    """
    在PDF中智能搜索相关内容。

    Args:
        file_path: PDF文件路径
        search_query: 搜索查询
        max_chars: 最大字符数限制

    Returns:
        tuple: (找到的文本, 起始页码, 结束页码)
    """
    try:
        import fitz
    except ImportError:
        return "", 0, 0

    path = Path(file_path)
    if not path.exists():
        return "", 0, 0

    doc = None
    try:
        doc = fitz.open(file_path)

        # 定义搜索关键词映射
        search_keywords = {
            'bibliography': ['bibliography', '参考文献', 'reference', '引用文献', '参考资料'],
            'index': ['index', '索引', '目录'],
            'appendix': ['appendix', '附录', 'appendixes'],
            'table of contents': ['table of contents', 'contents', '目录', 'content']
        }

        # 确定搜索类型
        query_lower = search_query.lower()
        target_keywords = []

        for search_type, keywords in search_keywords.items():
            if search_type in query_lower:
                target_keywords.extend(keywords)

        # 如果没有匹配的搜索类型，使用查询中的关键词
        if not target_keywords:
            target_keywords = [word.lower() for word in search_query.split() if len(word) > 2]

        # 从后往前搜索（Bibliography通常在文档末尾）
        if 'bibliography' in query_lower or '参考文献' in query_lower:
            search_range = range(doc.page_count, max(0, doc.page_count - 100), -1)
        else:
            search_range = range(1, doc.page_count + 1)

        for page_num in search_range:
            try:
                page = doc.load_page(page_num - 1)
                text = page.get_text()

                # 检查页面是否包含目标关键词
                if any(keyword.lower() in text.lower() for keyword in target_keywords):
                    # 找到相关页面，提取内容
                    extracted_text = f"--- Page {page_num} ---\n{text}\n"

                    # 尝试获取相邻页面的内容以获得更多上下文
                    context_text = ""
                    if page_num < doc.page_count:
                        try:
                            next_page = doc.load_page(page_num)
                            next_text = next_page.get_text()
                            context_text += f"\n--- Page {page_num + 1} ---\n{next_text[:2000]}...\n"
                        except:
                            pass

                    full_text = extracted_text + context_text

                    # 截断过长的内容
                    if len(full_text) > max_chars:
                        full_text = full_text[:max_chars] + "\n\n... (content truncated)"

                    return full_text, page_num, min(page_num + 1, doc.page_count)

            except Exception:
                continue

    except Exception:
        return "", 0, 0
    finally:
        if doc is not None:
            doc.close()

    return "", 0, 0


# 工具实例
pdf_tool = AgentTool(
    name="pdf_read",
    label="PDF Read",
    description="Read text content from PDF documents with optional page range selection",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the PDF file to read",
            },
            "start_page": {
                "type": "integer",
                "description": "Starting page number (1-based, default: 1)",
                "default": 1,
            },
            "end_page": {
                "type": "integer",
                "description": "Ending page number (inclusive, default: read all pages)",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return (default: 100000)",
                "default": 100000,
            },
            "search_query": {
                "type": "string",
                "description": "Search query to find specific content (e.g., 'Bibliography', 'Index'). If provided, the tool will automatically search for relevant pages.",
            },
        },
        "required": ["file_path"],
    },
    execute=pdf_read,
)


"""
PDF 工具测试模块
"""
from __future__ import annotations

import sys
from pathlib import Path

# 添加父目录到路径
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

import pytest

from agent.types import AgentToolResult, TextContent
from tools.pdf_tool import pdf_read, pdf_tool, _extract_pdf_text


class TestPdfTool:
    """PDF 工具测试类"""

    def test_pdf_tool_definition(self):
        """测试 PDF 工具定义"""
        assert pdf_tool.name == "pdf_read"
        assert pdf_tool.label == "PDF Read"
        assert "PDF" in pdf_tool.description

        # 检查参数定义
        params = pdf_tool.parameters
        assert params["type"] == "object"
        assert "file_path" in params["properties"]
        assert "start_page" in params["properties"]
        assert "end_page" in params["properties"]
        assert "max_chars" in params["properties"]
        assert params["required"] == ["file_path"]

    @pytest.mark.asyncio
    async def test_pdf_read_missing_file_path(self):
        """测试缺少 file_path 参数"""
        with pytest.raises(RuntimeError, match="file_path is required"):
            await pdf_read("test-id", {})

    @pytest.mark.asyncio
    async def test_pdf_read_file_not_found(self):
        """测试文件不存在"""
        with pytest.raises(RuntimeError, match="PDF file not found"):
            await pdf_read("test-id", {"file_path": "/nonexistent/file.pdf"})

    @pytest.mark.asyncio
    async def test_pdf_read_not_pdf_file(self):
        """测试非 PDF 文件"""
        # 创建一个临时非 PDF 文件
        temp_file = Path("/tmp/test_not_pdf.txt")
        temp_file.write_text("not a pdf")

        try:
            with pytest.raises(RuntimeError, match="File is not a PDF"):
                await pdf_read("test-id", {"file_path": str(temp_file)})
        finally:
            temp_file.unlink()

    @pytest.mark.asyncio
    async def test_pdf_read_pymupdf_not_installed(self, monkeypatch):
        """测试 PyMuPDF 未安装时的错误处理"""
        # 模拟 pymupdf 未安装
        monkeypatch.setitem(sys.modules, "fitz", None)

        with pytest.raises(RuntimeError, match="PyMuPDF is required"):
            _extract_pdf_text("/fake/path.pdf")


class TestPdfToolWithRealPdf:
    """使用真实 PDF 文件的测试"""

    @pytest.fixture
    def sample_pdf_path(self, tmp_path):
        """创建一个简单的测试 PDF 文件"""
        try:
            import fitz
        except ImportError:
            pytest.skip("PyMuPDF not installed")

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()

        # 添加第一页
        page1 = doc.new_page()
        page1.insert_text((100, 100), "This is page 1 content")

        # 添加第二页
        page2 = doc.new_page()
        page2.insert_text((100, 100), "This is page 2 content")

        # 添加第三页
        page3 = doc.new_page()
        page3.insert_text((100, 100), "This is page 3 content")

        doc.save(str(pdf_path))
        doc.close()

        return str(pdf_path)

    @pytest.mark.asyncio
    async def test_read_all_pages(self, sample_pdf_path):
        """测试读取所有页面"""
        result = await pdf_read("test-id", {"file_path": sample_pdf_path})

        assert isinstance(result, AgentToolResult)
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)

        text = result.content[0].text
        assert "page 1" in text
        assert "page 2" in text
        assert "page 3" in text

        assert result.details["file_path"] == sample_pdf_path
        assert result.details["start_page"] == 1
        assert result.details["text_length"] > 0
        assert result.details["truncated"] is False

    @pytest.mark.asyncio
    async def test_read_specific_pages(self, sample_pdf_path):
        """测试读取特定页面范围"""
        result = await pdf_read(
            "test-id",
            {"file_path": sample_pdf_path, "start_page": 2, "end_page": 2}
        )

        text = result.content[0].text
        assert "page 2" in text
        assert "page 1" not in text
        assert "page 3" not in text

        assert result.details["start_page"] == 2
        assert result.details["end_page"] == 2

    @pytest.mark.asyncio
    async def test_read_page_range(self, sample_pdf_path):
        """测试读取页面范围"""
        result = await pdf_read(
            "test-id",
            {"file_path": sample_pdf_path, "start_page": 1, "end_page": 2}
        )

        text = result.content[0].text
        assert "page 1" in text
        assert "page 2" in text
        assert "page 3" not in text

    @pytest.mark.asyncio
    async def test_max_chars_truncation(self, sample_pdf_path):
        """测试最大字符数截断"""
        result = await pdf_read(
            "test-id",
            {"file_path": sample_pdf_path, "max_chars": 50}
        )

        text = result.content[0].text
        assert "(content truncated)" in text
        assert result.details["truncated"] is True

    @pytest.mark.asyncio
    async def test_with_update_callback(self, sample_pdf_path):
        """测试带进度回调的读取"""
        updates = []

        def on_update(result):
            updates.append(result)

        result = await pdf_read(
            "test-id",
            {"file_path": sample_pdf_path},
            on_update=on_update
        )

        assert len(updates) == 2
        assert updates[0].details["status"] == "started"
        assert updates[1].details["status"] == "completed"


class TestExtractPdfText:
    """测试 _extract_pdf_text 函数"""

    @pytest.fixture
    def sample_pdf_path(self, tmp_path):
        """创建一个简单的测试 PDF 文件"""
        try:
            import fitz
        except ImportError:
            pytest.skip("PyMuPDF not installed")

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Test content")
        doc.save(str(pdf_path))
        doc.close()

        return str(pdf_path)

    def test_extract_with_invalid_start_page(self, sample_pdf_path):
        """测试无效的起始页码"""
        with pytest.raises(RuntimeError, match="exceeds total pages"):
            _extract_pdf_text(sample_pdf_path, start_page=100)

    def test_extract_with_invalid_page_range(self, sample_pdf_path):
        """测试无效的页面范围"""
        with pytest.raises(RuntimeError, match="must be greater than"):
            _extract_pdf_text(sample_pdf_path, start_page=1, end_page=1)

    def test_extract_empty_pdf(self, tmp_path):
        """测试空 PDF 文件"""
        try:
            import fitz
        except ImportError:
            pytest.skip("PyMuPDF not installed")

        pdf_path = tmp_path / "empty.pdf"
        doc = fitz.open()
        doc.new_page()  # 空页面
        doc.save(str(pdf_path))
        doc.close()

        result = _extract_pdf_text(str(pdf_path))
        assert result == ""


import pytest
from services.report_generator import ReportGenerator
from models.schemas import AuditReport, SectionAuditResult
import os


def test_generate_report():
    """测试生成审计报告docx"""
    report_data = AuditReport(
        sections=[
            SectionAuditResult(
                section_name="付款条款",
                original_content="买方应在收到发票后30日内支付货款。",
                risk_level="合规",
                violated_regulations=[],
                reason="条款符合增值税发票管理规定",
                suggestion=""
            ),
            SectionAuditResult(
                section_name="违约条款",
                original_content="逾期按日利率0.05%计算违约金。",
                risk_level="高风险",
                violated_regulations=["合同法第114条"],
                reason="违约金比例偏高，可能超过实际损失30%",
                suggestion="建议调整违约金比例至日利率0.03%以下"
            )
        ],
        summary="共审计2个章节，1个高风险条款需要关注"
    )

    generator = ReportGenerator()
    output_path = generator.generate(report_data, "test_output.docx")

    # 验证文件存在
    assert os.path.exists(output_path)

    # 清理
    os.unlink(output_path)


def test_generate_report_with_non_compliant_section():
    """测试包含不合规条款的报告生成"""
    report_data = AuditReport(
        sections=[
            SectionAuditResult(
                section_name="发票条款",
                original_content="买方无需开具发票。",
                risk_level="不合规",
                violated_regulations=["增值税暂行条例第21条"],
                reason="违反发票管理规定，必须开具发票",
                suggestion="修改为：买方应按税法规定开具增值税发票"
            )
        ],
        summary="共审计1个章节，1个不合规条款需立即修改"
    )

    generator = ReportGenerator()
    output_path = generator.generate(report_data, "test_non_compliant.docx")

    assert os.path.exists(output_path)
    os.unlink(output_path)


def test_generate_report_empty():
    """测试空报告生成"""
    report_data = AuditReport(
        sections=[],
        summary="无审计内容"
    )

    generator = ReportGenerator()
    output_path = generator.generate(report_data, "test_empty.docx")

    assert os.path.exists(output_path)
    os.unlink(output_path)
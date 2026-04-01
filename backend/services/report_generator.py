from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from models.schemas import AuditReport, SectionAuditResult
import os
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """生成审计报告docx"""

    def generate(self, report: AuditReport, output_filename: str = "审计报告.docx") -> str:
        """
        生成审计报告

        Args:
            report: 审计报告数据
            output_filename: 输出文件名

        Returns:
            生成的文件路径
        """
        doc = Document()

        # 标题
        title = doc.add_heading("税务合同审计报告", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 整体摘要
        doc.add_heading("审计摘要", level=1)
        doc.add_paragraph(report.summary)

        # 统计信息
        compliant_count = sum(1 for s in report.sections if s.risk_level == "合规")
        high_risk_count = sum(1 for s in report.sections if s.risk_level == "高风险")
        non_compliant_count = sum(1 for s in report.sections if s.risk_level == "不合规")

        stats_para = doc.add_paragraph()
        stats_para.add_run(f"合规条款: {compliant_count}  ")
        high_risk_run = stats_para.add_run(f"高风险条款: {high_risk_count}  ")
        high_risk_run.bold = True
        non_compliant_run = stats_para.add_run(f"不合规条款: {non_compliant_count}  ")
        non_compliant_run.bold = True

        # 各章节详情
        doc.add_heading("详细分析", level=1)

        for section in report.sections:
            self._add_section(doc, section)

        # 保存文件
        output_path = os.path.join(os.getcwd(), output_filename)
        doc.save(output_path)
        logger.info(f"Report saved to {output_path}")

        return output_path

    def _add_section(self, doc: Document, section: SectionAuditResult):
        """添加单个章节的分析结果"""

        # 章节标题
        doc.add_heading(section.section_name, level=2)

        # 风险等级（颜色标记）
        risk_para = doc.add_paragraph()
        risk_para.add_run("风险等级: ").bold = True

        risk_run = risk_para.add_run(section.risk_level)
        if section.risk_level == "不合规":
            risk_run.font.color.rgb = RGBColor(255, 0, 0)  # 红色
            risk_run.bold = True
        elif section.risk_level == "高风险":
            risk_run.font.color.rgb = RGBColor(255, 165, 0)  # 橙色
            risk_run.bold = True
        else:
            risk_run.font.color.rgb = RGBColor(0, 128, 0)  # 绿色

        # 条款原文
        doc.add_paragraph().add_run("条款原文:").bold = True
        doc.add_paragraph(section.original_content)

        # 违反法规
        if section.violated_regulations:
            doc.add_paragraph().add_run("违反法规:").bold = True
            for reg in section.violated_regulations:
                doc.add_paragraph(f"  - {reg}", style="List Bullet")

        # 原因分析
        if section.reason:
            doc.add_paragraph().add_run("原因分析:").bold = True
            doc.add_paragraph(section.reason)

        # 修改建议
        if section.suggestion:
            doc.add_paragraph().add_run("修改建议:").bold = True
            suggestion_para = doc.add_paragraph(section.suggestion)
            suggestion_para.runs[0].font.color.rgb = RGBColor(0, 100, 0)

        # 分隔线
        doc.add_paragraph("─" * 40)
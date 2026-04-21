"""
报告导出服务

生成 PDF/图片格式的评估报告
"""

import os
import io
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReportResult:
    """报告生成结果 DTO"""
    success: bool
    pdf_path: Optional[str] = None
    image_path: Optional[str] = None
    error_message: Optional[str] = None


class ReportService:
    """
    报告导出服务

    生成包含评分、图表、建议的完整报告
    """

    def __init__(self, output_dir: Path):
        """
        初始化报告服务

        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_pdf_report(
        self,
        analysis_result: Dict,
        filename: str
    ) -> ReportResult:
        """
        生成 PDF 报告

        Args:
            analysis_result: 分析结果字典
            filename: 文件名

        Returns:
            ReportResult: 生成结果
        """
        try:
            # 尝试导入 ReportLab
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import cm
                from reportlab.lib.colors import HexColor
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
                from reportlab.lib import colors
            except ImportError:
                logger.warning("ReportLab 未安装，使用图片报告替代")
                return self.generate_image_report(analysis_result, filename)

            # 创建 PDF
            pdf_path = self.output_dir / f"{filename}_report.pdf"
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )

            # 样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                textColor=HexColor('#3b82f6'),
                spaceAfter=30
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=HexColor('#1e293b'),
                spaceBefore=20,
                spaceAfter=10
            )
            body_style = styles['Normal']

            # 内容
            story = []

            # 标题
            story.append(Paragraph("声乐评估报告", title_style))
            story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
            story.append(Spacer(1, 20))

            # 基本信息
            story.append(Paragraph("📊 基本信息", heading_style))
            basic_info = analysis_result.get('basic_info', {})
            basic_data = [
                ['文件名', basic_info.get('filename', '--')],
                ['时长', basic_info.get('duration', '--')],
                ['采样率', f"{basic_info.get('sample_rate', '--')} Hz"],
                ['文件大小', basic_info.get('file_size', '--')]
            ]
            basic_table = Table(basic_data, colWidths=[4*cm, 10*cm])
            basic_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0, 0), (0, -1), HexColor('#64748b')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(basic_table)

            # 总评分
            story.append(Paragraph("🏆 综合评分", heading_style))
            total_score = analysis_result.get('total_score', 0)
            level = analysis_result.get('level', '--')
            score_color = self._get_score_color(total_score)

            score_data = [
                ['总分', f"{total_score:.1f} 分"],
                ['等级', level],
                ['评价', self._get_score_comment(total_score)]
            ]
            score_table = Table(score_data, colWidths=[4*cm, 10*cm])
            score_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), HexColor('#eff6ff')),
                ('TEXTCOLOR', (1, 0), (1, 0), HexColor(score_color)),
                ('FONTSIZE', (1, 0), (1, 0), 16),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(score_table)

            # 五维评分
            story.append(Paragraph("📈 五维评分", heading_style))
            scores = analysis_result.get('scores', {})
            dim_names = {'volume': '音量', 'pitch': '音准', 'rhythm': '节奏', 'breath': '气息', 'emotion': '情绪'}
            scores_data = [['维度', '分数', '评价']]
            for key, name in dim_names.items():
                score = scores.get(key, 0)
                scores_data.append([name, f"{score:.1f}", self._get_dim_comment(key, score)])

            scores_table = Table(scores_data, colWidths=[4*cm, 3*cm, 7*cm])
            scores_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#f8fafc')]),
            ]))
            story.append(scores_table)

            # 音色分析
            timbre = analysis_result.get('timbre')
            if timbre:
                story.append(Paragraph("🎨 音色分析", heading_style))
                timbre_data = [
                    ['明亮度', f"{timbre.get('brightness', 0) * 100:.0f}%"],
                    ['温暖度', f"{timbre.get('warmth', 0) * 100:.0f}%"],
                    ['鼻音占比', f"{timbre.get('nasality', 0) * 100:.0f}%"],
                    ['气声占比', f"{timbre.get('breathiness', 0) * 100:.0f}%"],
                    ['HNR', f"{timbre.get('hnr', 0):.1f} dB"],
                    ['音色风格', timbre.get('style', '--')]
                ]
                timbre_table = Table(timbre_data, colWidths=[4*cm, 10*cm])
                timbre_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), HexColor('#faf5ff')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(timbre_table)

            # 改进建议
            advice = analysis_result.get('advice', [])
            if advice:
                story.append(Paragraph("💡 改进建议", heading_style))
                for a in advice:
                    story.append(Paragraph(f"• {a}", body_style))

            # 可视化图片
            visualization = analysis_result.get('visualization')
            if visualization:
                story.append(Paragraph("📊 音频特征可视化", heading_style))
                combined_path = visualization.get('combined')
                if combined_path:
                    # 转换为绝对路径
                    img_path = Path('web/static') / combined_path.lstrip('/static/')
                    if img_path.exists():
                        img = Image(str(img_path), width=15*cm, height=10*cm)
                        story.append(img)

            # 构建 PDF
            doc.build(story)

            return ReportResult(
                success=True,
                pdf_path=str(pdf_path)
            )

        except Exception as e:
            logger.exception("PDF 生成失败")
            return ReportResult(
                success=False,
                error_message=str(e)
            )

    def generate_image_report(
        self,
        analysis_result: Dict,
        filename: str
    ) -> ReportResult:
        """
        生成图片报告

        使用 matplotlib 生成报告图片

        Args:
            analysis_result: 分析结果字典
            filename: 文件名

        Returns:
            ReportResult: 生成结果
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            import numpy as np

            # 创建大图
            fig = plt.figure(figsize=(12, 16))
            fig.patch.set_facecolor('#f8fafc')

            # 标题区域
            ax_title = fig.add_axes([0.1, 0.92, 0.8, 0.06])
            ax_title.axis('off')
            ax_title.text(0.5, 0.5, '声乐评估报告', fontsize=28, fontweight='bold',
                         ha='center', va='center', color='#3b82f6')
            ax_title.text(0.5, 0.1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                         fontsize=12, ha='center', va='center', color='#64748b')

            # 基本信息区域
            ax_info = fig.add_axes([0.1, 0.78, 0.8, 0.12])
            ax_info.axis('off')
            ax_info.set_facecolor('#ffffff')

            basic_info = analysis_result.get('basic_info', {})
            info_text = f"文件名: {basic_info.get('filename', '--')}    时长: {basic_info.get('duration', '--')}    采样率: {basic_info.get('sample_rate', '--')} Hz"
            ax_info.text(0.5, 0.7, '📊 基本信息', fontsize=14, fontweight='bold', ha='center', va='center')
            ax_info.text(0.5, 0.3, info_text, fontsize=11, ha='center', va='center', color='#475569')

            # 总评分区域
            ax_total = fig.add_axes([0.1, 0.60, 0.8, 0.15])
            ax_total.axis('off')

            total_score = analysis_result.get('total_score', 0)
            level = analysis_result.get('level', '--')
            score_color = self._get_score_color(total_score)

            # 画大圆
            circle = plt.Circle((0.3, 0.5), 0.35, color=score_color, alpha=0.1)
            ax_total.add_patch(circle)
            ax_total.text(0.3, 0.55, f'{total_score:.0f}', fontsize=48, fontweight='bold',
                         ha='center', va='center', color=score_color)
            ax_total.text(0.3, 0.25, '分', fontsize=16, ha='center', va='center', color='#64748b')
            ax_total.text(0.7, 0.6, f'等级: {level}', fontsize=16, ha='center', va='center', fontweight='bold')
            ax_total.text(0.7, 0.4, self._get_score_comment(total_score), fontsize=12, ha='center', va='center', color='#64748b')

            # 五维评分柱状图
            ax_scores = fig.add_axes([0.15, 0.35, 0.7, 0.22])
            scores = analysis_result.get('scores', {})
            dim_names = ['音量', '音准', '节奏', '气息', '情绪']
            dim_keys = ['volume', 'pitch', 'rhythm', 'breath', 'emotion']
            values = [scores.get(k, 0) for k in dim_keys]
            colors = ['#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444']

            bars = ax_scores.barh(dim_names, values, color=colors, height=0.6)
            ax_scores.set_xlim(0, 100)
            ax_scores.set_title('📈 五维评分', fontsize=14, fontweight='bold', loc='left', pad=10)

            for bar, val in zip(bars, values):
                ax_scores.text(val + 2, bar.get_y() + bar.get_height()/2,
                              f'{val:.1f}', va='center', fontsize=11, fontweight='bold')

            ax_scores.spines['top'].set_visible(False)
            ax_scores.spines['right'].set_visible(False)

            # 音色分析
            timbre = analysis_result.get('timbre')
            if timbre:
                ax_timbre = fig.add_axes([0.15, 0.18, 0.7, 0.14])
                ax_timbre.axis('off')

                ax_timbre.text(0, 0.9, '🎨 音色分析', fontsize=14, fontweight='bold')
                timbre_text = f"明亮度: {timbre.get('brightness', 0)*100:.0f}%    温暖度: {timbre.get('warmth', 0)*100:.0f}%    " \
                             f"鼻音: {timbre.get('nasality', 0)*100:.0f}%    气声: {timbre.get('breathiness', 0)*100:.0f}%    " \
                             f"HNR: {timbre.get('hnr', 0):.1f} dB"
                ax_timbre.text(0, 0.5, timbre_text, fontsize=11, color='#475569')
                ax_timbre.text(0, 0.1, f"音色风格: {timbre.get('style', '--')}", fontsize=12, fontweight='bold', color='#8b5cf6')

            # 改进建议
            advice = analysis_result.get('advice', [])
            if advice:
                ax_advice = fig.add_axes([0.15, 0.02, 0.7, 0.14])
                ax_advice.axis('off')

                ax_advice.text(0, 0.9, '💡 改进建议', fontsize=14, fontweight='bold')
                for i, a in enumerate(advice[:4]):
                    ax_advice.text(0, 0.6 - i*0.2, f'• {a}', fontsize=10, color='#475569')

            # 保存
            img_path = self.output_dir / f"{filename}_report.png"
            plt.savefig(str(img_path), dpi=150, bbox_inches='tight', facecolor='#f8fafc')
            plt.close()

            return ReportResult(
                success=True,
                image_path=str(img_path)
            )

        except Exception as e:
            logger.exception("图片报告生成失败")
            return ReportResult(
                success=False,
                error_message=str(e)
            )

    def _get_score_color(self, score: float) -> str:
        """获取分数颜色"""
        if score >= 90:
            return '#22c55e'
        elif score >= 80:
            return '#3b82f6'
        elif score >= 70:
            return '#f59e0b'
        elif score >= 60:
            return '#f97316'
        return '#ef4444'

    def _get_score_comment(self, score: float) -> str:
        """获取分数评价"""
        if score >= 90:
            return "表现优秀，继续保持！"
        elif score >= 80:
            return "表现良好，有小幅提升空间"
        elif score >= 70:
            return "表现中等，需要加强练习"
        elif score >= 60:
            return "基础需要加强"
        return "需要重点关注和练习"

    def _get_dim_comment(self, dim: str, score: float) -> str:
        """获取维度评价"""
        comments = {
            'volume': {
                'high': '音量控制出色',
                'mid': '音量适中',
                'low': '音量偏小，注意气息支持'
            },
            'pitch': {
                'high': '音准非常准确',
                'mid': '音准基本准确',
                'low': '音准需要加强练习'
            },
            'rhythm': {
                'high': '节奏感很强',
                'mid': '节奏基本稳定',
                'low': '节奏感需要提升'
            },
            'breath': {
                'high': '气息控制优秀',
                'mid': '气息基本稳定',
                'low': '气息需要加强训练'
            },
            'emotion': {
                'high': '情感表达丰富',
                'mid': '情感表达适度',
                'low': '可以增加情感投入'
            }
        }

        dim_comments = comments.get(dim, {})
        if score >= 85:
            return dim_comments.get('high', '表现优秀')
        elif score >= 70:
            return dim_comments.get('mid', '表现良好')
        return dim_comments.get('low', '需要提升')

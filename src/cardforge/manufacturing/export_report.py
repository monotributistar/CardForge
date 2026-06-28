"""Manufacturing report exporter — writes reports as JSON and Markdown."""

import json
from pathlib import Path

from cardforge.manufacturing.report import ManufacturingReport


def export_report_json(report: ManufacturingReport, output_path: Path) -> Path:
    """Export the manufacturing report as JSON.

    Args:
        report: The manufacturing report to export.
        output_path: Where to write the JSON file.

    Returns:
        The output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = report.to_dict()
    output_path.write_text(json.dumps(data, indent=2))
    return output_path


def export_report_markdown(report: ManufacturingReport, output_path: Path) -> Path:
    """Export the manufacturing report as Markdown.

    Args:
        report: The manufacturing report to export.
        output_path: Where to write the Markdown file.

    Returns:
        The output path.
    """
    lines = []
    lines.append(f"# Manufacturing Report")
    lines.append("")
    lines.append(f"**Profile:** {report.profile.process.upper()} — "
                 f"{report.profile.printer_name} ({report.profile.material})")
    lines.append(f"**Nozzle:** {report.profile.nozzle}mm | "
                 f"**Layer Height:** {report.profile.layer_height}mm")
    lines.append("")
    lines.append(f"## Score: {report.score}/100 — {report.score_label}")
    lines.append("")
    lines.append(f"**Status:** {'✅ Manufacturable' if report.is_manufacturable else '❌ Not manufacturable'}")
    lines.append("")

    # Issues summary
    lines.append("## Issues")
    lines.append("")
    lines.append(f"| Severity | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| 🔴 Error | {len(report.errors)} |")
    lines.append(f"| 🟡 Warning | {len(report.warnings)} |")
    lines.append(f"| 🔵 Info | {len(report.infos)} |")
    lines.append("")

    # Detailed issues
    if report.issues:
        lines.append("## Details")
        lines.append("")
        for issue in report.issues:
            icon = {"error": "🔴", "warning": "🟡", "info": "🔵", "fatal": "💀"}.get(
                issue.severity.value, "•")
            lines.append(f"- {icon} **{issue.severity.value.upper()}**: {issue.message}")
            if issue.suggestion:
                lines.append(f"  → {issue.suggestion}")
        lines.append("")

    # Suggestions
    if report.suggestions:
        lines.append("## Suggestions")
        lines.append("")
        for s in report.suggestions:
            lines.append(f"- {s}")
        lines.append("")

    # Metrics
    metrics = report.metrics.to_dict()
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    metric_labels = [
        ("feature_count", "Features"),
        ("svg_count", "SVG elements"),
        ("text_count", "Text elements"),
        ("smallest_line_mm", "Smallest line"),
        ("smallest_emboss_mm", "Smallest emboss"),
        ("smallest_deboss_mm", "Smallest deboss"),
        ("smallest_text_mm", "Smallest text"),
        ("smallest_qr_mm", "Smallest QR"),
        ("min_wall_mm", "Minimum wall"),
    ]
    for key, label in metric_labels:
        val = metrics.get(key, 0)
        if val and val != 999.0:
            lines.append(f"| {label} | {val} mm |")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    return output_path

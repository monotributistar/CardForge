"""Manufacturing report console formatter — human-readable output."""

from cardforge.manufacturing.report import ManufacturingReport


def format_report_console(report: ManufacturingReport) -> str:
    """Format a manufacturing report for console output.

    Args:
        report: The manufacturing report.

    Returns:
        Formatted string ready for print.
    """
    lines = []
    lines.append("")
    lines.append("─" * 46)
    lines.append("Manufacturing Analysis")
    lines.append(f"Profile: {report.profile.printer_name} "
                 f"({report.profile.material}, {report.profile.nozzle}mm)")
    lines.append(f"Score: {report.score}/100 — {report.score_label}")
    lines.append(f"Status: {'Manufacturable' if report.is_manufacturable else 'Not manufacturable'}")
    lines.append("")

    if report.errors:
        lines.append("Errors:")
        for e in report.errors:
            lines.append(f"  - {e.message}")
        lines.append("")

    if report.warnings:
        lines.append("Warnings:")
        for w in report.warnings:
            lines.append(f"  - {w.message}")
        lines.append("")

    if report.suggestions:
        lines.append("Suggestions:")
        for s in report.suggestions:
            lines.append(f"  - {s}")
        lines.append("")

    if not report.is_manufacturable:
        lines.append("Build blocked before STL export.")
        lines.append("Use --ignore-manufacturing-errors to override.")
        lines.append("")

    lines.append("─" * 46)
    return "\n".join(lines)

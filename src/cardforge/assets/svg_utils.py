"""SVG utility functions — header, footer, rect, text, group, sanitization."""

import html


def escape_xml(value: str) -> str:
    """Escape special XML characters in a string."""
    return html.escape(value, quote=True)


def sanitize_svg_id(value: str) -> str:
    """Convert a string into a valid SVG id (no spaces, special chars)."""
    import re
    # Replace anything that's not alphanumeric, dash, or underscore with dash
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", value)
    # Remove leading dashes/digits that would make it invalid
    sanitized = re.sub(r"^-+", "", sanitized)
    if not sanitized:
        return "id"
    return sanitized.lower()


def svg_header(width_mm: float, height_mm: float, viewbox: str = None) -> str:
    """Generate an SVG opening tag with mm units."""
    vb = viewbox or f"0 0 {width_mm} {height_mm}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="{vb}">'
    )


def svg_footer() -> str:
    """Generate SVG closing tag."""
    return "</svg>"


def svg_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    rx: float = 0,
    ry: float = 0,
    fill: str = None,
    stroke: str = None,
    stroke_width: float = None,
    class_name: str = None,
) -> str:
    """Generate an SVG <rect> element."""
    parts = [f'<rect x="{x}" y="{y}" width="{width}" height="{height}"']
    if rx:
        parts.append(f' rx="{rx}"')
    if ry:
        parts.append(f' ry="{ry}"')
    if fill:
        parts.append(f' fill="{escape_xml(fill)}"')
    if stroke:
        parts.append(f' stroke="{escape_xml(stroke)}"')
    if stroke_width is not None:
        parts.append(f' stroke-width="{stroke_width}"')
    if class_name:
        parts.append(f' class="{escape_xml(class_name)}"')
    parts.append("/>")
    return "".join(parts)


def svg_text(
    x: float,
    y: float,
    text: str,
    font_family: str = "sans-serif",
    font_size: float = 12,
    font_weight: str = "normal",
    fill: str = None,
    text_anchor: str = "start",
    class_name: str = None,
) -> str:
    """Generate an SVG <text> element."""
    parts = [
        f'<text x="{x}" y="{y}"',
        f' font-family="{escape_xml(font_family)}"',
        f' font-size="{font_size}"',
        f' font-weight="{font_weight}"',
    ]
    if fill:
        parts.append(f' fill="{escape_xml(fill)}"')
    if text_anchor != "start":
        parts.append(f' text-anchor="{text_anchor}"')
    if class_name:
        parts.append(f' class="{escape_xml(class_name)}"')
    parts.append(f">{escape_xml(text)}</text>")
    return "".join(parts)


def svg_image(
    x: float,
    y: float,
    width: float,
    height: float,
    href: str,
    class_name: str = None,
) -> str:
    """Generate an SVG <image> element."""
    parts = [
        f'<image x="{x}" y="{y}" width="{width}" height="{height}"',
        f' href="{escape_xml(href)}"',
    ]
    if class_name:
        parts.append(f' class="{escape_xml(class_name)}"')
    parts.append("/>")
    return "".join(parts)


def svg_group(
    children: str = "",
    transform: str = None,
    class_name: str = None,
    id: str = None,
) -> str:
    """Wrap content in an SVG <g> group element."""
    parts = ["<g"]
    if transform:
        parts.append(f' transform="{escape_xml(transform)}"')
    if class_name:
        parts.append(f' class="{escape_xml(class_name)}"')
    if id:
        parts.append(f' id="{sanitize_svg_id(id)}"')
    parts.append(f">{children}</g>")
    return "".join(parts)


def svg_comment(text: str) -> str:
    """Generate an HTML/SVG comment."""
    safe = text.replace("--", "- -")
    return f"<!-- {safe} -->"

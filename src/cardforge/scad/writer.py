"""SCAD Writer — builds OpenSCAD code with proper indentation and formatting."""

from cardforge.scad.expressions import comment, section_header, include_module, module_call


class ScadWriter:
    """Builds an OpenSCAD .scad file programmatically."""

    def __init__(self):
        self._lines = []
        self._indent = 0

    def line(self, text: str = "") -> None:
        """Add a line at current indentation."""
        prefix = "    " * self._indent
        self._lines.append(f"{prefix}{text}")

    def comment(self, text: str) -> None:
        self.line(comment(text))

    def section(self, text: str) -> None:
        self._lines.append(section_header(text))

    def include(self, path: str) -> None:
        self.line(include_module(path))

    def module_call(self, name: str, **kwargs) -> None:
        self.line(module_call(name, **kwargs))

    def blank_line(self) -> None:
        self._lines.append("")

    def push_indent(self) -> None:
        self._indent += 1

    def pop_indent(self) -> None:
        self._indent = max(0, self._indent - 1)

    def open_block(self, text: str) -> None:
        """Open a module or block with { and increase indent."""
        prefix = "    " * self._indent
        self._lines.append(f"{prefix}{text} {{")
        self._indent += 1

    def close_block(self) -> None:
        """Close a block with } and decrease indent."""
        self._indent = max(0, self._indent - 1)
        prefix = "    " * self._indent
        self._lines.append(f"{prefix}}}")

    def translate(self, x: float, y: float, z: float) -> None:
        """Open a translate block."""
        from cardforge.scad.expressions import vector3
        self.open_block(f"translate({vector3(x, y, z)})")

    def mirror_z(self) -> None:
        """Open a mirror block for z-axis flip (back face)."""
        self.open_block("mirror([0, 0, 1])")

    def difference(self) -> None:
        """Open a difference block."""
        self.open_block("difference()")

    def build(self) -> str:
        """Return the complete SCAD source code."""
        return "\n".join(self._lines)

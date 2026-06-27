"""SCAD expressions — safe value formatting for OpenSCAD code generation."""


def escape_string(value: str) -> str:
    """Escape a string for use in an OpenSCAD string literal."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def number(value: float) -> str:
    """Format a number for OpenSCAD."""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def vector2(x: float, y: float) -> str:
    """Format a 2D vector: [x, y]."""
    return f"[{number(x)}, {number(y)}]"


def vector3(x: float, y: float, z: float) -> str:
    """Format a 3D vector: [x, y, z]."""
    return f"[{number(x)}, {number(y)}, {number(z)}]"


def module_call(name: str, **kwargs) -> str:
    """Generate an OpenSCAD module call.

    Example:
        module_call("card_base", width=85, height=54, thickness=1.8, radius=4)
        → 'card_base(width=85, height=54, thickness=1.8, radius=4);'
    """
    params = []
    for key, value in kwargs.items():
        if isinstance(value, str):
            params.append(f"{key}={escape_string(value)}")
        elif isinstance(value, bool):
            params.append(f"{key}={'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            params.append(f"{key}={number(value)}")
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            params.append(f"{key}={vector2(value[0], value[1])}")
        elif isinstance(value, (list, tuple)) and len(value) == 3:
            params.append(f"{key}={vector3(value[0], value[1], value[2])}")
        else:
            params.append(f"{key}={value}")
    return f"{name}({', '.join(params)});"


def comment(text: str) -> str:
    """Format an OpenSCAD comment line."""
    return f"// {text}"


def section_header(text: str) -> str:
    """Format a section header comment block."""
    line = "// " + "-" * 58
    return f"\n{line}\n// {text}\n{line}\n"


def include_module(path: str) -> str:
    """Generate an include statement."""
    return f'include <{path}>;'

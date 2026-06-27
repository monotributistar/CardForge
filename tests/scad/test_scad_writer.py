"""Tests for SCAD expressions and writer."""

import pytest
from cardforge.scad.expressions import (
    escape_string,
    number,
    vector2,
    vector3,
    module_call,
    comment,
    section_header,
    include_module,
)
from cardforge.scad.writer import ScadWriter


class TestExpressions:
    def test_escape_string_basic(self):
        assert escape_string("hello") == '"hello"'

    def test_escape_quotes(self):
        result = escape_string('say "hi"')
        assert '\\"' in result

    def test_number_int(self):
        assert number(42) == "42"

    def test_number_float(self):
        assert number(3.5) == "3.5"

    def test_number_removes_trailing_zeros(self):
        assert number(1.0) == "1"

    def test_vector2(self):
        assert vector2(10, 20) == "[10, 20]"

    def test_vector3(self):
        assert vector3(1, 2, 3) == "[1, 2, 3]"

    def test_module_call_simple(self):
        result = module_call("card_base", width=85, height=54, thickness=1.8)
        assert "card_base(" in result
        assert "width=85" in result
        assert "height=54" in result
        assert result.endswith(");")

    def test_module_call_with_string(self):
        result = module_call("text", text_value="Hello")
        assert '"Hello"' in result

    def test_module_call_with_bool(self):
        result = module_call("debug", show=True)
        assert "true" in result

    def test_module_call_with_vector(self):
        result = module_call("translate", pos=(1, 2))
        assert "[1, 2]" in result

    def test_module_call_with_vector3(self):
        result = module_call("translate", pos=(1, 2, 3))
        assert "[1, 2, 3]" in result

    def test_comment(self):
        c = comment("hello world")
        assert c.startswith("//")
        assert "hello world" in c

    def test_section_header(self):
        s = section_header("Front Face")
        assert "Front Face" in s
        assert "---" in s

    def test_include_module(self):
        i = include_module("main.scad")
        assert "main.scad" in i
        assert i.startswith("include")


class TestScadWriter:
    def test_empty_writer(self):
        w = ScadWriter()
        assert w.build() == ""

    def test_header_and_comment(self):
        w = ScadWriter()
        w.comment("CardForge auto-generated")
        output = w.build()
        assert "CardForge" in output

    def test_module_call_line(self):
        w = ScadWriter()
        w.module_call("card_base", width=85, height=54, thickness=1.8, radius=4)
        output = w.build()
        assert "card_base(" in output
        assert "width=85" in output

    def test_include(self):
        w = ScadWriter()
        w.include("main.scad")
        output = w.build()
        assert "include <main.scad>" in output

    def test_block_syntax(self):
        w = ScadWriter()
        w.open_block("translate([0, 0, 1.8])")
        w.line("cube([10, 10, 1]);")
        w.close_block()
        output = w.build()
        assert "translate([0, 0, 1.8]) {" in output
        assert "    cube([10, 10, 1]);" in output
        assert output.strip().endswith("}")

    def test_difference_block(self):
        w = ScadWriter()
        w.difference()
        w.line("cube([10, 10, 1]);")
        w.line("cube([5, 5, 2]);")
        w.close_block()
        output = w.build()
        assert "difference() {" in output

    def test_indent_push_pop(self):
        w = ScadWriter()
        w.line("root;")
        w.push_indent()
        w.line("child;")
        w.push_indent()
        w.line("grandchild;")
        w.pop_indent()
        w.line("child2;")
        w.pop_indent()
        w.line("root2;")
        output = w.build()
        lines = output.split("\n")
        assert lines[0] == "root;"
        assert lines[1] == "    child;"
        assert lines[2] == "        grandchild;"
        assert lines[3] == "    child2;"
        assert lines[4] == "root2;"

    def test_section(self):
        w = ScadWriter()
        w.section("Front Face")
        output = w.build()
        assert "Front Face" in output
        assert "// -----" in output

    def test_translate_shortcut(self):
        w = ScadWriter()
        w.translate(10, 20, 1.8)
        w.line("cube([5, 5, 1]);")
        w.close_block()
        output = w.build()
        assert "translate([10, 20, 1.8]) {" in output

// CardForge — Text Layer
// Renders text using OpenSCAD's built-in text() function.

// 2D text shape — the caller supplies the linear_extrude (Geometry IR path).
// Avoids a 3D-in-2D double extrusion when wrapped by an ExtrudeNode.
module text_shape_2d(text_value, font_size, font_name, halign, valign) {
    text(
        text = text_value,
        size = font_size,
        font = font_name,
        halign = halign,
        valign = valign
    );
}

// Self-extruding text layer (legacy generator path).
module text_emboss_layer(text_value, x, y, z, font_size, height, font_name, halign, valign) {
    translate([x, y, z])
    linear_extrude(height = height)
    text(
        text = text_value,
        size = font_size,
        font = font_name,
        halign = halign,
        valign = valign
    );
}

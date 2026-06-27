// CardForge — Text Layer
// Renders text using OpenSCAD's built-in text() function.

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

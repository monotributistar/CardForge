// CardForge — SVG Layer
// Imports an SVG file and extrudes it as a 3D layer.

module svg_emboss_layer(file, x, y, z, height, scale_factor) {
    translate([x, y, z])
    linear_extrude(height = height)
    scale([scale_factor, scale_factor, 1])
        import(file = file, center = true);
}

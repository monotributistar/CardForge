// CardForge — SVG Layer
// Imports an SVG file and extrudes it as a 3D layer.

// 2D SVG shape — the caller supplies the linear_extrude (Geometry IR path).
// Avoids a 3D-in-2D double extrusion when wrapped by an ExtrudeNode.
module svg_shape_2d(file, scale_factor) {
    scale([scale_factor, scale_factor, 1])
        import(file = file, center = true);
}

// Self-extruding SVG layer (legacy generator path).
module svg_emboss_layer(file, x, y, z, height, scale_factor) {
    translate([x, y, z])
    linear_extrude(height = height)
    scale([scale_factor, scale_factor, 1])
        import(file = file, center = true);
}

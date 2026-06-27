// CardForge — Rounded Rectangle 2D
// Creates a 2D rounded rectangle centered at origin.
//
// Coordinate system: centered at [0, 0]
// width, height in mm
// radius = corner rounding radius

module rounded_rect_2d(width, height, radius) {
    // OpenSCAD offset() creates rounded corners by shrinking then expanding
    // We create a sharp rectangle, then offset to round, then offset back
    if (radius > 0) {
        offset(r = radius)
        offset(delta = -radius)
        square([width, height], center = true);
    } else {
        square([width, height], center = true);
    }
}

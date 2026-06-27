// CardForge — Card Base
// Creates the solid base of the card object.
//
// centered at origin, z=0 sits on XY plane
// card extends from z=0 to z=thickness

include <rounded_rect.scad>;

module card_base(width, height, thickness, radius) {
    color("DimGray")
    linear_extrude(height = thickness, center = false)
        rounded_rect_2d(width, height, radius);
}

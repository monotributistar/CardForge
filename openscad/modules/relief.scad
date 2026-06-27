// CardForge — Relief Operations
// Centralized relief operations for features.

// emboss: union (feature sits on top of base)
module emboss(height) {
    children();
}

// deboss: subtract a shallow layer from the base
module deboss(depth, thickness) {
    difference() {
        children(0); // base
        translate([0, 0, thickness - depth])
        children(1); // feature to subtract
    }
}

// cut: full subtraction through the base
module cut(depth, thickness) {
    difference() {
        children(0); // base
        children(1); // feature to subtract
    }
}

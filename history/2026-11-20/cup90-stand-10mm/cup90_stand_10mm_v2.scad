// One-piece dropped cradle for probe_capped_head_v2, with 10 mm exposed tips.
// Cup OD/height approximately 90/90 mm. Print standing on the BACK edge.
// Default model is already rotated into the support-free printing orientation.
use <reference_head.scad>
$fn = 96;
part = "print"; // [print,installed,assembly,section,head_collision,cup_collision]

cup_outer_diameter = 90;
cup_height = 90;
span = 126;
depth = 40;
wall = 3;
thickness = 5;
head_width = 58;
head_depth = 38;
head_side_clearance = 0.6;
head_seat_below_rim = 20;
exposed_tip = 10;
water_below_rim = 22; // Initial example: 8 mm of each tip in water.
entry_width = 36.8;
entry_rear_y = 13.4;
rim_guide_gap = 94; // Outside rim guides, 2 mm clearance per side for 90 mm OD.
rim_guide_drop = 5;
head_bottom = -head_seat_below_rim;
floor_bottom = head_bottom - thickness;
inner_half = head_width / 2 + head_side_clearance;
outer_half = inner_half + wall;

module side_entry() {
    radius = 2;
    translate([0, 0, floor_bottom - 0.1])
        linear_extrude(height = thickness + 0.2)
            hull() {
                for (x = [-entry_width / 2 + radius, entry_width / 2 - radius]) {
                    translate([x, -depth / 2 - radius - 1]) circle(r = radius);
                    translate([x, entry_rear_y - radius]) circle(r = radius);
                }
            }
}

module installed_stand() {
    union() {
        difference() {
            translate([-outer_half, -depth / 2, floor_bottom])
                cube([2 * outer_half, depth, thickness]);
            side_entry();
        }
        // Side walls rise beside the full 58 x 38 mm lower head frame.
        // Rectangular profiles remain connected through every print layer.
        for (side = [-1, 1]) {
            translate([side < 0 ? -outer_half : inner_half, -depth / 2, floor_bottom])
                cube([wall, depth, head_seat_below_rim + 2 * thickness]);
            translate([side < 0 ? -span / 2 : inner_half, -depth / 2, 0])
                cube([span / 2 - inner_half, depth, thickness]);
            translate([side < 0 ? -rim_guide_gap / 2 - wall : rim_guide_gap / 2,
                       -depth / 2, -rim_guide_drop])
                cube([wall, depth, rim_guide_drop + 0.05]);
        }
    }
}

module printable_stand() {
    // Installed +Y back edge is the print bed. The opening finishes at the top.
    // Bounds in print orientation: X +/-63, Y +/-15, Z 0..40 mm.
    translate([0, 10, depth / 2]) rotate([-90, 0, 0]) installed_stand();
}

module exact_rigid_head() {
    // Actual rigid printed components of the CURRENT capped head, not v1.
    union() {
        retainer();
        translate([0, 0, 4]) cap_core();
        translate([0, 0, 29.75]) holder();
    }
}

module current_head() {
    color([0.89, 0.89, 0.86]) exact_rigid_head();
    color([0.92, 0.66, 0.25]) translate([0, 0, 29]) gasket();
    for (i = [0:2]) color([0.13, 0.13, 0.14]) compressed_seal(i);
    probes(); // Exact probe XY positions and three tips at z = -10 mm.
    for (p = [[-22.5, -12], [-22.5, 12], [22.5, -12], [22.5, 12]]) {
        color([0.60, 0.61, 0.63]) {
            translate([p[0], p[1], 23]) cylinder(d = 3, h = 25);
            translate([p[0], p[1], 47.75]) cylinder(d = 5.5, h = 2.5);
        }
    }
}

module cup_solid() {
    // Approximate tapered cup; actual Daiso spout/handle are not modelled.
    difference() {
        translate([0, 0, -cup_height]) cylinder(d1 = 66, d2 = cup_outer_diameter, h = cup_height);
        translate([0, 0, -cup_height + 3])
            cylinder(d1 = 62, d2 = cup_outer_diameter - 4, h = cup_height - 2.9);
    }
}

module water() {
    color([0.22, 0.61, 0.90, 0.20])
        translate([0, 0, -cup_height + 3])
            cylinder(d1 = 61.8,
                     d2 = 62 + (cup_outer_diameter - 4 - 62) *
                          (cup_height - 3 - water_below_rim) / (cup_height - 3),
                     h = cup_height - 3 - water_below_rim);
}

module assembly(section = false) {
    color([0.16, 0.43, 0.73]) installed_stand();
    translate([0, 0, head_bottom]) current_head();
    color([0.75, 0.80, 0.84, 0.23]) {
        if (section) {
            intersection() {
                cup_solid();
                translate([-60, 0, -100]) cube([120, 60, 110]);
            }
        } else cup_solid();
    }
    if (!section) water();
    else {
        color([0.22, 0.61, 0.90])
            translate([-30, -0.2, -water_below_rim]) cube([60, 0.4, 0.5]);
    }
}

assert(head_width == 58 && head_depth == 38 && exposed_tip == 10,
       "This version is specifically for the current capped head with 10 mm tips.");
assert(depth >= head_depth + 2);
assert(entry_rear_y >= 8 + 3.3 + 2, "Clear the temperature probe through-hole.");
assert(depth / 2 - entry_rear_y >= 6, "Keep the back of the lower cradle connected.");
assert(head_side_clearance >= 0.4);
assert(head_seat_below_rim + exposed_tip - water_below_rim > 0);
assert(water_below_rim > head_seat_below_rim, "Example water surface stays below the head plastic.");

if (part == "installed") installed_stand();
else if (part == "assembly") assembly();
else if (part == "section") assembly(true);
else if (part == "head_collision") {
    intersection() {
        installed_stand();
        translate([0, 0, head_bottom + 0.01]) exact_rigid_head();
    }
    intersection() {
        installed_stand();
        for (p = [[-10, -6], [10, -6], [0, 8]])
            translate([p[0], p[1], head_bottom - exposed_tip]) cylinder(d = 6.6, h = 65);
    }
}
else if (part == "cup_collision") {
    intersection() {
        installed_stand();
        translate([0, 0, -0.01]) cup_solid();
    }
}
else printable_stand();

// OBSOLETE FOR THE CURRENT 10 mm EXPOSED-TIP HEAD. Do not print for that head.
// Use ../../2026-11-20/cup90-stand-10mm/cup90_stand_10mm_v2.scad instead.
// One printed part for the existing 44 x 34 mm test head and an approximately
// 90 mm outside-diameter cup. Units are millimetres.
// Default geometry is already oriented for printing, broad flat face on bed.
// The cradle opens at one side so the assembled probes can enter sideways.
$fn = 96;
part = "print"; // [print,assembly,installed,interference]

cup_outer_diameter = 90;
cup_diameter_allowance = 6; // Total diameter allowance, 3 mm radial at nominal size.
plate_length = 126;
plate_width = 52;
plate_thickness = 5;
slot_width = 36.8;
slot_rear_y = 17.4;
guide_wall = 4;
guide_drop = 8;
guide_half_width = 18;

head_width = 44;
head_depth = 34;
head_height = 18;
head_rod_projection = 55; // Existing-head record. Verify assembled hardware.
temperature_projection = 40; // Assembly illustration only, not a measured length.
preview_cup_height = 90;
preview_water_below_rim = 25; // Example fill level, set the actual level by measurement.

guide_inner_diameter = cup_outer_diameter + cup_diameter_allowance;
guide_outer_diameter = guide_inner_diameter + 2 * guide_wall;

module rounded_plate(w, d, h, radius = 3) {
    linear_extrude(height = h)
        offset(r = radius) square([w - 2 * radius, d - 2 * radius], center = true);
}

module side_entry() {
    radius = 2;
    linear_extrude(height = plate_thickness + 0.2)
        hull() {
            for (x = [-slot_width / 2 + radius, slot_width / 2 - radius]) {
                translate([x, -plate_width / 2 - radius - 1]) circle(r = radius);
                translate([x, slot_rear_y - radius]) circle(r = radius);
            }
        }
}

module rim_guides() {
    // Two short outside guides leave the spout and handle directions open.
    // Guides and plate overlap, so the exported mesh is a single connected part.
    intersection() {
        difference() {
            cylinder(d = guide_outer_diameter, h = guide_drop + 0.05);
            translate([0, 0, -0.1])
                cylinder(d = guide_inner_diameter, h = guide_drop + 0.25);
        }
        translate([-guide_outer_diameter, -guide_half_width, -0.1])
            cube([2 * guide_outer_diameter, 2 * guide_half_width, guide_drop + 0.25]);
    }
}

module printable_stand() {
    union() {
        difference() {
            rounded_plate(plate_length, plate_width, plate_thickness);
            translate([0, 0, -0.1]) side_entry();
        }
        translate([0, 0, plate_thickness - 0.05]) rim_guides();
    }
}

module installed_stand() {
    // Turn the print over. Plate bottom is at the cup rim, z = 0.
    translate([0, 0, plate_thickness]) rotate([180, 0, 0]) printable_stand();
}

module reference_head() {
    // Existing head envelope and actual probe XY positions.
    // Side clamp hardware is shown schematically for orientation.
    difference() {
        rounded_plate(head_width, head_depth, head_height, 2);
        for (x = [-10, 10])
            translate([x, -6, -0.1]) cylinder(d = 5.5, h = head_height + 0.2);
        translate([0, 8, -0.1]) cylinder(d = 6.5, h = head_height + 0.2);
    }
}

module reference_probes() {
    for (x = [-10, 10])
        color([0.62, 0.64, 0.67])
            translate([x, -6, plate_thickness - head_rod_projection])
                cylinder(d = 5, h = head_rod_projection + head_height + 12);
    color([0.48, 0.51, 0.54])
        translate([0, 8, plate_thickness - temperature_projection]) cylinder(d = 6, h = 50);
    color([0.12, 0.12, 0.13])
        translate([0, 8, plate_thickness - temperature_projection + 50]) cylinder(d = 3, h = 22);
}

module reference_cup() {
    // A generic tapered cup, not an exact model of a Daiso product.
    color([0.75, 0.80, 0.85, 0.23])
        difference() {
            translate([0, 0, -preview_cup_height])
                cylinder(d1 = 66, d2 = cup_outer_diameter, h = preview_cup_height);
            translate([0, 0, -preview_cup_height + 3])
                cylinder(d1 = 62, d2 = cup_outer_diameter - 4, h = preview_cup_height - 2.9);
        }
    color([0.23, 0.60, 0.90, 0.18])
        translate([0, 0, -preview_cup_height + 3])
            cylinder(d1 = 61.8,
                     d2 = 62 + (cup_outer_diameter - 4 - 62) *
                          (preview_cup_height - 3 - preview_water_below_rim) / (preview_cup_height - 3),
                     h = preview_cup_height - 3 - preview_water_below_rim);
}

module reference_tape() {
    // Two dry tape strips hold the plastic head to the two side shelves.
    for (side = [-1, 1]) {
        x = side * (head_width / 2 - 1);
        color([0.93, 0.67, 0.25, 0.85]) {
            translate([x - 4, -4, plate_thickness + head_height]) cube([8, 8, 0.3]);
            translate([side < 0 ? -head_width / 2 - 0.3 : head_width / 2, -4, plate_thickness])
                cube([0.3, 8, head_height + 0.3]);
            translate([side < 0 ? -35 : head_width / 2, -4, plate_thickness])
                cube([35 - head_width / 2, 8, 0.3]);
        }
    }
}

module assembly() {
    color([0.17, 0.43, 0.72]) installed_stand();
    color([0.91, 0.91, 0.88]) translate([0, 0, plate_thickness]) reference_head();
    reference_probes();
    reference_tape();
    reference_cup();
}

assert(head_width > slot_width + 6, "Leave at least 3 mm head bearing on each side.");
assert(slot_rear_y > head_depth / 2, "The head must clear the rear edge of the opening.");
assert(plate_width / 2 - slot_rear_y >= 8, "Keep the rear bridge at least 8 mm wide.");
assert(guide_outer_diameter < plate_length - 10, "Rim guides must stay inside the plate footprint.");
assert(2 * guide_half_width < plate_width - 10);
assert(guide_inner_diameter > cup_outer_diameter);

if (part == "assembly") assembly();
else if (part == "installed") installed_stand();
else if (part == "interference") {
    intersection() {
        installed_stand();
        translate([0, 0, plate_thickness + 0.01]) reference_head();
    }
    intersection() {
        installed_stand();
        for (p = [[-10, -6], [10, -6], [0, 8]])
            translate([p[0], p[1], -5]) cylinder(d = 8, h = 36);
    }
}
else printable_stand();

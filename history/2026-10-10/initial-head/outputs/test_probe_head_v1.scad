// Test fixture only. Dimensions in mm. Not a food-contact or waterproof product.
// Source probe specification: Devicemart 15584272, metal tube diameter 6, length 50.
// Check actual hardware and print the fit coupon before printing the full head.
$fn = 96;
part = "head"; // [head,coupon,assembly]
rod_d = 5;
temp_d = 6;
hole_allowance = 0.5; // DIAMETRAL allowance, not radial.
rod_pitch = 20; // Experimental center distance, NOT an optimized cell constant.
width = 44;
depth = 34;
height = 18;
rod_y = -6;
temp_y = 8;
bolt_z = 7; // Temperature metal tube must extend at least 10 mm into the head.
screw_hole_d = 3.4;
nut_slot_width = 5.9; // M3 hex nut across flats 5.5 mm; printer dependent.
nut_slot_depth = 2.8;
nut_bottom = bolt_z - 3.3;
show_probes = true;
round_radius = 2;

module rounded_block(w,d,h,r=2) {
    linear_extrude(height=h)
        offset(r=r) square([w-2*r,d-2*r],center=true);
}
module axial_hole(x,y,d,h=height) {
    translate([x,y,-0.1]) cylinder(d=d,h=h+0.2);
}
module actual_clamp_port(x,side) {
    // side=-1: front face to rod; side=+1: rear face to temperature probe.
    if(side < 0) {
        translate([x,-12,bolt_z]) rotate([90,0,0])
            cylinder(d=screw_hole_d,h=12,center=true);
        translate([x-nut_slot_width/2,-13.5-nut_slot_depth/2,nut_bottom])
            cube([nut_slot_width,nut_slot_depth,height-nut_bottom+0.1]);
    } else {
        translate([x,13,bolt_z]) rotate([90,0,0])
            cylinder(d=screw_hole_d,h=10,center=true);
        translate([x-nut_slot_width/2,13.5-nut_slot_depth/2,nut_bottom])
            cube([nut_slot_width,nut_slot_depth,height-nut_bottom+0.1]);
    }
}
module head() {
    difference() {
        rounded_block(width,depth,height,round_radius);
        for(x=[-rod_pitch/2,rod_pitch/2]) {
            axial_hole(x,rod_y,rod_d+hole_allowance);
            actual_clamp_port(x,-1);
        }
        axial_hole(0,temp_y,temp_d+hole_allowance);
        actual_clamp_port(0,+1);
        // Optional mounting holes for an external support, not probe clamping holes.
        for(x=[-17,17]) axial_hole(x,8,3.4);
    }
}
module coupon() {
    // Three trial clearances for each diameter. Mark order left->right 0.3/0.5/0.7 mm.
    difference() {
        rounded_block(38,23,5,1);
        for(i=[0:2]) {
            axial_hole(-12+12*i,-5,rod_d+0.3+0.2*i,5);
            axial_hole(-12+12*i,5,temp_d+0.3+0.2*i,5);
        }
    }
}
module assembly() {
    color([0.14,0.52,0.61,0.75]) head();
    if(show_probes) {
        for(x=[-rod_pitch/2,rod_pitch/2])
            color([0.72,0.75,0.78]) translate([x,rod_y,-40]) cylinder(d=rod_d,h=100);
        color([0.52,0.56,0.60]) translate([0,temp_y,-40]) cylinder(d=temp_d,h=50);
        color([0.10,0.10,0.12]) translate([0,temp_y,10]) cylinder(d=3,h=32);
    }
}
assert(rod_pitch >= rod_d + hole_allowance + 4);
assert(width/2 > rod_pitch/2 + (rod_d+hole_allowance)/2 + 4);
if(part=="coupon") coupon();
else if(part=="assembly") assembly();
else head();

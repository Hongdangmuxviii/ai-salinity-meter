// Removable dry rim bridge for test_probe_head_v1 (44 x 34 x 18 mm).
// Units: mm. Prototype only; not food-contact, waterproof or physically validated.
// A rim support fixes the HEAD, not the liquid surface. Set liquid freeboard first.
// Existing head mounting holes: x = +/-17, y = 8, vertical M3 clearance.
$fn = 64;
part = "bridge"; // [bridge,stop,spacer5,coupon,assembly]
bridge_length = 200;
bridge_width = 42;
bridge_thickness = 6;
head_width = 44;
head_depth = 34;
head_height = 18;
mount_x = 17;
mount_y = 8;
mount_clearance = 3.6;
nut_af_clearance = 5.9;
nut_depth = 2.8;
slot_start = 28;
slot_end = 84;
slot_width = 3.8;
stop_width = 14;
stop_depth = 22;
stop_height = 6;
spacer_height = 0; // Assembly preview: 0 or 5. Print optional spacer5 separately.
rod_projection = 55; // USER CONFIRMED: length below the HEAD, not total rod length.
immersion = 25; // Illustrative first test only; not an optimized EC measurement depth.
temperature_projection = 40; // Existing head guide example; must verify actual installation.
preview_inner_diameter = 110; // Example vessel only, not a selected product.
preview_outer_diameter = 118;
preview_vessel_depth = 80;
preview_stop_x = 45;
show_liquid = true;

head_bottom = bridge_thickness + spacer_height;
freeboard = rod_projection - immersion - head_bottom;

module rounded_plate(w,d,h,r=2) {
    linear_extrude(height=h)
        offset(r=r) square([w-2*r,d-2*r],center=true);
}
module bore(x,y,d,z,h) {
    translate([x,y,z]) cylinder(d=d,h=h);
}
module hex_pocket(x,y,z,h) {
    translate([x,y,z]) rotate([0,0,30])
        cylinder(d=nut_af_clearance/cos(30),h=h,$fn=6);
}
module sensor_clearances(h) {
    // Larger than the original head bores: clearance only, NOT extra rod clamps.
    for(x=[-10,10]) bore(x,-6,9,-0.1,h+0.2);
    bore(0,8,10,-0.1,h+0.2);
}
module mount_bores(h) {
    for(x=[-mount_x,mount_x]) bore(x,mount_y,mount_clearance,-0.1,h+0.2);
}
module long_slot(side) {
    hull() {
        bore(side*slot_start,0,slot_width,-0.1,bridge_thickness+0.2);
        bore(side*slot_end,0,slot_width,-0.1,bridge_thickness+0.2);
    }
}
module bridge() {
    difference() {
        rounded_plate(bridge_length,bridge_width,bridge_thickness,3);
        sensor_clearances(bridge_thickness);
        mount_bores(bridge_thickness);
        for(side=[-1,1]) {
            long_slot(side);
            // Nuts insert from BELOW the bridge; pocket is accessible from below.
            hex_pocket(side*mount_x,mount_y,-0.1,nut_depth+0.1);
        }
        for(x=[-70,70])
            translate([x,10,bridge_thickness-0.5])
                linear_extrude(height=0.6) text("DRY",size=4,halign="center");
    }
}
module stop() {
    // PRINT with nut pocket facing UP; turn over for assembly below bridge.
    difference() {
        rounded_plate(stop_width,stop_depth,stop_height,2);
        bore(0,0,mount_clearance,-0.1,stop_height+0.2);
        hex_pocket(0,0,stop_height-nut_depth,nut_depth+0.1);
    }
}
module spacer(h) {
    difference() {
        rounded_plate(head_width,head_depth,h,2);
        sensor_clearances(h);
        mount_bores(h);
    }
}
module reference_head() {
    // Exact v1 head geometry, reproduced for assembly preview only.
    difference() {
        rounded_plate(head_width,head_depth,head_height,2);
        for(x=[-10,10]) {
            bore(x,-6,5.5,-0.1,head_height+0.2);
            translate([x,-12,7]) rotate([90,0,0]) cylinder(d=3.4,h=12,center=true);
            translate([x-5.9/2,-13.5-2.8/2,3.7]) cube([5.9,2.8,14.4]);
        }
        bore(0,8,6.5,-0.1,head_height+0.2);
        translate([0,13,7]) rotate([90,0,0]) cylinder(d=3.4,h=10,center=true);
        translate([-5.9/2,13.5-2.8/2,3.7]) cube([5.9,2.8,14.4]);
        for(x=[-17,17]) bore(x,8,3.4,-0.1,head_height+0.2);
    }
}
module assembled_frame() {
    color([0.2,0.48,0.77]) bridge();
    if(spacer_height>0) color([0.8,0.67,0.22])
        translate([0,0,bridge_thickness]) spacer(spacer_height);
    for(side=[-1,1]) color([0.85,0.46,0.17])
        translate([side*preview_stop_x,0,0]) rotate([180,0,0]) stop();
}
module assembly() {
    assembled_frame();
    color([0.12,0.58,0.53]) translate([0,0,head_bottom]) reference_head();
    for(x=[-10,10]) color([0.65,0.68,0.72])
        bore(x,-6,5,head_bottom-rod_projection,rod_projection+head_height+12);
    color([0.43,0.46,0.48])
        bore(0,8,6,head_bottom-temperature_projection,50);
    color([0.15,0.15,0.16])
        bore(0,8,3,head_bottom-temperature_projection+50,26);
    // Example cup shown as thin translucent shell; top rim z=0.
    color([0.75,0.8,0.84,0.20]) difference() {
        bore(0,0,preview_outer_diameter,-preview_vessel_depth,preview_vessel_depth);
        bore(0,0,preview_inner_diameter,-preview_vessel_depth+3,preview_vessel_depth+0.1);
    }
    if(show_liquid) color([0.25,0.63,0.92,0.18])
        bore(0,0,preview_inner_diameter-0.2,-preview_vessel_depth+3,
             preview_vessel_depth-3-freeboard);
}

assert(bridge_length <= 240, "Keep bridge within the intended X1C build plate envelope.");
assert(mount_x==17 && mount_y==8, "Mount holes must match existing v1 head.");
assert(rod_projection > immersion);
assert(spacer_height==0 || spacer_height==5, "Preview uses only supplied spacer heights.");
assert(freeboard>=15, "Keep water >=15 below rim in this dry prototype; check splash separately.");
assert(preview_stop_x>=slot_start && preview_stop_x<=slot_end);
assert(sqrt(pow(preview_stop_x+stop_width/2,2)+pow(stop_depth/2,2))
       < preview_inner_diameter/2, "Preview rim stops must fit inside the cup.");

if(part=="stop") stop();
else if(part=="spacer5") spacer(5);
else if(part=="coupon") spacer(3);
else if(part=="assembly") assembly();
else bridge();

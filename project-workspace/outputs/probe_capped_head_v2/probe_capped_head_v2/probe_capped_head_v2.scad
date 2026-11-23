// Capped three-probe MVP development head, mm. Prototype, NOT verified watertight/food-safe.
// Existing clamp METHOD and probe XY positions retained. Old head/bridge not reused.
// EM Tech Devicemart 15584272: metal probe 6 x 50 mm (verify received hardware).
// Seals: nominal JIS P5 (4.8 x 1.9) x2, P6 (5.8 x 1.9) x1.
// Size designation is NOT food-contact certification. Select actual compound separately.
$fn = 64;
part = "holder"; // [holder,cap,retainer,alignment_jig,fit_coupon,gasket_template,assembly,exploded,section,interference]
rod_d = 5;
temp_d = 6;
temp_metal_length = 50;
tip_projection = 10; // Below OUTSIDE bottom face; not an exact effective EC electrode length.
head_clearance = 0.5;
cap_clearance = 0.6;
head_h = 18;
head_w = 44;
head_d = 34;
clamp_z = 7;
nut_af = 5.9;
nut_depth = 2.8;
clear_m3 = 3.6;
cap_w = 34;
cap_d = 32;
cap_h = 25;
base_h = 4;
entry_land = 1.2; // Fluid can contact a short length inside this through-hole too.
seal_h = 1.5; // Nominal squeeze of 1.9 mm cross-section; needs seal coupon validation.
seal_cs = 1.9;
gasket_stock_h = 1;
gasket_compressed_h = 0.75;
ear_x = 22.5;
ear_y = 12;
ear_size = 9;
frame_w = 58;
frame_d = 38;
temp_clamp_overlap_min = 10;
preview_rod_length = 85; // Preview only; actual total rod length has not been measured.
preview_liquid_z = 5; // 15 mm above tips, 5 mm above cap outside face. Not validated minimum.
show_hardware = true;
show_liquid = true;

sensor_xy = [[-10,-6],[10,-6],[0,8]];
sensor_d = [rod_d,rod_d,temp_d];
seal_id = [4.8,4.8,5.8];
seal_od = [9.8,9.8,10.8];
boss_od = [9.3,9.3,10.3];
cap_top = base_h + cap_h;
head_bottom = cap_top + gasket_compressed_h;
head_top = head_bottom + head_h;
boss_bottom = entry_land + seal_h;
boss_extension = base_h - boss_bottom;
temp_tip = -tip_projection;
temp_metal_top = temp_tip + temp_metal_length;
fastener_xy = [for(x=[-ear_x,ear_x]) for(y=[-ear_y,ear_y]) [x,y]];

module rounded_block(w,d,h,r=2) {
    linear_extrude(height=h) offset(r=r) square([w-2*r,d-2*r],center=true);
}
module hole(x,y,d,z,h) { translate([x,y,z]) cylinder(d=d,h=h); }
module hexhole(x,y,z,h) {
    translate([x,y,z]) rotate([0,0,30]) cylinder(d=nut_af/cos(30),h=h,$fn=6);
}
module probe_bores(h,clearance) {
    for(i=[0:2]) hole(sensor_xy[i][0],sensor_xy[i][1],sensor_d[i]+clearance,-0.1,h+0.2);
}
module clamp_port(x,side) {
    // Same nut-and-side-screw principle and central head dimensions as v1.
    if(side<0) {
        translate([x,-12,clamp_z]) rotate([90,0,0]) cylinder(d=3.4,h=12,center=true);
        translate([x-nut_af/2,-13.5-nut_depth/2,clamp_z-3.3])
            cube([nut_af,nut_depth,head_h-clamp_z+3.4]);
    } else {
        translate([x,13,clamp_z]) rotate([90,0,0]) cylinder(d=3.4,h=10,center=true);
        translate([x-nut_af/2,13.5-nut_depth/2,clamp_z-3.3])
            cube([nut_af,nut_depth,head_h-clamp_z+3.4]);
    }
}
module holder() {
    difference() {
        union() {
            rounded_block(head_w,head_d,head_h,2);
            for(p=fastener_xy) translate([p[0],p[1],0])
                rounded_block(ear_size,ear_size,head_h,1);
        }
        probe_bores(head_h,head_clearance);
        for(x=[-10,10]) clamp_port(x,-1);
        clamp_port(0,+1);
        for(p=fastener_xy) hole(p[0],p[1],clear_m3,-0.1,head_h+0.2);
    }
}
module cap_core() {
    // Local main body z=0..25. Three bosses protrude DOWN by 1.3 mm.
    difference() {
        union() {
            rounded_block(cap_w,cap_d,cap_h,2);
            for(i=[0:2]) hole(sensor_xy[i][0],sensor_xy[i][1],boss_od[i],
                             -boss_extension,boss_extension+0.1);
        }
        for(i=[0:2]) hole(sensor_xy[i][0],sensor_xy[i][1],sensor_d[i]+cap_clearance,
                         -boss_extension-0.1,cap_h+boss_extension+0.2);
    }
}
module cap_print() {
    // Broad flat TOP of cap on bed, bosses UP. No trapped support in seal region.
    translate([0,0,cap_h]) rotate([180,0,0]) cap_core();
}
module retainer() {
    difference() {
        union() {
            rounded_block(frame_w,frame_d,base_h,2);
            for(p=fastener_xy) translate([p[0],p[1],base_h-0.1])
                rounded_block(ear_size,ear_size,head_bottom-base_h+0.1,1);
        }
        probe_bores(base_h,cap_clearance);
        // O-rings load from TOP. Seat floor is z=1.2; boss presses at z=2.7.
        for(i=[0:2]) hole(sensor_xy[i][0],sensor_xy[i][1],seal_od[i],
                         entry_land,base_h-entry_land+0.1);
        // Nuts remain in the upper DRY pillars, not on the wetted bottom face.
        for(p=fastener_xy) {
            hole(p[0],p[1],clear_m3,20,head_bottom-20+0.1);
            hexhole(p[0],p[1],head_bottom-nut_depth,nut_depth+0.1);
        }
    }
}
module gasket_2d() {
    difference() {
        offset(r=2) square([cap_w-4,cap_d-4],center=true);
        for(i=[0:2]) translate(sensor_xy[i]) circle(d=sensor_d[i]+1);
    }
}
module gasket(h=gasket_compressed_h) { linear_extrude(height=h) gasket_2d(); }
module alignment_jig() {
    // Rod tips rest on base top z=2; retainer bottom rests on posts z=12.
    union() {
        rounded_block(frame_w,frame_d,2,2);
        for(x=[-24,24]) for(y=[-14,14])
            translate([x,y,2-0.1]) rounded_block(6,6,tip_projection+0.1,1);
    }
}
module fit_coupon() {
    difference() {
        rounded_block(40,25,5,1);
        for(i=[0:2]) {
            hole(-12+12*i,-5,rod_d+0.3+0.2*i,-0.1,5.2);
            hole(-12+12*i,5,temp_d+0.3+0.2*i,-0.1,5.2);
        }
    }
}
module compressed_seal(i) {
    // Illustrative incompressible elliptical torus; not an FEA/contact solution.
    w=(-sensor_d[i]+sqrt(pow(sensor_d[i],2)+4*(seal_id[i]+seal_cs)*pow(seal_cs,2)/seal_h))/2;
    translate([sensor_xy[i][0],sensor_xy[i][1],entry_land+seal_h/2])
        rotate_extrude() translate([sensor_d[i]/2+w/2,0]) scale([w/2,seal_h/2]) circle(r=1,$fn=40);
}
module print_components(explode=0) {
    color([0.20,0.43,0.74]) retainer();
    color([0.18,0.64,0.59]) translate([0,0,base_h+explode]) cap_core();
    color([0.85,0.70,0.27]) translate([0,0,cap_top+explode*1.6]) gasket();
    color([0.22,0.48,0.72]) translate([0,0,head_bottom+explode*2.3]) holder();
    for(i=[0:2]) color([0.90,0.47,0.16]) compressed_seal(i);
}
module probes() {
    for(i=[0:1]) color([0.68,0.71,0.74]) hole(sensor_xy[i][0],sensor_xy[i][1],rod_d,
                                             -tip_projection,preview_rod_length);
    color([0.50,0.54,0.56]) hole(0,8,temp_d,temp_tip,temp_metal_length);
    color([0.12,0.13,0.14]) hole(0,8,3,temp_metal_top,30);
}
module assembly(explode=0) {
    print_components(explode);
    if(explode==0) {
        probes();
        if(show_hardware) for(p=fastener_xy) color([0.65,0.65,0.67]) {
            hole(p[0],p[1],3,head_top-25,25);
            hole(p[0],p[1],5.5,head_top,2.5);
        }
        if(show_liquid) color([0.25,0.63,0.90,0.14])
            translate([-38,-27,-tip_projection-2]) cube([76,54,tip_projection+2+preview_liquid_z]);
    }
}
module section() {
    // Front half-section reveals electrodes/O-ring seats; temperature is behind this plane.
    intersection() { print_components(); translate([-60,-6,-1]) cube([120,70,70]); }
    probes();
}
module interference() {
    // Rigid printed-part intersections only. Ignore intended zero-thickness mating faces
    // by lifting inserted parts 0.01 mm. Compressed seals intentionally excluded.
    eps = 0.01;
    union() {
        intersection() { retainer(); translate([0,0,base_h+eps]) cap_core(); }
        intersection() { retainer(); translate([0,0,head_bottom+eps]) holder(); }
        intersection() { translate([0,0,base_h+eps]) cap_core(); translate([0,0,head_bottom+eps]) holder(); }
    }
}

assert(head_clearance>0 && cap_clearance>0);
assert(temp_metal_top-head_bottom>=temp_clamp_overlap_min,
       "Temperature metal tube must overlap holder >=10 mm; adjust cap height before changing tip length.");
assert(temp_metal_top-(head_bottom+clamp_z)>=3,
       "Clamp must press metal, not cable/heat-shrink junction.");
assert(boss_extension>0 && entry_land>=1);
assert(seal_h>0 && seal_h<seal_cs);
assert(gasket_compressed_h>0 && gasket_compressed_h<gasket_stock_h);
assert(ear_x-ear_size/2>cap_w/2, "Retainer pillars must clear central cap.");
assert((preview_liquid_z+tip_projection)>=tip_projection+3);
assert(preview_liquid_z<20, "Prototype immersion zone stays below dry nuts/holder.");

if(part=="holder") holder();
else if(part=="cap") cap_print();
else if(part=="retainer") retainer();
else if(part=="alignment_jig") alignment_jig();
else if(part=="fit_coupon") fit_coupon();
else if(part=="gasket_template") gasket_2d();
else if(part=="assembly") assembly();
else if(part=="exploded") assembly(12);
else if(part=="section") section();
else if(part=="interference") interference();

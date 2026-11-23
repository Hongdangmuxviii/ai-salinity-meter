// Battery-powered MVP concept. NOT a print-ready enclosure.
// Existing head imported without changing probe positions or 10 mm projection.
use <reference_head.scad>
$fn=56;
view="assembled"; // assembled, cutaway
base_z=47.75;
body_h=108;
module rounded(w,d,h,r=4){linear_extrude(height=h) offset(r=r) square([w-2*r,d-2*r],center=true);}
module housing(){
  difference(){
    translate([0,0,base_z]) rounded(64,44,body_h,5);
    translate([0,0,base_z+2.4]) rounded(59.2,39.2,body_h-4.8,3);
    // Front openings, preview dimensions only.
    translate([-21,-25,115]) cube([42,8,13]);
    for(x=[-18,0,18]) translate([x,-25,96]) rotate([-90,0,0]) cylinder(d=13,h=8);
    translate([-25,-25,133]) cube([49,8,17]);
    // USB-C on top; switch on right.
    translate([-23,-17,151]) cube([12,7,9]);
    translate([29,-4,132]) cube([8,8,14]);
    // Proposed dry-side head saddle. Head itself is unchanged.
    translate([0,0,44]) rounded(55,35,9,2);
  }
}
module existing_head(){
 color([.20,.38,.53]) retainer();
 color([.18,.54,.56]) translate([0,0,4]) cap_core();
 color([.82,.68,.25]) translate([0,0,29]) gasket();
 color([.20,.38,.53]) translate([0,0,29.75]) holder();
 for(i=[0:2]) color([.90,.47,.16]) compressed_seal(i);
 probes();
 for(x=[-22.5,22.5]) for(y=[-12,12]) color([.65,.68,.7]) translate([x,y,47.75]) cylinder(d=5.5,h=2.5);
}
module face_text(t,x,z,s=2.8){translate([x,-22.25,z]) rotate([90,0,0]) linear_extrude(height=.15) text(t,size=s,halign="center",font="Arial:style=Bold");}
module controls(){
 color([.025,.055,.08]) translate([-24.5,-22.2,132.5]) cube([49,1,18]);
 // Camera aperture and separate ToF optical aperture.
 color([.08,.1,.12]) translate([-16,-23,141]) rotate([-90,0,0]) cylinder(d=10,h=2);
 color([.12,.35,.45]) translate([-16,-23.1,141]) rotate([-90,0,0]) cylinder(d=5,h=.2);
 color([.10,.12,.15]) translate([6,-22.7,137]) cube([16,1.2,8]);
 color([.025,.04,.055]) translate([-21,-22.25,114.5]) cube([42,.9,14]);
 color([.65,.94,.95]) {face_text("RAW 55.4",0,122,3);face_text("T 22.9 C",0,117.5,2.5);}
 for(x=[-18,0,18]) color(x==0?[.14,.59,.58]:[.20,.27,.33]) translate([x,-23,96]) rotate([-90,0,0]) cylinder(d=12,h=2);
 color([.25,.34,.4]) {face_text("MEASURE",-18,84.5,1.9);face_text("MODE",0,84.5,1.9);face_text("SAVE",18,84.5,1.9);face_text("SALT / MVP",0,68,3.4);}
 color([.12,.15,.17]) translate([32,-3,134]) cube([1.5,6,7]);
 color([.08,.1,.12]) translate([-22,-16.5,155.6]) cube([10,6,.3]);
}
module internals(){
 // All rectangular component shapes are allocated envelopes, not exact STEP models.
 color([.08,.36,.24]) translate([-27,-15,131]) cube([22,3,21]); // XIAO + camera envelope
 color([.07,.30,.24]) translate([3,-15,127]) cube([25.4,3,25.4]); // ToF
 color([.07,.30,.24]) translate([-19,-17,114]) cube([38,3,15]); // OLED PCB allowance
 color([.10,.28,.20]) translate([-16,-15,54]) cube([32,3,32]); // ADS1115
 color([.10,.40,.27]) translate([-25,0,54]) cube([50,2,35]); // carrier allowance
 color([.78,.80,.82]) translate([-15,9,94]) cube([30,8,40]); // nominal DTP803040 cell
 color([.94,.66,.16]) translate([-12,8.8,103]) cube([24,.3,22]);
 color([.14,.14,.15]) translate([16,7,73]) rotate([90,0,0]) cylinder(d=14,h=8); // buzzer
 color([.13,.38,.24]) translate([27,-7,129]) cube([2.5,15.2,15.2]); // Pololu
 // Indicative red and black battery leads, kept within dry zone.
 color([.75,.07,.06]) translate([-13,10,134]) cylinder(d=1.4,h=12);
 color([.05,.06,.07]) translate([-10,10,134]) cylinder(d=1.4,h=12);
}
existing_head();
if(view=="cutaway"){
  color([.85,.88,.89]) difference(){housing();translate([-40,1,48]) cube([80,30,120]);}
  controls(); internals();
} else {color([.88,.91,.92]) housing();controls();}

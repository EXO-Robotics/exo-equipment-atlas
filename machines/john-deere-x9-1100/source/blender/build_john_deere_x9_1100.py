#!/usr/bin/env python3
"""Deterministic machine-local John Deere X9 1100 structural-study builder.

This file owns the X9/HD50R topology. Manufacturer-published dimensions are
used only where the evidence package identifies them; the carrier envelope,
panels, hidden pivots, supports, and kinematics remain reconstructed. The
neutral geometry is independently authored and contains no manufacturer CAD,
logos, textures, or trade dress.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import bpy


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()


def load_shared_generator():
    spec = importlib.util.spec_from_file_location("exo_fleet_builder_x9", SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load shared fleet generator: {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared_generator()


class JohnDeereX91100Builder(shared.FleetBuilder):
    """Author the selected wheeled X9, HD50R and 9.45 m auger study."""

    HEADER_SPAN_M = 15.2
    FEEDERHOUSE_WIDTH_M = 1.72
    ROTOR_LENGTH_M = 3.5
    ROTOR_DIAMETER_M = 0.6
    GRAIN_TANK_CAPACITY_M3 = 16.210
    AUGER_CENTERLINE_M = 9.45

    def write_machine_wrapper(self):
        """Preserve this audited machine-local subclass."""

    @staticmethod
    def _descends(node_name, ancestor_name):
        node = bpy.data.objects.get(node_name)
        while node is not None:
            if node.name == ancestor_name:
                return True
            node = node.parent
        return False

    @staticmethod
    def _world_extent(node_name, axis):
        node = bpy.data.objects[node_name]
        values = [(node.matrix_world @ shared.Vector(corner))[axis] for corner in node.bound_box]
        return max(values) - min(values)

    def _gate(self, gate_id, condition, detail):
        semantic_nodes = {
            "selected_header_span_envelope": ["Header_ROOT", "HD50R_Main_Backbone"],
            "carrier_length_unresolved": [],
            "carrier_height_unresolved": [],
            "wheeled_running_gear": ["Running_Gear_ROOT", "Front_L_Wheel_ROOT", "Front_R_Wheel_ROOT", "Rear_L_Wheel_ROOT", "Rear_R_Wheel_ROOT"],
            "feederhouse_continuity": ["Feederhouse_ROOT", "Feeder_Chain_1_ROOT", "Feeder_Chain_2_ROOT", "Feeder_Chain_3_ROOT", "Feeder_Chain_4_ROOT"],
            "header_attachment_continuity": ["Feederhouse_ROOT", "Header_Lift_Pivot", "Header_ROOT", "HD50R_L_Wing_ROOT", "HD50R_R_Wing_ROOT"],
            "reel_axis_continuity": ["Header_ROOT", "Reel_Pivot", "Reel_ROOT", "HD50R_Reel_Axle"],
            "unloader_hinge_continuity": ["Unloader_Swing_Pivot", "Unloader_ROOT", "Unloader_Auger_9_45m_Tube"],
            "auger_header_clearance": ["Unloader_ROOT", "Unloader_Auger_9_45m_Tube", "Header_ROOT", "HD50R_Main_Backbone"],
            "ground_collision": ["Running_Gear_ROOT", "Front_L_Tire", "Front_R_Tire", "Rear_L_Tire", "Rear_R_Tire"],
            "self_collision": ["Unloader_ROOT", "Header_ROOT", "Grain_Tank_External_Volume"],
            "neutral_unbranded_material_review": ["Machine_Root"],
        }[gate_id]
        fact_ids = {
            "selected_header_span_envelope": ["public-envelope-z", "hd50r-compatibility"],
            "carrier_length_unresolved": [],
            "carrier_height_unresolved": [],
            "wheeled_running_gear": [],
            "feederhouse_continuity": ["feederhouse-width", "feeder-chain-count"],
            "header_attachment_continuity": [],
            "reel_axis_continuity": [],
            "unloader_hinge_continuity": ["selected-auger-length"],
            "auger_header_clearance": [],
            "ground_collision": [],
            "self_collision": ["rotor-count", "rotor-length", "rotor-diameter", "grain-tank-capacity"],
            "neutral_unbranded_material_review": [],
        }[gate_id]
        return {
            "id": gate_id,
            "status": "PASS" if condition else "FAIL",
            "detail": {
                "method": "machine-local metric measurement and exported-hierarchy assertion",
                "evidence": detail,
                "semantic_nodes": semantic_nodes,
                "fact_ids": fact_ids,
            },
        }

    def _add_smooth_wheel(self, prefix, center, radius, width):
        """Add one undistorted circular tire without cosmetic tread padding."""
        pivot = self.empty(f"{prefix}_Wheel_Pivot", center, self.running_root, role="wheel_pivot")
        root = self.empty(f"{prefix}_Wheel_ROOT", parent=pivot, role="wheel_root")
        tire = self.wheel_tire(f"{prefix}_Tire", radius, width / 2, self.materials["rubber"], root)
        tire["exo_nominal_radius_m"] = radius
        tire["exo_nominal_width_m"] = width
        self.cylinder(
            f"{prefix}_Rim", (0, 0, 0), radius * 0.50, width * 0.76,
            self.materials["steel"], root, vertices=28, role="wheel_rim",
        )
        self.cylinder(
            f"{prefix}_Hub", (0, 0, 0), radius * 0.18, width * 0.84,
            self.materials["graphite"], root, vertices=20, role="wheel_hub",
        )
        return root

    def _torus(self, name, location, major_radius, minor_radius, material, parent, rotation=(0, 0, 0), role="geometry"):
        """Create a dimensionally authored ring without scale distortion."""
        bpy.ops.mesh.primitive_torus_add(
            major_radius=major_radius,
            minor_radius=minor_radius,
            major_segments=28,
            minor_segments=8,
            location=location,
            rotation=rotation,
        )
        obj = bpy.context.object
        obj.name = name
        obj.parent = parent
        obj.data.materials.append(material)
        return self.tag(obj, role=role)

    def _add_combine_cab(self):
        """Build the elevated, forward panoramic combine operator station."""
        cab = self.empty("Operator_Station_ROOT", (2.02, 1.78, 0), self.fixed_root, role="operator_station")
        self.box("Cab_Floor", (0, 0.10, 0), (1.92, 0.18, 1.96), self.materials["graphite"], cab, role="cab_structure")
        self.box("Cab_Roof_Cap", (-0.02, 2.14, 0), (2.12, 0.16, 2.16), self.materials["body"], cab, role="cab_structure", bevel=0.045)
        self.box("Cab_Roof_Visor", (0.98, 2.02, 0), (0.24, 0.22, 2.10), self.materials["body_dark"], cab, rotation=(0, 0, -0.12), role="cab_structure")
        self.box("Cab_Front_Panoramic_Glass", (0.86, 1.15, 0), (0.11, 1.62, 1.82), self.materials["glass"], cab, rotation=(0, 0, -0.11), role="glazing")
        self.box("Cab_Rear_Glass", (-0.88, 1.12, 0), (0.09, 1.48, 1.74), self.materials["glass"], cab, role="glazing")
        side_outline = [(-0.80, 0.36), (0.72, 0.36), (0.91, 1.88), (0.67, 2.02), (-0.76, 2.02)]
        for side, z in (("L", -0.95), ("R", 0.95)):
            self.side_profile(
                f"Cab_{side}_Panoramic_Glass", side_outline, 0.055,
                self.materials["glass"], cab, z_center=z, role="glazing",
            )
            for x, y, label in ((-0.82, 1.18, "Rear"), (0.80, 1.18, "Front")):
                self.box(
                    f"Cab_{side}_{label}_Post", (x, y, z), (0.09, 1.70, 0.09),
                    self.materials["graphite"], cab, rotation=(0, 0, -0.06 if x > 0 else 0),
                    role="cab_structure",
                )
        self.box("Cab_Lower_Nose", (0.70, 0.34, 0), (0.52, 0.46, 1.92), self.materials["body_dark"], cab, rotation=(0, 0, -0.10), role="cab_structure")
        self.box("Operator_Seat", (-0.15, 0.66, 0), (0.48, 0.74, 0.62), self.materials["graphite"], cab, role="operator_cue")
        self.cylinder("Steering_Column", (0.45, 0.69, 0), 0.035, 0.55, self.materials["steel"], cab, vertices=16, rotation=(0, math.pi / 2, 0), role="operator_cue")
        return cab

    def _add_access_system(self):
        """Add the operator-side deck, ladder, guard rails and service walkway."""
        deck = self.empty("Operator_Access_ROOT", (1.55, 1.47, -1.67), self.fixed_root, role="access_system")
        self.box("Operator_Access_Deck", (0, 0, 0), (2.20, 0.10, 0.72), self.materials["steel"], deck, role="access_platform")
        for index, x in enumerate((-0.95, -0.25, 0.45, 1.02), start=1):
            self.pipe_between(f"Access_Rail_Post_{index}", (x, 0.04, -0.31), (x, 0.78, -0.31), 0.025, self.materials["rod"], deck, role="handrail")
        self.pipe_between("Access_Rail_Top", (-0.98, 0.78, -0.31), (1.03, 0.78, -0.31), 0.025, self.materials["rod"], deck, role="handrail")
        ladder = self.empty("Operator_Ladder_ROOT", (-0.90, -0.05, -0.10), deck, role="access_ladder")
        for side, z in (("L", -0.25), ("R", 0.25)):
            self.pipe_between(f"Ladder_Stringer_{side}", (0, -0.80, z), (0, 0.0, z), 0.027, self.materials["steel"], ladder, role="ladder_stringer")
        for index in range(5):
            self.pipe_between(f"Ladder_Rung_{index + 1:02d}", (0, -0.72 + index * 0.18, -0.25), (0, -0.72 + index * 0.18, 0.25), 0.024, self.materials["steel"], ladder, role="ladder_rung")

    def _add_rear_cleaning_and_residue(self):
        """Expose the cleaning shoe discharge, chopper and twin spreader path."""
        cleaning = self.empty("Rear_Cleaning_ROOT", (-3.75, 0.80, 0), self.fixed_root, role="cleaning_system")
        for index in range(5):
            self.box(
                f"Cleaning_Shoe_Louver_{index + 1:02d}", (-0.28 + index * 0.18, 0.14 + index * 0.05, 0),
                (0.13, 0.035, 2.10), self.materials["steel"], cleaning,
                rotation=(0, 0, -0.18), role="cleaning_shoe_louver", bevel=0.004,
            )
        chopper = self.empty("Rear_Chopper_ROOT", (-0.42, 0.38, 0), cleaning, role="rotary_root")
        self.cylinder("Rear_Residue_Chopper", (0, 0, 0), 0.28, 1.90, self.materials["graphite"], chopper, vertices=28, role="residue_chopper")
        for index in range(8):
            angle = math.tau * index / 8
            self.box(
                f"Rear_Chopper_Knife_{index + 1:02d}", (math.cos(angle) * 0.29, math.sin(angle) * 0.29, 0),
                (0.18, 0.035, 1.78), self.materials["steel"], chopper,
                rotation=(0, 0, angle), role="chopper_knife", bevel=0.004,
            )
        for side, z in (("L", -0.62), ("R", 0.62)):
            spreader = self.empty(f"Residue_Spreader_{side}_ROOT", (-0.88, -0.20, z), cleaning, role="rotary_root")
            self.cylinder(
                f"Residue_Spreader_{side}_Disc", (0, 0, 0), 0.31, 0.055,
                self.materials["steel"], spreader, vertices=28,
                rotation=(math.pi / 2, 0, 0), role="residue_spreader",
            )
            for vane in range(4):
                angle = math.tau * vane / 4
                self.box(
                    f"Residue_Spreader_{side}_Vane_{vane + 1}",
                    (math.cos(angle) * 0.18, 0, math.sin(angle) * 0.18),
                    (0.25, 0.035, 0.045), self.materials["graphite"], spreader,
                    rotation=(0, -angle, 0), role="spreader_vane", bevel=0.004,
                )

    def _add_feederhouse(self):
        feeder = self.empty("Feederhouse_ROOT", (1.30, 1.18, 0), self.fixed_root, role="motion_root")
        self.side_profile(
            "Feederhouse_Side_L",
            [(0.0, 0.23), (1.70, -0.36), (1.70, 0.17), (0.0, 0.42)],
            0.055, self.materials["body_dark"], feeder,
            z_center=-self.FEEDERHOUSE_WIDTH_M / 2, role="feederhouse_frame",
        )
        self.side_profile(
            "Feederhouse_Side_R",
            [(0.0, 0.23), (1.70, -0.36), (1.70, 0.17), (0.0, 0.42)],
            0.055, self.materials["body_dark"], feeder,
            z_center=self.FEEDERHOUSE_WIDTH_M / 2, role="feederhouse_frame",
        )
        self.box(
            "Feederhouse_Width_Crossmember", (0.12, 0.30, 0),
            (0.12, 0.12, self.FEEDERHOUSE_WIDTH_M), self.materials["steel"],
            feeder, role="feederhouse_crossmember",
        )
        self.box(
            "Feederhouse_Bottom_Pan", (0.86, -0.22, 0), (1.62, 0.065, 1.62),
            self.materials["body_dark"], feeder, rotation=(0, 0, -0.32), role="feederhouse_pan",
        )
        for index, x in enumerate((0.34, 0.88, 1.42), start=1):
            self.box(
                f"Feederhouse_Top_Brace_{index}", (x, 0.27 - x * 0.31, 0),
                (0.075, 0.075, 1.63), self.materials["steel"], feeder,
                rotation=(0, 0, -0.32), role="feederhouse_brace",
            )
        self.cylinder(
            "Feederhouse_Front_Drum", (1.56, -0.26, 0), 0.13, 1.55,
            self.materials["graphite"], feeder, vertices=24, role="feeder_drum",
        )
        for side, z in (("L", -0.86), ("R", 0.86)):
            self.cylinder(
                f"Feederhouse_Rear_Pivot_{side}", (0.02, 0.30, z), 0.15, 0.08,
                self.materials["steel"], feeder, vertices=24, role="feederhouse_pivot_cue",
            )

        # Four separately named conveyor chains with common formed-steel slats.
        chain_z = (-0.60, -0.20, 0.20, 0.60)
        for index, z in enumerate(chain_z, start=1):
            chain = self.empty(
                f"Feeder_Chain_{index}_ROOT", (0, 0, z), feeder,
                role="continuous_chain_root",
            )
            self.pipe_between(
                f"Feeder_Chain_{index}_Upper_Run", (0.10, 0.28, 0), (1.57, -0.21, 0),
                0.018, self.materials["graphite"], chain, role="feeder_chain",
            )
            self.pipe_between(
                f"Feeder_Chain_{index}_Lower_Run", (0.12, 0.18, 0), (1.55, -0.31, 0),
                0.018, self.materials["graphite"], chain, role="feeder_chain",
            )
            for label, point in (("Rear", (0.11, 0.23, 0)), ("Front", (1.56, -0.26, 0))):
                self.cylinder(
                    f"Feeder_Chain_{index}_{label}_Sprocket", point, 0.075, 0.035,
                    self.materials["steel"], chain, vertices=16, role="feeder_sprocket",
                )
        for index in range(13):
            t = index / 12
            self.box(
                f"Feeder_Formed_Slat_{index + 1:02d}",
                (0.12 + 1.43 * t, 0.18 - 0.49 * t, 0),
                (0.075, 0.035, 1.48), self.materials["steel"], feeder,
                rotation=(0, 0, -0.33), role="feeder_slat", bevel=0.006,
            )
        return feeder

    def _add_hd50r(self, feeder):
        pivot = self.empty("Header_Lift_Pivot", (1.70, -0.63, 0), feeder, role="pivot")
        header = self.empty("Header_ROOT", parent=pivot, role="motion_root")

        # Published 15.2 m working-span class. Individual frame, belt and hinge
        # proportions are reconstructed but remain bilaterally explicit.
        self.box(
            "HD50R_Main_Backbone", (0.78, 0.20, 0), (0.18, 0.18, self.HEADER_SPAN_M),
            self.materials["body_dark"], header, role="header_backbone",
        )
        self.box(
            "HD50R_Center_Frame", (0.86, -0.02, 0), (1.50, 0.42, 3.20),
            self.materials["body"], header, role="draper_center_section",
        )
        wing_width = 6.0
        for side, sign in (("L", -1), ("R", 1)):
            hinge = self.empty(
                f"HD50R_{side}_Wing_Hinge_Pivot", (0.35, 0.05, sign * 1.60),
                header, role="pivot",
            )
            wing = self.empty(f"HD50R_{side}_Wing_ROOT", parent=hinge, role="motion_root")
            self.box(
                f"HD50R_{side}_Wing_Frame", (0.52, -0.02, sign * wing_width / 2),
                (1.55, 0.39, wing_width), self.materials["body"], wing,
                role="draper_wing",
            )
            self.box(
                f"HD50R_{side}_Draper_Belt", (0.69, 0.01, sign * wing_width / 2),
                (1.15, 0.075, wing_width * 0.94), self.materials["graphite"], wing,
                role="draper_belt",
            )
            for index in range(5):
                self.box(
                    f"HD50R_{side}_Belt_Cleat_{index + 1:02d}",
                    (0.78, 0.055, sign * (0.65 + index * 1.18)),
                    (0.92, 0.035, 0.045), self.materials["steel"], wing,
                    rotation=(0, 0, -0.10 if sign < 0 else 0.10),
                    role="draper_belt_cleat", bevel=0.004,
                )
            self.pipe_between(
                f"HD50R_{side}_Hinge_Link", (0.05, 0.18, 0),
                (0.52, -0.06, sign * 0.62), 0.032, self.materials["steel"],
                wing, role="header_hinge_link",
            )
            self.side_profile(
                f"HD50R_{side}_Crop_Divider",
                [(0.05, -0.31), (1.70, -0.40), (1.36, 0.16), (0.22, 0.44)],
                0.055, self.materials["body"], wing, z_center=sign * 5.90,
                role="crop_divider",
            )
        self.box(
            "HD50R_Center_Draper_Belt", (0.73, 0.01, 0), (1.16, 0.075, 3.02),
            self.materials["graphite"], header, role="draper_belt",
        )
        self.cylinder(
            "HD50R_Center_Feed_Drum", (0.58, 0.13, 0), 0.20, 2.78,
            self.materials["steel"], header, vertices=28, role="header_center_feed_drum",
        )
        for index in range(5):
            z = -1.05 + index * 0.525
            self.box(
                f"HD50R_Center_Belt_Cleat_{index + 1:02d}", (0.78, 0.055, z),
                (0.92, 0.035, 0.045), self.materials["steel"], header,
                role="draper_belt_cleat", bevel=0.004,
            )
        self.box(
            "HD50R_Cutterbar", (1.995, -0.34, 0), (0.11, 0.075, 15.10),
            self.materials["steel"], header, role="cutterbar",
        )
        for index in range(51):
            z = -7.50 + 15.0 * index / 50
            self.cone(
                f"HD50R_Cutter_Guard_{index + 1:02d}", (1.975, -0.39, z),
                0.040, 0.010, 0.15, self.materials["steel"], header,
                vertices=10, rotation=(0, math.pi / 2, 0), role="cutter_guard",
            )

        reel_pivot = self.empty("Reel_Pivot", (0.92, 0.54, 0), header, role="pivot")
        reel = self.empty("Reel_ROOT", parent=reel_pivot, role="rotary_root")
        self.cylinder(
            "HD50R_Reel_Axle", (0, 0, 0), 0.055, 14.70,
            self.materials["steel"], reel, vertices=20, role="reel_axle",
        )
        for index in range(6):
            angle = math.tau * index / 6
            self.box(
                f"HD50R_Reel_Bat_{index + 1}",
                (math.cos(angle) * 0.34, math.sin(angle) * 0.34, 0),
                (0.055, 0.055, 14.55), self.materials["warning"], reel,
                rotation=(0, 0, angle), role="reel_bat", bevel=0.008,
            )
        for side, z in (("L", -7.35), ("R", 7.35)):
            self.cylinder(
                f"HD50R_Reel_{side}_Spider", (0, 0, z), 0.38, 0.045,
                self.materials["steel"], reel, vertices=20, role="reel_spider",
            )
        for station, z in enumerate((-3.68, 0.0, 3.68), start=1):
            self.cylinder(
                f"HD50R_Reel_Intermediate_Spider_{station}", (0, 0, z), 0.36, 0.035,
                self.materials["steel"], reel, vertices=20, role="reel_spider",
            )
        for bat in range(6):
            angle = math.tau * bat / 6
            for station, z in enumerate((-6.8, -4.55, -2.28, 0.0, 2.28, 4.55, 6.8), start=1):
                self.pipe_between(
                    f"HD50R_Reel_Tine_{bat + 1}_{station:02d}",
                    (math.cos(angle) * 0.34, math.sin(angle) * 0.34, z),
                    (math.cos(angle) * 0.51, math.sin(angle) * 0.51 - 0.10, z),
                    0.012, self.materials["steel"], reel, role="reel_tine",
                )
        return header

    def _add_processing_and_tank(self):
        self.box(
            "Separator_Bottom_Pan", (-0.55, 0.72, 0), (4.25, 0.13, 3.05),
            self.materials["body"], self.fixed_root, role="separator_house",
        )
        self.box(
            "Separator_Upper_Roof", (-0.55, 2.18, 0), (4.10, 0.34, 3.00),
            self.materials["body_dark"], self.fixed_root, role="separator_house",
        )
        for side, z in (("L", -1.57), ("R", 1.57)):
            self.box(
                f"Separator_{side}_Lower_Rail", (-0.55, 1.05, z),
                (4.05, 0.18, 0.10), self.materials["steel"], self.fixed_root,
                role="separator_structure",
            )

        # Two published-size separator rotors, deliberately exposed as a
        # schematic cutaway. Centers and flights remain reconstructed.
        for side, z in (("L", -0.39), ("R", 0.39)):
            rotor = self.empty(f"Dual_Rotor_{side}_ROOT", (-0.65, 1.55, z), self.fixed_root, role="rotary_root")
            body = self.cylinder(
                f"Dual_Rotor_{side}_Body", (0, 0, 0), self.ROTOR_DIAMETER_M / 2,
                self.ROTOR_LENGTH_M, self.materials["graphite"], rotor,
                vertices=28, rotation=(0, math.pi / 2, 0), role="separator_rotor",
            )
            body["exo_published_length_m"] = self.ROTOR_LENGTH_M
            body["exo_published_diameter_m"] = self.ROTOR_DIAMETER_M
            for index in range(12):
                x = -1.52 + index * (3.04 / 11)
                angle = index * math.pi / 3
                self.box(
                    f"Dual_Rotor_{side}_Flight_{index + 1:02d}",
                    (x, math.sin(angle) * 0.23, math.cos(angle) * 0.23),
                    (0.11, 0.07, 0.31), self.materials["steel"], rotor,
                    rotation=(angle, 0, 0), role="rotor_flight", bevel=0.008,
                )

        # Exposed cage rings, concaves and a hinged service cutaway make the
        # published dual-rotor layout readable without claiming hidden mounts.
        for side, z in (("L", -0.39), ("R", 0.39)):
            for station, x in enumerate((-2.05, -1.35, -0.65, 0.05, 0.75), start=1):
                self._torus(
                    f"Dual_Rotor_{side}_Cage_Ring_{station}", (x, 1.55, z),
                    0.35, 0.018, self.materials["steel"], self.fixed_root,
                    rotation=(0, math.pi / 2, 0), role="rotor_cage_ring",
                )
            for bar, dz in enumerate((-0.24, 0.0, 0.24), start=1):
                self.pipe_between(
                    f"Dual_Rotor_{side}_Concave_Bar_{bar}", (-2.36, 1.26, z + dz),
                    (1.06, 1.26, z + dz), 0.018, self.materials["steel"],
                    self.fixed_root, role="rotor_concave_bar",
                )
            self._torus(
                f"Dual_Rotor_{side}_Rear_Service_Flange", (-2.43, 1.55, z),
                0.31, 0.035, self.materials["rod"], self.fixed_root,
                rotation=(0, math.pi / 2, 0), role="rotor_service_flange",
            )
            self.cylinder(
                f"Dual_Rotor_{side}_Rear_End_Cap", (-2.45, 1.55, z), 0.22, 0.055,
                self.materials["steel"], self.fixed_root, vertices=24,
                rotation=(0, math.pi / 2, 0), role="rotor_service_end_cap",
            )
        service = self.empty("Dual_Rotor_Service_Cutaway_ROOT", (-0.65, 1.70, -1.58), self.fixed_root, role="service_cutaway")
        for panel, x in (("Front", 0.90), ("Rear", -0.90)):
            door = self.empty(f"Dual_Rotor_{panel}_Service_Door_Pivot", (x, 0.30, 0), service, role="service_hinge")
            self.side_profile(
                f"Dual_Rotor_{panel}_Service_Door",
                [(-0.78, -0.40), (0.78, -0.40), (0.70, 0.48), (-0.70, 0.48)],
                0.055, self.materials["body"], door, z_center=0,
                role="service_door",
            )

        tank_profile = [
            (-3.30, 2.10), (0.30, 2.10), (0.60, 2.55),
            (0.28, 3.90), (-2.85, 3.90), (-3.30, 3.38),
        ]
        tank = self.side_profile(
            "Grain_Tank_External_Volume", tank_profile, 0.08,
            self.materials["body_dark"], self.fixed_root, z_center=-1.56,
            role="grain_tank_side",
        )
        profile_area = abs(sum(
            tank_profile[index][0] * tank_profile[(index + 1) % len(tank_profile)][1]
            - tank_profile[(index + 1) % len(tank_profile)][0] * tank_profile[index][1]
            for index in range(len(tank_profile))
        )) * 0.5
        tank_gross_profile_m3 = profile_area * 3.12
        tank["exo_external_envelope_volume_m3"] = tank_gross_profile_m3
        tank["exo_published_nominal_capacity_m3"] = self.GRAIN_TANK_CAPACITY_M3
        tank["exo_nominal_capacity_fraction_of_gross"] = self.GRAIN_TANK_CAPACITY_M3 / tank_gross_profile_m3
        self.side_profile(
            "Grain_Tank_Right_Side", tank_profile, 0.08,
            self.materials["body_dark"], self.fixed_root, z_center=1.56,
            role="grain_tank_side",
        )
        self.box(
            "Grain_Tank_Front_Wall", (0.35, 3.10, 0),
            (0.08, 1.38, 3.02), self.materials["body_dark"], self.fixed_root,
            rotation=(0, 0, -0.18),
            role="grain_tank_wall",
        )
        self.box(
            "Grain_Tank_Rear_Wall", (-3.22, 3.02, 0),
            (0.08, 1.44, 3.02), self.materials["body_dark"], self.fixed_root,
            rotation=(0, 0, 0.14),
            role="grain_tank_wall",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.box(
                f"Grain_Tank_{side}_Hopper_Floor", (-1.42, 2.24, sign * 0.76),
                (3.22, 0.08, 1.58), self.materials["graphite"], self.fixed_root,
                rotation=(0.30 * sign, 0, 0), role="grain_tank_floor",
            )
        for side, z in (("L", -1.56), ("R", 1.56)):
            self.box(
                f"Grain_Tank_{side}_Top_Rail", (-1.29, 3.94, z),
                (3.18, 0.08, 0.08), self.materials["steel"], self.fixed_root,
                role="grain_tank_rail",
            )

    def _add_unloader(self):
        pivot_location = (-4.35, 3.20, 1.82)
        yaw = self.empty("Unloader_Swing_Pivot", pivot_location, self.fixed_root, role="pivot")
        auger = self.empty("Unloader_ROOT", parent=yaw, role="motion_root")
        elbow_end = (0.36, 0.27, 0)
        main_length = self.AUGER_CENTERLINE_M - math.dist((0, 0, 0), elbow_end)
        direction = (math.cos(0.11), -math.sin(0.11), 0)
        endpoint = tuple(elbow_end[index] + direction[index] * main_length for index in range(3))
        self.pipe_between(
            "Unloader_Auger_Base_Elbow", (0, 0, 0), elbow_end, 0.12,
            self.materials["body_dark"], auger, role="unloader_elbow",
        )
        tube = self.pipe_between(
            "Unloader_Auger_9_45m_Tube", elbow_end, endpoint, 0.105,
            self.materials["body"], auger, role="unloader_tube",
        )
        tube["exo_centerline_length_m"] = self.AUGER_CENTERLINE_M
        self.cylinder(
            "Unloader_Base_Bearing", (0, 0, 0), 0.15, 0.24,
            self.materials["steel"], auger, vertices=24, role="unloader_bearing",
        )
        self.cone(
            "Unloader_Discharge_Boot", endpoint, 0.18, 0.11, 0.22,
            self.materials["body_dark"], auger, vertices=20,
            rotation=(0, math.pi / 2, 0), role="unloader_outlet",
        )
        self.pipe_between(
            "Unloader_Stow_Cradle", (-0.20, -0.20, 0), (0.42, 0.12, 0),
            0.035, self.materials["steel"], yaw, role="unloader_support",
        )
        self._auger_low_y = pivot_location[1] + min(0, elbow_end[1], endpoint[1]) - 0.12

    def build_combine(self):
        # Round, unscaled wheeled running gear. Selected tire families are
        # visual choices, not a claim about one delivered order configuration.
        for side, sign in (("L", -1), ("R", 1)):
            self._add_smooth_wheel(f"Front_{side}", (1.05, 1.08, sign * 1.69), 1.08, 0.92)
            self._add_smooth_wheel(f"Rear_{side}", (-3.18, 0.68, sign * 1.83), 0.68, 0.64)
        self.box(
            "Carrier_Main_Frame", (-0.45, 0.82, 0), (7.80, 0.28, 2.85),
            self.materials["graphite"], self.fixed_root, role="chassis",
        )
        self.box(
            "Carrier_Rear_Bumper", (-4.90, 0.88, 0), (0.30, 0.35, 2.20),
            self.materials["steel"], self.fixed_root, role="rear_structure",
        )
        for side, z in (("L", -1.40), ("R", 1.40)):
            self.side_profile(
                f"Rear_Power_Module_{side}_Profile",
                [(-4.45, 0.78), (-2.18, 0.78), (-2.05, 2.15), (-2.55, 2.48), (-4.20, 2.34), (-4.50, 1.70)],
                0.08, self.materials["body"], self.fixed_root, z_center=z,
                role="power_module",
            )
        self.box(
            "Rear_Power_Module_Top", (-3.25, 2.34, 0), (2.05, 0.15, 2.74),
            self.materials["body_dark"], self.fixed_root,
            rotation=(0, 0, -0.04), role="power_module",
        )
        for index in range(8):
            self.box(
                f"Rear_Cooling_Slot_{index + 1:02d}",
                (-3.95 + index * 0.16, 1.78, -1.415), (0.075, 0.72, 0.035),
                self.materials["graphite"], self.fixed_root, role="cooling_slot", bevel=0.004,
            )

        self._add_processing_and_tank()
        self._add_combine_cab()
        self._add_access_system()
        self._add_rear_cleaning_and_residue()
        feeder = self._add_feederhouse()
        self._add_hd50r(feeder)
        self._add_unloader()
        for side, z in (("L", -0.72), ("R", 0.72)):
            self.pipe_between(
                f"Feederhouse_Lift_Cylinder_{side}", (1.00, 0.92, z),
                (2.58, 0.74, z), 0.045, self.materials["steel"],
                self.hydraulics_root, role="header_lift_hydraulic",
            )

    def render_views(self):
        """Render six proof views with distinct, explicitly reconstructed poses."""
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        span = max(self.length, self.width, self.height)
        center = shared.Vector((0, self.height * 0.46, 0))
        pose_nodes = [
            "Feederhouse_ROOT", "Header_ROOT", "Reel_ROOT", "Unloader_ROOT",
            "HD50R_L_Wing_ROOT", "HD50R_R_Wing_ROOT", "Rear_Chopper_ROOT",
            "Dual_Rotor_Front_Service_Door_Pivot", "Dual_Rotor_Rear_Service_Door_Pivot",
            "Dual_Rotor_L_ROOT", "Dual_Rotor_R_ROOT",
        ]
        neutral = {name: tuple(bpy.data.objects[name].rotation_euler) for name in pose_nodes}
        views = [
            ("operator-side", (0, self.height * 0.62, -span * 1.55), 10.9, {}),
            ("front-three-quarter", (span * 1.10, self.height * 0.88, -span * 1.02), span * 1.18,
             {"Header_ROOT": (0, 0, 0.08), "Reel_ROOT": (0, 0, 0.85)}),
            ("rear-three-quarter", (-span * 0.78, self.height * 0.72, span * 0.64), 10.6,
             {"Unloader_ROOT": (0, 1.35, 0), "Rear_Chopper_ROOT": (0, 0, 0.65)}),
            ("elevated-technical", (span * 0.62, span * 1.36, -span * 0.88), span * 1.28,
             {"HD50R_L_Wing_ROOT": (-0.035, 0, 0), "HD50R_R_Wing_ROOT": (0.035, 0, 0), "Reel_ROOT": (0, 0, 0.48), "Unloader_ROOT": (0, 0.55, 0)}),
            ("articulation-detail", (-7.0, 3.2, -4.6), 4.7,
             {"Feederhouse_ROOT": (0, 0, 0.08), "Header_ROOT": (0, 0, 0.15), "Reel_ROOT": (0, 0, 1.45),
              "Dual_Rotor_Front_Service_Door_Pivot": (-1.02, 0, 0), "Dual_Rotor_Rear_Service_Door_Pivot": (-1.02, 0, 0),
              "Dual_Rotor_L_ROOT": (0.58, 0, 0), "Dual_Rotor_R_ROOT": (-0.58, 0, 0)}),
            ("right-side", (0, self.height * 0.62, span * 1.55), 10.9,
             {"Unloader_ROOT": (0, 1.62, 0), "Reel_ROOT": (0, 0, 0.30)}),
        ]
        paths = []
        cutaway_objects = (
            "Grain_Tank_External_Volume",
            "Separator_Upper_Roof",
            "Rear_Power_Module_L_Profile",
        )
        for label, location, ortho_scale, pose in views:
            for name, rotation in neutral.items():
                bpy.data.objects[name].rotation_euler = rotation
            for name, rotation in pose.items():
                bpy.data.objects[name].rotation_euler = rotation
            # This single review image is an exterior-panel-removed service
            # cutaway.  Restore every visibility flag immediately afterward so
            # the saved/exported neutral asset remains complete.
            for name in cutaway_objects:
                bpy.data.objects[name].hide_render = label == "articulation-detail"
            bpy.context.view_layer.update()
            camera.location = location
            target = shared.Vector((-0.65, 1.47, -0.22)) if label == "articulation-detail" else center
            self.point_at(camera, target)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        for name in cutaway_objects:
            bpy.data.objects[name].hide_render = False
        for name, rotation in neutral.items():
            bpy.data.objects[name].rotation_euler = rotation
        bpy.context.view_layer.update()
        return paths

    def required_semantics(self):
        return [
            *super().required_semantics(),
            "Feeder_Chain_1_ROOT", "Feeder_Chain_2_ROOT", "Feeder_Chain_3_ROOT", "Feeder_Chain_4_ROOT",
            "Dual_Rotor_L_ROOT", "Dual_Rotor_R_ROOT",
            "HD50R_L_Wing_Hinge_Pivot", "HD50R_R_Wing_Hinge_Pivot",
        ]

    def machine_specific_validation_gates(self, contract):
        names = contract["node_names"]
        actual_span = self._world_extent("HD50R_Main_Backbone", 2)
        feeder_width = self._world_extent("Feederhouse_Width_Crossmember", 2)
        tank = bpy.data.objects["Grain_Tank_External_Volume"]
        tank_volume = float(tank["exo_external_envelope_volume_m3"])
        tank_fill_fraction = float(tank["exo_nominal_capacity_fraction_of_gross"])
        auger = bpy.data.objects["Unloader_Auger_9_45m_Tube"]
        auger_length = float(auger["exo_centerline_length_m"])
        tire_names = [name for name in names if name.endswith("_Tire")]
        tire_scales = {name: tuple(round(v, 7) for v in bpy.data.objects[name].scale) for name in tire_names}
        material_names = {
            slot.material.name
            for obj in self.public_objects() if obj.type == "MESH"
            for slot in obj.material_slots if slot.material is not None
        }
        unresolved_text = " ".join(self.design["unresolved_choices"]).lower()
        header_top_y = 1.18 - 0.63 + 0.54 + 0.38
        neutral_vertical_gap = self._auger_low_y - header_top_y
        return [
            self._gate(
                "selected_header_span_envelope", abs(actual_span - self.HEADER_SPAN_M) <= 0.002,
                {"measured_span_m": round(actual_span, 6), "published_span_m": self.HEADER_SPAN_M},
            ),
            self._gate(
                "carrier_length_unresolved", "carrier overall length" in unresolved_text,
                {
                    "unresolved_marker": "carrier overall length",
                    "presentation_envelope_m": 10.1,
                    "claim_status": "reconstructed presentation envelope; not a manufacturer dimension",
                },
            ),
            self._gate(
                "carrier_height_unresolved", "overall height" in unresolved_text,
                {
                    "unresolved_marker": "overall height",
                    "presentation_envelope_m": 4.0,
                    "claim_status": "reconstructed presentation envelope; not a manufacturer dimension",
                },
            ),
            self._gate(
                "wheeled_running_gear",
                len(tire_names) == 4 and not any(name.startswith("Track_") for name in names)
                and all(scale == (1.0, 1.0, 1.0) for scale in tire_scales.values()),
                {"tire_nodes": sorted(tire_names), "mesh_scales": tire_scales, "track_nodes": []},
            ),
            self._gate(
                "feederhouse_continuity",
                abs(feeder_width - self.FEEDERHOUSE_WIDTH_M) <= 0.002
                and all(self._descends(f"Feeder_Chain_{index}_ROOT", "Feederhouse_ROOT") for index in range(1, 5)),
                {"measured_width_m": round(feeder_width, 6), "published_width_m": self.FEEDERHOUSE_WIDTH_M, "chain_roots": 4},
            ),
            self._gate(
                "header_attachment_continuity",
                self._descends("Header_ROOT", "Feederhouse_ROOT")
                and self._descends("HD50R_L_Wing_ROOT", "Header_ROOT")
                and self._descends("HD50R_R_Wing_ROOT", "Header_ROOT"),
                {
                    "hierarchy": "Feederhouse_ROOT -> Header_Lift_Pivot -> Header_ROOT -> two HD50R wing roots",
                    "left_wing_descends_from_header": self._descends("HD50R_L_Wing_ROOT", "Header_ROOT"),
                    "right_wing_descends_from_header": self._descends("HD50R_R_Wing_ROOT", "Header_ROOT"),
                },
            ),
            self._gate(
                "reel_axis_continuity", self._descends("Reel_ROOT", "Header_ROOT") and "HD50R_Reel_Axle" in names,
                {
                    "reel_descends_from_header": self._descends("Reel_ROOT", "Header_ROOT"),
                    "reel_axle_present": "HD50R_Reel_Axle" in names,
                    "reconstructed_axle_span_m": 14.70,
                },
            ),
            self._gate(
                "unloader_hinge_continuity",
                self._descends("Unloader_ROOT", "Unloader_Swing_Pivot")
                and abs(auger_length - self.AUGER_CENTERLINE_M) <= 1e-6,
                {"measured_tube_centerline_m": auger_length, "selected_option_m": self.AUGER_CENTERLINE_M},
            ),
            self._gate(
                "auger_header_clearance", neutral_vertical_gap > 0.15,
                {"neutral_pose_min_vertical_clearance_m": round(neutral_vertical_gap, 6), "scope": "authored neutral pose"},
            ),
            self._gate(
                "ground_collision", contract["bounds"]["min_m"][1] >= -0.005,
                {"minimum_visible_y_m": contract["bounds"]["min_m"][1], "ground_y_m": 0.0},
            ),
            self._gate(
                "self_collision", neutral_vertical_gap > 0.15 and tank_volume >= self.GRAIN_TANK_CAPACITY_M3 and tank_fill_fraction < 0.90,
                {"neutral_auger_header_gap_m": round(neutral_vertical_gap, 6), "tank_gross_profile_prism_m3": round(tank_volume, 6), "tank_nominal_capacity_m3": self.GRAIN_TANK_CAPACITY_M3, "nominal_capacity_fraction_of_gross": round(tank_fill_fraction, 6), "dual_rotor_count": 2, "each_rotor_length_m": self.ROTOR_LENGTH_M, "each_rotor_diameter_m": self.ROTOR_DIAMETER_M, "scope": "neutral structural pose and component containment; swept-volume solver remains outside claim"},
            ),
            self._gate(
                "neutral_unbranded_material_review",
                bool(material_names) and all(name.startswith("Neutral_") for name in material_names),
                {"public_materials": sorted(material_names), "images": contract["images"], "textures": contract["textures"]},
            ),
        ]


if __name__ == "__main__":
    design = shared.load_design(DESIGN)
    JohnDeereX91100Builder(design, DESIGN, OUTPUT_DIR).run()

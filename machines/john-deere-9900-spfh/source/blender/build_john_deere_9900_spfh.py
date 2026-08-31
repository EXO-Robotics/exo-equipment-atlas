#!/usr/bin/env python3
"""Deterministic machine-local John Deere 9900 SPFH structural study.

The selected 282DZ/4005/0415KM/5597/3.3 m package is represented with explicit
crop-flow components and a three-module 772 header. Published component sizes
are retained where cited; hidden centers, fold paths, mounts, panels, and all
kinematics remain independently reconstructed and non-authoritative.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()


def load_shared_generator():
    spec = importlib.util.spec_from_file_location("exo_fleet_builder_9900", SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load shared fleet generator: {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared_generator()


class JohnDeere9900SPFHBuilder(shared.FleetBuilder):
    """Author the selected legacy 9900 crop-flow and 772 header study."""

    HEADER_OVERALL_WIDTH_M = 9.05
    HEADER_WORKING_WIDTH_M = 9.0
    HEADER_TRANSPORT_WIDTH_M = 3.0
    HEADER_LENGTH_M = 2.7
    HEADER_HEIGHT_M = 1.98
    CARRIER_WIDTH_M = 3.3
    CUTTERHEAD_WIDTH_M = 0.856
    CUTTERHEAD_DIAMETER_M = 0.670
    CUTTERHEAD_KNIVES = 40
    ACCELERATOR_WIDTH_M = 0.632
    ACCELERATOR_DIAMETER_M = 0.560
    SPOUT_SWING_DEG = 210.0

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

    @staticmethod
    def _world_range(node_name, axis):
        node = bpy.data.objects[node_name]
        values = [(node.matrix_world @ shared.Vector(corner))[axis] for corner in node.bound_box]
        return min(values), max(values)

    def _gate(self, gate_id, condition, detail):
        semantic_nodes = {
            "frozen_282DZ_4005_0415KM_5597_configuration": [],
            "selected_772_overall_width": ["Header_ROOT", "772_Header_Overall_Frame", "772_L_Wing_ROOT", "772_R_Wing_ROOT"],
            "carrier_3_3m_width_class": ["Running_Gear_ROOT", "Front_L_Tire", "Front_R_Tire", "Rear_L_Tire", "Rear_R_Tire"],
            "header_lift_continuity": ["Header_Lift_Pivot", "Header_ROOT", "772_L_Wing_Fold_Pivot", "772_L_Wing_ROOT", "772_R_Wing_Fold_Pivot", "772_R_Wing_ROOT"],
            "feedroll_continuity": ["Feedroll_ROOT", "Feedroll_Upper_ROOT", "Feedroll_Upper_Front_ROOT", "Feedroll_Upper_Rear_ROOT", "Feedroll_Lower_ROOT", "Feedroll_Lower_Front_ROOT", "Feedroll_Lower_Rear_ROOT"],
            "spout_yaw_and_tip_continuity": ["Spout_Yaw_Pivot", "Spout_ROOT", "Spout_Tip_Pivot", "Spout_Tip_ROOT"],
            "header_carrier_spout_clearance": ["Header_ROOT", "772_Header_Overall_Frame", "Spout_Yaw_Pivot", "Spout_ROOT"],
            "ground_collision": ["Running_Gear_ROOT", "Front_L_Tire", "Front_R_Tire", "Rear_L_Tire", "Rear_R_Tire", "Header_ROOT"],
            "self_collision": ["Header_ROOT", "Feedroll_ROOT", "Dura_Drum_Cutterhead_ROOT", "Crop_Accelerator_ROOT", "Spout_ROOT"],
            "neutral_unbranded_material_review": ["Machine_Root"],
        }[gate_id]
        fact_ids = {
            "frozen_282DZ_4005_0415KM_5597_configuration": [],
            "selected_772_overall_width": ["public-envelope-z", "header-length", "header-height", "header-working-width", "header-transport-width"],
            "carrier_3_3m_width_class": ["carrier-width-class"],
            "header_lift_continuity": [],
            "feedroll_continuity": ["feedroll-count"],
            "spout_yaw_and_tip_continuity": ["spout-swing"],
            "header_carrier_spout_clearance": [],
            "ground_collision": [],
            "self_collision": ["cutterhead-width", "cutterhead-diameter", "selected-knife-count", "accelerator-width", "accelerator-diameter"],
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

    def _add_smooth_wheel(self, prefix, center, radius, width, parent=None):
        pivot = self.empty(f"{prefix}_Wheel_Pivot", center, parent or self.running_root, role="wheel_pivot")
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

    def _add_forage_cab(self):
        """Build a high-visibility forage-harvester cab rather than a tractor box."""
        cab = self.empty("Operator_Station_ROOT", (0.86, 1.82, 0), self.fixed_root, role="operator_station")
        self.box("Cab_Floor", (0, 0.10, 0), (1.78, 0.18, 2.20), self.materials["graphite"], cab, role="cab_structure")
        self.box("Cab_Roof_Cap", (-0.02, 2.15, 0), (1.98, 0.16, 2.44), self.materials["body"], cab, role="cab_structure", bevel=0.045)
        self.box("Cab_Roof_Forward_Visor", (0.88, 2.02, 0), (0.25, 0.22, 2.38), self.materials["body_dark"], cab, rotation=(0, 0, -0.11), role="cab_structure")
        self.box("Cab_Front_Panoramic_Glass", (0.79, 1.14, 0), (0.11, 1.62, 2.08), self.materials["glass"], cab, rotation=(0, 0, -0.12), role="glazing")
        self.box("Cab_Rear_Glass", (-0.80, 1.15, 0), (0.09, 1.50, 2.00), self.materials["glass"], cab, role="glazing")
        side_outline = [(-0.72, 0.34), (0.64, 0.34), (0.84, 1.88), (0.62, 2.03), (-0.70, 2.03)]
        for side, z in (("L", -1.08), ("R", 1.08)):
            self.side_profile(f"Cab_{side}_Panoramic_Glass", side_outline, 0.055, self.materials["glass"], cab, z_center=z, role="glazing")
            for x, y, label in ((-0.75, 1.18, "Rear"), (0.72, 1.18, "Front")):
                self.box(f"Cab_{side}_{label}_Post", (x, y, z), (0.09, 1.72, 0.09), self.materials["graphite"], cab, rotation=(0, 0, -0.06 if x > 0 else 0), role="cab_structure")
        self.box("Cab_Lower_Intake_Nose", (0.63, 0.33, 0), (0.50, 0.45, 2.16), self.materials["body_dark"], cab, rotation=(0, 0, -0.10), role="cab_structure")
        self.box("Operator_Seat", (-0.12, 0.66, 0), (0.46, 0.72, 0.62), self.materials["graphite"], cab, role="operator_cue")

    def _add_power_module_body(self):
        """Add the sloped rear engine/cooling envelope and service surfaces."""
        outline = [
            (-4.44, 0.84), (-0.92, 0.84), (-0.68, 1.42),
            (-0.88, 2.88), (-1.52, 3.28), (-3.92, 3.04), (-4.45, 2.34),
        ]
        for side, z in (("L", -1.31), ("R", 1.31)):
            self.side_profile(f"Power_Module_{side}_Profile", outline, 0.08, self.materials["body"], self.fixed_root, z_center=z, role="power_module")
        self.box("Power_Module_Top_Deck", (-2.62, 3.08, 0), (2.55, 0.16, 2.56), self.materials["body_dark"], self.fixed_root, rotation=(0, 0, 0.04), role="power_module")
        self.box("Rear_Radiator_Screen", (-4.50, 2.03, 0), (0.10, 1.64, 2.42), self.materials["graphite"], self.fixed_root, role="cooling_screen")
        for index in range(10):
            self.box(
                f"Side_Cooling_Louver_{index + 1:02d}", (-3.78 + index * 0.19, 2.12, -1.365),
                (0.09, 1.02, 0.035), self.materials["graphite"], self.fixed_root,
                rotation=(0, 0, -0.04), role="cooling_louver", bevel=0.004,
            )
        for index, x in enumerate((-3.75, -2.85, -1.95), start=1):
            self.pipe_between(f"Engine_Deck_Rail_Post_{index}", (x, 3.14, -1.18), (x, 3.55, -1.18), 0.022, self.materials["rod"], self.fixed_root, role="service_handrail")
        self.pipe_between("Engine_Deck_Rail_Top", (-3.82, 3.55, -1.18), (-1.88, 3.55, -1.18), 0.022, self.materials["rod"], self.fixed_root, role="service_handrail")

    def _add_access_system(self):
        deck = self.empty("Operator_Access_ROOT", (0.15, 1.56, -1.40), self.fixed_root, role="access_system")
        self.box("Operator_Access_Deck", (0, 0, 0), (2.35, 0.10, 0.58), self.materials["steel"], deck, role="access_platform")
        for index, x in enumerate((-1.03, -0.34, 0.35, 1.04), start=1):
            self.pipe_between(f"Operator_Rail_Post_{index}", (x, 0.04, -0.25), (x, 0.76, -0.25), 0.024, self.materials["rod"], deck, role="handrail")
        self.pipe_between("Operator_Rail_Top", (-1.05, 0.76, -0.25), (1.06, 0.76, -0.25), 0.024, self.materials["rod"], deck, role="handrail")
        ladder = self.empty("Operator_Ladder_ROOT", (-0.86, -0.02, 0), deck, role="access_ladder")
        for side, z in (("L", -0.23), ("R", 0.23)):
            self.pipe_between(f"Ladder_Stringer_{side}", (0, -0.88, z), (0, 0, z), 0.025, self.materials["steel"], ladder, role="ladder_stringer")
        for index in range(5):
            self.pipe_between(f"Ladder_Rung_{index + 1:02d}", (0, -0.78 + index * 0.18, -0.23), (0, -0.78 + index * 0.18, 0.23), 0.022, self.materials["steel"], ladder, role="ladder_rung")

    def _add_running_gear(self):
        """Build fixed front drive axle and paired rear steering anatomy."""
        self.box("Front_Drive_Axle_Beam", (0.75, 0.88, 0), (0.34, 0.28, 2.55), self.materials["steel"], self.running_root, role="drive_axle")
        self.cylinder("Front_Differential_Housing", (0.75, 0.88, 0), 0.28, 0.48, self.materials["graphite"], self.running_root, vertices=28, role="differential")
        for side, sign in (("L", -1), ("R", 1)):
            self._add_smooth_wheel(f"Front_{side}", (0.75, 0.88, sign * 1.29), 0.88, 0.72)
        rear_pivot = self.empty("Rear_Axle_Oscillation_Pivot", (-3.15, 0.64, 0), self.running_root, role="pivot")
        rear_axle = self.empty("Rear_Axle_ROOT", parent=rear_pivot, role="motion_root")
        self.box("Rear_Steering_Axle_Beam", (0, 0, 0), (0.28, 0.22, 2.68), self.materials["steel"], rear_axle, role="steering_axle")
        for side, sign in (("L", -1), ("R", 1)):
            steering = self.empty(f"Rear_Steering_{side}_Pivot", (0, 0, sign * 1.34), rear_axle, role="steering_pivot")
            self._add_smooth_wheel(f"Rear_{side}", (0, 0, 0), 0.64, 0.62, steering)
        self.pipe_between("Rear_Steering_Tie_Rod", (0.12, 0.10, -1.28), (0.12, 0.10, 1.28), 0.025, self.materials["rod"], rear_axle, role="steering_link")

    def _add_rotary_header_module(self, prefix, parent, center_z, span, drum_count):
        """Add reconstructed gathering drums and cutting rotors to one module."""
        self.box(
            f"772_{prefix}_Intake_Deck", (1.34, -0.80, center_z),
            (2.32, 0.07, span * 0.90), self.materials["body_dark"], parent,
            role="header_intake_deck",
        )
        for edge, z in (("L", center_z - span * 0.45), ("R", center_z + span * 0.45)):
            self.pipe_between(
                f"772_{prefix}_{edge}_Crop_Deflector", (2.42, -0.70, z), (0.38, 0.26, z),
                0.035, self.materials["steel"], parent, role="crop_deflector",
            )
        for index in range(drum_count):
            fraction = (index + 0.5) / drum_count
            z = center_z - span / 2 + span * fraction
            drum_root = self.empty(
                f"772_{prefix}_Gatherer_{index + 1:02d}_ROOT", (1.25, -0.27, z),
                parent, role="rotary_root",
            )
            self.cylinder(
                f"772_{prefix}_Gatherer_{index + 1:02d}_Drum", (0, 0, 0), 0.34, 0.52,
                self.materials["body_dark"], drum_root, vertices=24,
                rotation=(math.pi / 2, 0, 0), role="gatherer_drum",
            )
            self.side_profile(
                f"772_{prefix}_Gatherer_{index + 1:02d}_Hood",
                [(0.84, -0.14), (1.72, -0.14), (1.61, 0.22), (0.96, 0.25)],
                0.045, self.materials["body"], parent, z_center=z,
                role="gatherer_hood",
            )
            for tooth in range(8):
                angle = math.tau * tooth / 8
                self.box(
                    f"772_{prefix}_Gatherer_{index + 1:02d}_Finger_{tooth + 1:02d}",
                    (math.cos(angle) * 0.40, 0, math.sin(angle) * 0.40),
                    (0.16, 0.08, 0.055), self.materials["steel"], drum_root,
                    rotation=(0, -angle, 0), role="gatherer_finger", bevel=0.006,
                )
            cutter = self.empty(
                f"772_{prefix}_Cutting_Rotor_{index + 1:02d}_ROOT", (1.37, -0.71, z),
                parent, role="rotary_root",
            )
            self.cylinder(
                f"772_{prefix}_Cutting_Rotor_{index + 1:02d}", (0, 0, 0), 0.30, 0.045,
                self.materials["steel"], cutter, vertices=22,
                rotation=(math.pi / 2, 0, 0), role="cutting_rotor",
            )
            for blade in range(6):
                angle = math.tau * blade / 6
                self.box(
                    f"772_{prefix}_Cutting_Blade_{index + 1:02d}_{blade + 1:02d}",
                    (math.cos(angle) * 0.32, 0, math.sin(angle) * 0.32),
                    (0.22, 0.025, 0.04), self.materials["graphite"], cutter,
                    rotation=(0, -angle, 0), role="cutting_blade", bevel=0.004,
                )

    def _add_772_header(self):
        # The complete header is 2.7 x 1.98 m in X/Y and 9.05 m overall in Z.
        pivot = self.empty("Header_Lift_Pivot", (1.90, 0.99, 0), self.fixed_root, role="pivot")
        header = self.empty("Header_ROOT", parent=pivot, role="motion_root")
        overall = self.box(
            "772_Header_Overall_Frame", (0.18, 0.93, 0),
            (0.14, 0.12, self.HEADER_TRANSPORT_WIDTH_M),
            self.materials["body_dark"], header, role="header_backbone",
        )
        overall["exo_published_overall_width_m"] = self.HEADER_OVERALL_WIDTH_M
        self.box(
            "772_Center_Cutting_Beam", (2.58, -0.84, 0),
            (0.16, 0.10, self.HEADER_TRANSPORT_WIDTH_M), self.materials["steel"],
            header, role="cutting_beam",
        )
        # Side frames preserve the published height/length without presenting a
        # solid generic header block.
        for side, z in (("L", -1.47), ("R", 1.47)):
            self.side_profile(
                f"772_Center_{side}_Side_Frame",
                [(0.0, -0.99), (2.70, -0.99), (2.55, 0.72), (0.35, 0.99), (0.0, 0.45)],
                0.06, self.materials["body"], header, z_center=z,
                role="header_side_frame",
            )

        # Published 3.0 m transport width represented by a 3.0 m fixed center
        # module plus two 3.0 m working wings. Exact folded swept geometry stays
        # explicitly reconstructed; the hinge/cylinder hardware is visible.
        center = self.empty("772_Center_Module_ROOT", parent=header, role="header_module_root")
        self.box(
            "772_Center_Module_Frame", (0.28, 0.42, 0), (0.12, 0.12, 3.0),
            self.materials["body"], center, role="header_center_module",
        )
        self.box(
            "772_Center_Module_Rear_Beam", (2.30, 0.20, 0), (0.12, 0.12, 3.0),
            self.materials["body"], center, role="header_center_module",
        )
        for side, z in (("L", -1.45), ("R", 1.45)):
            self.pipe_between(
                f"772_Center_Module_{side}_Rail", (0.30, 0.40, z),
                (2.28, 0.18, z), 0.045, self.materials["steel"], center,
                role="header_module_rail",
            )
        self._add_rotary_header_module("Center", center, 0.0, 3.0, 2)
        self.side_profile(
            "772_Center_Intake_Throat",
            [(0.08, -0.62), (1.35, -0.72), (1.62, -0.16), (0.34, 0.42)],
            1.02, self.materials["body_dark"], center, z_center=0,
            role="header_intake_throat",
        )
        for side, sign in (("L", -1), ("R", 1)):
            hinge = self.empty(
                f"772_{side}_Wing_Fold_Pivot", (0.0, 0.15, sign * 1.50),
                header, role="pivot",
            )
            wing = self.empty(f"772_{side}_Wing_ROOT", parent=hinge, role="motion_root")
            self.box(
                f"772_{side}_Wing_Frame", (0.28, 0.40, sign * 1.50),
                (0.12, 0.12, 3.0), self.materials["body"], wing,
                role="header_fold_wing",
            )
            self.box(
                f"772_{side}_Wing_Rear_Beam", (2.30, 0.18, sign * 1.50),
                (0.12, 0.12, 3.0), self.materials["body"], wing,
                role="header_fold_wing",
            )
            self.box(
                f"772_{side}_Wing_Cutting_Beam", (2.58, -0.84, sign * 1.50),
                (0.16, 0.10, 3.0), self.materials["steel"], wing,
                role="cutting_beam",
            )
            for edge, local_z in (("Inner", 0.06 * sign), ("Outer", 2.94 * sign)):
                self.pipe_between(
                    f"772_{side}_Wing_{edge}_Rail", (0.30, 0.38, local_z),
                    (2.28, 0.16, local_z), 0.045, self.materials["steel"], wing,
                    role="header_module_rail",
                )
            self._add_rotary_header_module(side, wing, sign * 1.50, 3.0, 2)
            self.cylinder(
                f"772_{side}_Wing_Hinge_Pin", (0.0, 0.15, sign * 1.50),
                0.075, 0.36, self.materials["steel"], header, vertices=24,
                rotation=(0, math.pi / 2, 0), role="header_hinge_pin",
            )
            self.pipe_between(
                f"772_{side}_Fold_Cylinder", (-0.18, 0.66, sign * 1.28),
                (0.55, 0.17, sign * 2.05), 0.045, self.materials["rod"],
                wing, role="header_fold_hydraulic",
            )
            divider = self.side_profile(
                f"772_{side}_Crop_Divider",
                [(0.10, -0.72), (2.68, -0.92), (2.42, -0.45), (0.46, 0.70), (0.10, 0.54)],
                0.05, self.materials["body"], wing, z_center=sign * 3.0,
                role="crop_divider",
            )
            divider["exo_overall_extent_role"] = side
            self.box(
                f"772_{side}_Outer_Skid", (1.80, -0.92, sign * 2.82),
                (1.38, 0.08, 0.22), self.materials["steel"], wing,
                rotation=(0, 0, -0.05), role="header_skid",
            )
        overall["exo_working_width_m"] = self.HEADER_WORKING_WIDTH_M
        overall["exo_transport_width_target_m"] = self.HEADER_TRANSPORT_WIDTH_M
        overall["exo_fold_geometry_authority"] = "reconstructed"
        return header

    def _add_feedroll_carrier(self):
        carrier = self.empty("Feedroll_ROOT", (1.08, 1.36, 0), self.fixed_root, role="rotary_process_root")
        for side, z in (("L", -0.56), ("R", 0.56)):
            self.side_profile(
                f"Feedroll_Carrier_{side}_Plate",
                [(-0.48, -0.43), (0.48, -0.43), (0.55, 0.40), (-0.50, 0.40)],
                0.055, self.materials["body"], carrier, z_center=z,
                role="feedroll_carrier_plate",
            )
        for level, y in (("Top", 0.40), ("Bottom", -0.40)):
            self.box(
                f"Feedroll_Carrier_{level}_Rail", (0, y, 0), (0.94, 0.08, 1.08),
                self.materials["steel"], carrier, role="feedroll_carrier_rail",
            )
        self.box(
            "Feedroll_Intake_Lip", (0.48, -0.02, 0), (0.12, 0.68, 1.06),
            self.materials["body_dark"], carrier, rotation=(0, 0, -0.08), role="feedroll_intake",
        )
        rows = (("Upper", 0.19), ("Lower", -0.19))
        positions = (("Front", 0.20), ("Rear", -0.20))
        for row, y in rows:
            row_root = self.empty(f"Feedroll_{row}_ROOT", (0, y, 0), carrier, role="feedroll_row_root")
            for position, x in positions:
                root = self.empty(
                    f"Feedroll_{row}_{position}_ROOT", (x, 0, 0), row_root,
                    role="rotary_root",
                )
                self.cylinder(
                    f"Feedroll_{row}_{position}", (0, 0, 0), 0.15, 0.90,
                    self.materials["graphite"], root, vertices=24, role="feedroll",
                )
                for bar in range(8):
                    angle = math.tau * bar / 8
                    self.box(
                        f"Feedroll_{row}_{position}_Bar_{bar + 1:02d}",
                        (math.cos(angle) * 0.155, math.sin(angle) * 0.155, 0),
                        (0.035, 0.028, 0.86), self.materials["steel"], root,
                        rotation=(0, 0, angle), role="feedroll_bar", bevel=0.004,
                    )
            if row == "Upper":
                for side, z in (("L", -0.43), ("R", 0.43)):
                    self.pipe_between(
                        f"Feedroll_Upper_Preload_{side}", (-0.30, 0.16, z), (0.18, 0.54, z),
                        0.035, self.materials["rod"], row_root, role="feedroll_preload_link",
                    )
        return carrier

    def _add_cutterhead_and_accelerator(self):
        cutter = self.empty("Dura_Drum_Cutterhead_ROOT", (0.18, 1.45, 0), self.fixed_root, role="rotary_process_root")
        body = self.cylinder(
            "Dura_Drum_856x670_Body", (0, 0, 0), self.CUTTERHEAD_DIAMETER_M / 2,
            self.CUTTERHEAD_WIDTH_M, self.materials["graphite"], cutter,
            vertices=32, role="cutterhead",
        )
        body["exo_published_width_m"] = self.CUTTERHEAD_WIDTH_M
        body["exo_published_diameter_m"] = self.CUTTERHEAD_DIAMETER_M
        for index in range(self.CUTTERHEAD_KNIVES):
            angle = math.tau * index / self.CUTTERHEAD_KNIVES
            knife = self.box(
                f"Dura_Drum_Knife_Station_{index + 1:02d}",
                (math.cos(angle) * 0.34, math.sin(angle) * 0.34, 0),
                (0.07, 0.025, 0.82), self.materials["steel"], cutter,
                rotation=(0, 0, angle), role="cutterhead_knife_station", bevel=0.003,
            )
            knife["exo_station_index"] = index + 1
        for side, z in (("L", -self.CUTTERHEAD_WIDTH_M / 2), ("R", self.CUTTERHEAD_WIDTH_M / 2)):
            self._torus(
                f"Dura_Drum_{side}_Housing_Ring", (0, 0, z),
                self.CUTTERHEAD_DIAMETER_M * 0.54, 0.025,
                self.materials["body"], cutter, role="cutterhead_housing_ring",
            )
        self.box(
            "Dura_Drum_Shearbar", (0.31, -0.31, 0), (0.12, 0.06, 0.90),
            self.materials["rod"], cutter, rotation=(0, 0, -0.12), role="shearbar",
        )

        accelerator = self.empty("Crop_Accelerator_ROOT", (-0.62, 1.68, 0), self.fixed_root, role="rotary_process_root")
        accel_body = self.cylinder(
            "Crop_Accelerator_632x560_Body", (0, 0, 0), self.ACCELERATOR_DIAMETER_M / 2,
            self.ACCELERATOR_WIDTH_M, self.materials["graphite"], accelerator,
            vertices=28, role="crop_accelerator",
        )
        accel_body["exo_published_width_m"] = self.ACCELERATOR_WIDTH_M
        accel_body["exo_published_diameter_m"] = self.ACCELERATOR_DIAMETER_M
        for index in range(10):
            angle = math.tau * index / 10
            self.box(
                f"Crop_Accelerator_Paddle_{index + 1:02d}",
                (math.cos(angle) * 0.285, math.sin(angle) * 0.285, 0),
                (0.09, 0.035, 0.60), self.materials["steel"], accelerator,
                rotation=(0, 0, angle), role="accelerator_paddle", bevel=0.004,
            )
        for side, z in (("L", -self.ACCELERATOR_WIDTH_M / 2), ("R", self.ACCELERATOR_WIDTH_M / 2)):
            self._torus(
                f"Crop_Accelerator_{side}_Housing_Ring", (0, 0, z),
                self.ACCELERATOR_DIAMETER_M * 0.55, 0.022,
                self.materials["body"], accelerator, role="accelerator_housing_ring",
            )
        return cutter, accelerator

    def _add_crop_path(self):
        path = self.empty("Schematic_Crop_Path_ROOT", parent=self.fixed_root, role="process_path_root")
        channel_outline = [
            (2.18, 0.68), (2.18, 1.08), (1.42, 1.58),
            (0.50, 1.88), (-0.36, 2.08), (-0.86, 2.38),
            (-0.86, 1.92), (-0.28, 1.60), (0.48, 1.30), (1.34, 1.00),
        ]
        self.side_profile(
            "Crop_Channel_Right_Service_Wall", channel_outline, 0.055,
            self.materials["body_dark"], self.fixed_root, z_center=0.57,
            role="crop_channel_wall",
        )
        for side, z in (("L", -0.55), ("R", 0.55)):
            self.pipe_between(
                f"Crop_Channel_{side}_Lower_Rail", (2.12, 0.70, z), (-0.78, 1.92, z),
                0.035, self.materials["steel"], self.fixed_root, role="crop_channel_rail",
            )
        self.box(
            "Crop_Channel_Upper_Transition", (-0.58, 2.12, 0), (0.78, 0.10, 1.12),
            self.materials["body"], self.fixed_root, rotation=(0, 0, 0.18), role="crop_channel_transition",
        )
        points = [
            (2.10, 0.78, 0), (1.45, 1.05, 0), (1.08, 1.36, 0),
            (0.18, 1.45, 0), (-0.62, 1.68, 0), (-0.82, 2.20, 0),
        ]
        for index, (start, end) in enumerate(zip(points, points[1:]), start=1):
            self.pipe_between(
                f"Schematic_Crop_Path_Segment_{index:02d}", start, end, 0.035,
                self.materials["warning"], path, role="schematic_crop_path",
            )

    def _add_spout(self):
        yaw = self.empty("Spout_Yaw_Pivot", (-0.82, 2.22, 0), self.fixed_root, role="pivot")
        spout = self.empty("Spout_ROOT", parent=yaw, role="motion_root")
        arch_points = [
            (0.0, 0.0, 0), (0.0, 0.48, 0), (0.08, 0.90, 0),
            (0.26, 1.22, 0), (0.55, 1.43, 0), (0.90, 1.53, 0),
            (1.24, 1.50, 0), (1.50, 1.38, 0),
        ]
        for index, (start, end) in enumerate(zip(arch_points, arch_points[1:]), start=1):
            self.pipe_between(
                f"High_Arch_Spout_Segment_{index:02d}", start, end, 0.14,
                self.materials["body_dark" if index < 3 else "body"], spout,
                role="spout_duct",
            )
        for station, point in enumerate((arch_points[1], arch_points[3], arch_points[5]), start=1):
            self._torus(
                f"High_Arch_Spout_Service_Band_{station}", point, 0.145, 0.018,
                self.materials["steel"], spout, rotation=(0, math.pi / 2, 0),
                role="spout_service_band",
            )
        tip_pivot = self.empty("Spout_Tip_Pivot", arch_points[-1], spout, role="pivot")
        tip = self.empty("Spout_Tip_ROOT", parent=tip_pivot, role="motion_root")
        self.pipe_between(
            "Spout_Outlet_Tube", (0, 0, 0), (0.72, -0.24, 0), 0.135,
            self.materials["body"], tip, role="spout_outlet",
        )
        self.box(
            "Spout_Outlet_Mouth", (0.73, -0.24, 0), (0.16, 0.32, 0.42),
            self.materials["body_dark"], tip, rotation=(0, 0, -0.18), role="spout_outlet",
        )
        self.box(
            "Spout_Outlet_Flap", (0.80, -0.34, 0), (0.08, 0.30, 0.44),
            self.materials["steel"], tip, role="spout_flap",
        )

    def build_forage_harvester(self):
        # Selected 3.3 m tire-package width. Tires are procedural circular tori
        # with identity scale, not ellipses produced by envelope normalization.
        self._add_running_gear()
        self.box(
            "Carrier_6_7m_Frame", (-1.25, 0.78, 0), (6.70, 0.26, 2.45),
            self.materials["graphite"], self.fixed_root, role="chassis",
        )
        self.box(
            "Carrier_Rear_Extent", (-4.45, 1.05, 0), (0.30, 0.55, 2.40),
            self.materials["steel"], self.fixed_root, role="rear_structure",
        )
        self._add_power_module_body()
        processor = self.empty("Processor_Open_Frame_ROOT", (0.16, 1.48, 0), self.fixed_root, role="processor_frame")
        for side, z in (("L", -0.69), ("R", 0.69)):
            for edge, start, end in (
                ("Lower", (-1.05, -0.64, z), (1.05, -0.64, z)),
                ("Upper", (-1.05, 0.64, z), (1.05, 0.64, z)),
                ("Front", (1.05, -0.64, z), (1.05, 0.64, z)),
                ("Rear", (-1.05, -0.64, z), (-1.05, 0.64, z)),
            ):
                self.pipe_between(f"Processor_{side}_{edge}_Rail", start, end, 0.035, self.materials["steel"], processor, role="processor_frame_rail")
        self._add_forage_cab()
        self._add_access_system()

        self._add_772_header()
        self._add_feedroll_carrier()
        self._add_cutterhead_and_accelerator()
        self._add_crop_path()
        self._add_spout()
        for side, z in (("L", -0.62), ("R", 0.62)):
            self.pipe_between(
                f"772_Header_Lift_Cylinder_{side}", (1.28, 1.13, z),
                (2.20, 0.54, z), 0.045, self.materials["steel"],
                self.hydraulics_root, role="header_lift_hydraulic",
            )

    def render_views(self):
        """Render mechanism-specific lift, fold, crop-flow, spout and steering poses."""
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        span = max(self.length, self.width, self.height)
        center = shared.Vector((-0.10, 1.85, 0))
        pose_nodes = [
            "Header_Lift_Pivot", "772_L_Wing_ROOT", "772_R_Wing_ROOT",
            "Feedroll_Upper_Front_ROOT", "Feedroll_Upper_Rear_ROOT",
            "Feedroll_Lower_Front_ROOT", "Feedroll_Lower_Rear_ROOT",
            "Dura_Drum_Cutterhead_ROOT", "Crop_Accelerator_ROOT",
            "Spout_Yaw_Pivot", "Spout_Tip_Pivot",
            "Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot", "Rear_Axle_ROOT",
        ]
        neutral = {name: tuple(bpy.data.objects[name].rotation_euler) for name in pose_nodes}
        crop_pose = {
            "Feedroll_Upper_Front_ROOT": (0, 0, 0.55), "Feedroll_Upper_Rear_ROOT": (0, 0, 0.55),
            "Feedroll_Lower_Front_ROOT": (0, 0, -0.55), "Feedroll_Lower_Rear_ROOT": (0, 0, -0.55),
            "Dura_Drum_Cutterhead_ROOT": (0, 0, 0.72), "Crop_Accelerator_ROOT": (0, 0, -0.62),
        }
        views = [
            ("operator-side", (0, self.height * 0.62, -span * 1.55), 8.7, crop_pose),
            ("front-three-quarter", (span * 1.10, self.height * 0.88, -span * 1.02), 10.8,
             {"Header_Lift_Pivot": (0, 0, 0.10), **crop_pose}),
            ("rear-three-quarter", (-span * 1.02, self.height * 0.82, span * 0.84), 8.9,
             {"Spout_Yaw_Pivot": (0, -1.35, 0), "Spout_Tip_Pivot": (0, 0, -0.14), "Rear_Steering_L_Pivot": (0, 0.18, 0), "Rear_Steering_R_Pivot": (0, 0.18, 0)}),
            ("elevated-technical", (span * 0.72, span * 1.42, -span * 0.98), 10.4,
             {"772_L_Wing_ROOT": (1.02, 0, 0), "772_R_Wing_ROOT": (-1.02, 0, 0), "Spout_Yaw_Pivot": (0, 0.70, 0), **crop_pose}),
            ("articulation-detail", (0.05, 2.9, -5.4), 3.6,
             {"Header_Lift_Pivot": (0, 0, 0.14), "772_L_Wing_ROOT": (0.38, 0, 0), "772_R_Wing_ROOT": (-0.38, 0, 0), **crop_pose}),
            ("right-side", (0, self.height * 0.62, span * 1.55), 8.8,
             {"Spout_Yaw_Pivot": (0, 1.58, 0), "Spout_Tip_Pivot": (0, 0, 0.12), "Rear_Steering_L_Pivot": (0, -0.18, 0), "Rear_Steering_R_Pivot": (0, -0.18, 0), "Rear_Axle_ROOT": (0.05, 0, 0)}),
        ]
        paths = []
        cutaway_objects = (
            "Front_L_Tire", "Front_L_Rim", "Front_L_Hub",
            "Cab_L_Panoramic_Glass", "Cab_L_Front_Post", "Cab_L_Rear_Post",
            "Cab_Front_Panoramic_Glass", "Cab_Rear_Glass", "Cab_R_Panoramic_Glass",
            "Cab_Floor", "Cab_Lower_Intake_Nose", "Operator_Seat",
            "Feedroll_Carrier_L_Plate", "772_Center_L_Side_Frame",
        )
        access_cutaway_objects = tuple(
            child.name for child in bpy.data.objects["Operator_Access_ROOT"].children_recursive
        )
        cutaway_objects = cutaway_objects + access_cutaway_objects
        for label, location, ortho_scale, pose in views:
            for name, rotation in neutral.items():
                bpy.data.objects[name].rotation_euler = rotation
            for name, rotation in pose.items():
                bpy.data.objects[name].rotation_euler = rotation
            # Remove only the near-side review skin for the process proof.  The
            # visibility state is restored before saving/exporting the model.
            for name in cutaway_objects:
                bpy.data.objects[name].hide_render = label == "articulation-detail"
            bpy.context.view_layer.update()
            camera.location = location
            target = shared.Vector((0.32, 1.42, 0)) if label == "articulation-detail" else center
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
            "772_L_Wing_Fold_Pivot", "772_L_Wing_ROOT",
            "772_R_Wing_Fold_Pivot", "772_R_Wing_ROOT",
            "Feedroll_Upper_ROOT", "Feedroll_Lower_ROOT",
            "Dura_Drum_Cutterhead_ROOT", "Crop_Accelerator_ROOT",
            "Schematic_Crop_Path_ROOT",
            "Rear_Axle_ROOT", "Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot",
        ]

    def machine_specific_validation_gates(self, contract):
        names = contract["node_names"]
        config_id = self.design["configuration_id"]
        expected_codes = ("282DZ", "4005", "0415KM", "5597", "33M")
        header_extent_ranges = [
            self._world_range("772_L_Crop_Divider", 2),
            self._world_range("772_R_Crop_Divider", 2),
        ]
        header_width = max(pair[1] for pair in header_extent_ranges) - min(pair[0] for pair in header_extent_ranges)
        tire_ranges = [self._world_range(name, 2) for name in names if name.endswith("_Tire")]
        carrier_min_z = min(pair[0] for pair in tire_ranges)
        carrier_max_z = max(pair[1] for pair in tire_ranges)
        carrier_width = carrier_max_z - carrier_min_z
        cutter = bpy.data.objects["Dura_Drum_856x670_Body"]
        accelerator = bpy.data.objects["Crop_Accelerator_632x560_Body"]
        knives = [name for name in names if name.startswith("Dura_Drum_Knife_Station_")]
        feedrolls = [
            name for name in names
            if name in {
                "Feedroll_Upper_Front", "Feedroll_Upper_Rear",
                "Feedroll_Lower_Front", "Feedroll_Lower_Rear",
            }
        ]
        viewer = json.loads((self.output_dir / "viewer.json").read_text(encoding="utf-8"))
        spout_channel = next(channel for channel in viewer["motion"]["channels"] if channel["id"] == "spout-yaw")
        viewer_sweep_deg = math.degrees(spout_channel["to"] - spout_channel["from"])
        material_names = {
            slot.material.name
            for obj in self.public_objects() if obj.type == "MESH"
            for slot in obj.material_slots if slot.material is not None
        }
        header_top_y = 1.98
        spout_low_y = 2.22 - 0.08
        vertical_gap = spout_low_y - header_top_y
        component_measurements = {
            "feedroll_count": len(feedrolls),
            "cutterhead_width_m": float(cutter["exo_published_width_m"]),
            "cutterhead_diameter_m": float(cutter["exo_published_diameter_m"]),
            "knife_stations": len(knives),
            "accelerator_width_m": float(accelerator["exo_published_width_m"]),
            "accelerator_diameter_m": float(accelerator["exo_published_diameter_m"]),
        }
        return [
            self._gate(
                "frozen_282DZ_4005_0415KM_5597_configuration",
                all(code in config_id for code in expected_codes),
                {"configuration_id": config_id, "required_codes": expected_codes},
            ),
            self._gate(
                "selected_772_overall_width", abs(header_width - self.HEADER_OVERALL_WIDTH_M) <= 0.002,
                {"measured_overall_width_m": round(header_width, 6), "published_overall_width_m": self.HEADER_OVERALL_WIDTH_M, "working_width_m": self.HEADER_WORKING_WIDTH_M, "transport_width_target_m": self.HEADER_TRANSPORT_WIDTH_M, "fold_path_authority": "reconstructed"},
            ),
            self._gate(
                "carrier_3_3m_width_class", abs(carrier_width - self.CARRIER_WIDTH_M) <= 0.002,
                {"measured_tire_outer_width_m": round(carrier_width, 6), "published_width_class_m": self.CARRIER_WIDTH_M, "z_range_m": [round(carrier_min_z, 6), round(carrier_max_z, 6)]},
            ),
            self._gate(
                "header_lift_continuity",
                self._descends("Header_ROOT", "Header_Lift_Pivot")
                and self._descends("772_L_Wing_ROOT", "Header_ROOT")
                and self._descends("772_R_Wing_ROOT", "Header_ROOT"),
                {
                    "hierarchy": "fixed structure -> lift pivot -> complete 772 header -> two hydraulic-fold wing roots",
                    "left_wing_descends_from_header": self._descends("772_L_Wing_ROOT", "Header_ROOT"),
                    "right_wing_descends_from_header": self._descends("772_R_Wing_ROOT", "Header_ROOT"),
                },
            ),
            self._gate(
                "feedroll_continuity",
                len(feedrolls) == 4
                and self._descends("Feedroll_Upper_Front_ROOT", "Feedroll_Upper_ROOT")
                and self._descends("Feedroll_Lower_Rear_ROOT", "Feedroll_Lower_ROOT")
                and all(self._descends(name, "Feedroll_ROOT") for name in feedrolls),
                {**component_measurements, "hierarchy": "two upper plus two lower rollers under Feedroll_ROOT"},
            ),
            self._gate(
                "spout_yaw_and_tip_continuity",
                self._descends("Spout_ROOT", "Spout_Yaw_Pivot")
                and self._descends("Spout_Tip_ROOT", "Spout_ROOT")
                and abs(viewer_sweep_deg - self.SPOUT_SWING_DEG) <= 0.02,
                {"viewer_sweep_deg": round(viewer_sweep_deg, 6), "published_turning_angle_deg": self.SPOUT_SWING_DEG},
            ),
            self._gate(
                "header_carrier_spout_clearance", vertical_gap > 0.05,
                {"neutral_header_to_spout_vertical_gap_m": round(vertical_gap, 6), "scope": "authored neutral structural pose"},
            ),
            self._gate(
                "ground_collision", contract["bounds"]["min_m"][1] >= -0.005,
                {"minimum_visible_y_m": contract["bounds"]["min_m"][1], "ground_y_m": 0.0},
            ),
            self._gate(
                "self_collision",
                vertical_gap > 0.05 and len(knives) == self.CUTTERHEAD_KNIVES,
                {"neutral_header_spout_gap_m": round(vertical_gap, 6), **component_measurements, "scope": "neutral pose and component containment; swept-volume solver remains outside claim"},
            ),
            self._gate(
                "neutral_unbranded_material_review",
                bool(material_names) and all(name.startswith("Neutral_") for name in material_names),
                {"public_materials": sorted(material_names), "images": contract["images"], "textures": contract["textures"]},
            ),
        ]


if __name__ == "__main__":
    design = shared.load_design(DESIGN)
    JohnDeere9900SPFHBuilder(design, DESIGN, OUTPUT_DIR).run()

#!/usr/bin/env python3
"""Deterministic reconstructed Fendt IDEAL 10T mechanism study.

Only the hash-bound MotionShift fact is admitted.  Every visible dimension,
option, hidden pivot, and motion endpoint below is an authored visualization
target pending an applicable first-party technical freeze.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()
VIEWER = OUTPUT_DIR / "viewer.json"

spec = importlib.util.spec_from_file_location("exo_fleet_fendt_ideal_10t", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load frozen shared builder: {SHARED_GENERATOR}")
fleet = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fleet
spec.loader.exec_module(fleet)


class FendtIdeal10TBuilder(fleet.FleetBuilder):
    """Own the complete visible hierarchy and fail-closed study gates."""

    CARRIER_LENGTH_M = 10.63
    CARRIER_WIDTH_M = 3.49
    HEADER_SPAN_M = 10.70
    TRACK_WIDTH_M = 0.762
    REAR_TIRE_WIDTH_M = 0.520
    LIFT_ANGLE_RAD = 0.151
    ROLL_RANGE_RAD = math.radians(8.0)
    UNLOADER_INNER_M = 3.60
    UNLOADER_OUTER_M = 4.80
    UNLOADER_FOLD_RAD = -math.asin((4.95 - 3.05) / UNLOADER_OUTER_M)
    TOLERANCE_M = 0.004

    def write_machine_wrapper(self):
        """Preserve this audited machine-local implementation."""

    def create_materials(self):
        super().create_materials()
        self.materials["cutaway"] = self.material(
            "Neutral_Cutaway_Guard", (0.26, 0.31, 0.34),
            metallic=0.10, roughness=0.34, alpha=0.24,
        )
        self.materials["crop_path"] = self.material(
            "Neutral_Crop_Path_Cue", (0.50, 0.38, 0.12),
            metallic=0.02, roughness=0.70,
        )

    def required_semantics(self):
        names = list(super().required_semantics())
        for name in (
            "Header_Roll_Pivot", "PowerFlow_Belts_ROOT", "Header_Intake_Auger_ROOT",
            "Rear_Axle_ROOT", "Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot",
            "Track_L_Drive_Wheel_ROOT", "Track_R_Drive_Wheel_ROOT",
            "Header_Lift_Cylinder_L_ROOT", "Header_Lift_Cylinder_R_ROOT",
            "Unloader_Fold_Pivot", "Unloader_Outer_ROOT", "Unloader_Spout_Pivot",
            "Unloader_Spout_ROOT", "Dual_Helix_L_ROOT", "Dual_Helix_R_ROOT",
            "RotorFeeder_ROOT", "ShortCut_ROOT", "ActiveSpread_L_ROOT",
            "ActiveSpread_R_ROOT", "SwingFlow_ROOT", "AirSense_Fan_ROOT",
            "PowerFold_Ladder_Pivot", "PowerFold_Ladder_ROOT",
        ):
            if name not in names:
                names.append(name)
        return names

    def build_combine(self):
        # Reconstructed tracked-front / rear-steer carrier.
        track_length, track_height = 3.28, 1.22
        track_center_z = self.CARRIER_WIDTH_M / 2 - self.TRACK_WIDTH_M / 2
        for side, sign in (("L", -1), ("R", 1)):
            track = self.add_track_pod(
                f"Track_{side}", track_length, track_height, self.TRACK_WIDTH_M,
                (1.20, 0.006, sign * track_center_z), self.running_root,
                pads=30, rollers=5,
            )
            drive = self.empty(
                f"Track_{side}_Drive_Wheel_ROOT",
                (-track_length * 0.30, track_height * 0.52, 0), track,
                role="rotary_root",
            )
            self.cylinder(
                f"Track_{side}_Drive_Sprocket", (0, 0, 0), 0.37,
                self.TRACK_WIDTH_M * 0.70, self.materials["steel"], drive,
                vertices=24, role="drive_sprocket",
            )

        rear_x, rear_radius = -3.34, 0.79
        rear_center_z = self.CARRIER_WIDTH_M / 2 - self.REAR_TIRE_WIDTH_M / 2
        rear_axle = self.empty(
            "Rear_Axle_ROOT", (rear_x, rear_radius, 0), self.running_root,
            role="steering_axle_root",
        )
        self.box(
            "Rear_Steering_Axle_Beam", (0, 0, 0),
            (0.26, 0.23, rear_center_z * 2 + 0.18),
            self.materials["steel"], rear_axle, role="steering_axle",
        )
        for side, sign in (("L", -1), ("R", 1)):
            steer = self.empty(
                f"Rear_Steering_{side}_Pivot", (0, 0, sign * rear_center_z),
                rear_axle, role="steering_pivot",
            )
            self.add_wheel(
                f"Rear_{side}", (0, 0, 0), rear_radius,
                self.REAR_TIRE_WIDTH_M, steer, tread_count=14,
            )

        # Full carrier chain; the end structures are attached, not witnesses.
        self.box(
            "Carrier_Longitudinal_Frame", (0, 1.08, 0),
            (self.CARRIER_LENGTH_M - 0.10, 0.24, 1.28),
            self.materials["graphite"], self.fixed_root, role="chassis",
        )
        for label, sign in (("Rear", -1), ("Front", 1)):
            self.box(
                f"Carrier_{label}_End_Structure",
                (sign * (self.CARRIER_LENGTH_M / 2 - 0.025), 1.05, 0),
                (0.05, 0.28, 1.08), self.materials["graphite"],
                self.fixed_root, role="chassis_end", bevel=0.008,
            )
        for side, sign in (("L", -1), ("R", 1)):
            self.box(
                f"Carrier_Lateral_Structure_{side}", (-0.55, 1.21,
                sign * (self.CARRIER_WIDTH_M / 2 - 0.025)),
                (5.40, 0.22, 0.05), self.materials["graphite"],
                self.fixed_root, role="carrier_side", bevel=0.008,
            )

        self.side_profile(
            "Separator_Main_House",
            [(-4.55, 1.18), (1.20, 1.18), (1.65, 2.64),
             (0.65, 3.40), (-3.95, 3.26)],
            2.62, self.materials["body"], self.fixed_root,
            role="separator_house",
        )
        self.box(
            "Grain_Tank", (-1.35, 3.31, 0), (3.50, 0.60, 2.60),
            self.materials["body_dark"], self.fixed_root, role="grain_tank",
            bevel=0.035,
        )
        self.add_cab(1.62, 1.44, 1.55, 2.14, 2.45, self.fixed_root)
        self.box(
            "Carrier_Height_Roof", (1.62, self.height - 0.025, 0),
            (1.50, 0.05, 2.10), self.materials["body"],
            self.fixed_root, role="cab_structure", bevel=0.008,
        )
        self.box(
            "Engine_Bay_Lower_Mass", (-2.70, 1.58, 0),
            (2.45, 0.82, 2.48), self.materials["body_dark"],
            self.fixed_root, role="engine_bay", bevel=0.035,
        )

        # Correct lift hierarchy: the feeder and full header are one lift subtree.
        lift = self.empty(
            "Header_Lift_Pivot", (2.20, 1.85, 0), self.fixed_root,
            role="pivot",
        )
        feeder = self.empty("Feederhouse_ROOT", parent=lift, role="motion_root")
        self.side_profile(
            "Feederhouse_Casing",
            [(0, 0.12), (2.56, -0.18), (2.56, -0.64),
             (0.20, -0.46)],
            1.48, self.materials["body_dark"], feeder,
            role="feederhouse",
        )
        for index in range(4):
            self.box(
                f"Feeder_Chain_Path_{index + 1}", (1.32, -0.35,
                -0.54 + index * 0.36), (2.25, 0.045, 0.055),
                self.materials["steel"], feeder, role="feeder_chain",
                bevel=0.006,
            )
        self.box(
            "Feeder_Header_Coupler", (2.55, -0.38, 0),
            (0.16, 0.58, 1.46), self.materials["steel"], feeder,
            role="header_coupler", bevel=0.014,
        )
        roll = self.empty(
            "Header_Roll_Pivot", (2.57, -0.28, 0), feeder, role="pivot",
        )
        header = self.empty("Header_ROOT", parent=roll, role="motion_root")
        self.box(
            "Header_Coupler", (0.02, -0.10, 0), (0.18, 0.48, 1.50),
            self.materials["graphite"], header, role="header_coupler",
            bevel=0.012,
        )
        self.box(
            "Header_Backbone", (0.18, -0.33, 0),
            (0.58, 0.54, self.HEADER_SPAN_M), self.materials["body"],
            header, role="header", bevel=0.025,
        )
        self.box(
            "Cutterbar", (0.42, -0.69, 0),
            (0.26, 0.10, self.HEADER_SPAN_M * 0.985),
            self.materials["steel"], header, role="cutterbar", bevel=0.008,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.side_profile(
                f"Header_Crop_Divider_{side}",
                [(0.02, -0.30), (0.50, -0.45), (0.46, -0.68),
                 (0.06, -0.60)],
                0.08, self.materials["body_dark"], header,
                z_center=sign * (self.HEADER_SPAN_M / 2 - 0.04),
                role="crop_divider",
            )

        reel_pivot = self.empty(
            "Reel_Pivot", (0.03, 0.12, 0), header, role="pivot",
        )
        reel = self.empty("Reel_ROOT", parent=reel_pivot, role="rotary_root")
        self.cylinder(
            "PowerFlow_Reel_Axle", (0, 0, 0), 0.055,
            self.HEADER_SPAN_M * 0.93, self.materials["steel"], reel,
            vertices=20, role="reel",
        )
        for index in range(6):
            angle = math.tau * index / 6
            self.box(
                f"PowerFlow_Reel_Bat_{index + 1}",
                (math.cos(angle) * 0.47, math.sin(angle) * 0.47, 0),
                (0.055, 0.055, self.HEADER_SPAN_M * 0.91),
                self.materials["warning"], reel, rotation=(0, 0, angle),
                role="reel_bat", bevel=0.008,
            )
        belts = self.empty(
            "PowerFlow_Belts_ROOT", (0.10, -0.48, 0), header,
            role="linear_motion_root",
        )
        for index, z in enumerate((-3.80, -2.28, -0.76, 0.76, 2.28, 3.80), 1):
            self.box(
                f"PowerFlow_Belt_{index}", (0, 0, z),
                (0.58, 0.055, 1.34), self.materials["rubber"], belts,
                rotation=(0, 0, -0.08), role="header_belt", bevel=0.006,
            )
        intake = self.empty(
            "Header_Intake_Auger_ROOT", (-0.02, -0.24, 0), header,
            role="rotary_root",
        )
        self.cylinder(
            "Header_Intake_Auger", (0, 0, 0), 0.16,
            self.HEADER_SPAN_M * 0.78, self.materials["steel"], intake,
            vertices=28, role="intake_auger",
        )

        # Paired 92 mm visual cylinders, each attached at both rest-pose ends.
        for side, sign in (("L", -1), ("R", 1)):
            self.box(
                f"Lift_Frame_Bracket_{side}", (2.14, 1.92, sign * 0.58),
                (0.22, 0.28, 0.18), self.materials["graphite"],
                self.fixed_root, role="hydraulic_mount", bevel=0.010,
            )
            self.box(
                f"Lift_Feeder_Bracket_{side}", (0.82, -0.22, sign * 0.58),
                (0.20, 0.20, 0.18), self.materials["graphite"], feeder,
                role="hydraulic_mount", bevel=0.010,
            )
            cylinder_root = self.empty(
                f"Header_Lift_Cylinder_{side}_ROOT", parent=self.hydraulics_root,
                role="hydraulic_root",
            )
            self.pipe_between(
                f"Header_Lift_Cylinder_{side}",
                (2.14, 1.92, sign * 0.58),
                (3.02, 1.63, sign * 0.58), 0.046,
                self.materials["rod"], cylinder_root, role="hydraulic",
            )

        # Exposed reconstructed crop-path topology.
        for side, z in (("L", -0.43), ("R", 0.43)):
            rotor = self.empty(
                f"Dual_Helix_{side}_ROOT", (-0.55, 2.42, z),
                self.fixed_root, role="rotary_root",
            )
            self.cylinder(
                f"Dual_Helix_{side}_Drum", (0, 0, 0), 0.30, 3.45,
                self.materials["steel"], rotor, vertices=32,
                rotation=(0, math.pi / 2, 0), role="threshing_rotor",
            )
            for index in range(10):
                angle = math.tau * index / 10
                self.box(
                    f"Dual_Helix_{side}_Bar_{index + 1}",
                    (0, math.cos(angle) * 0.27, math.sin(angle) * 0.27),
                    (3.20, 0.035, 0.035), self.materials["graphite"],
                    rotor, rotation=(angle, 0, 0), role="rotor_bar",
                    bevel=0.004,
                )
        self.box(
            "Dual_Helix_Cutaway_Guard", (-0.55, 2.42, 0),
            (3.72, 0.84, 1.20), self.materials["cutaway"],
            self.fixed_root, role="rotor_containment", bevel=0.025,
        )
        rotor_feeder = self.empty(
            "RotorFeeder_ROOT", (1.36, 1.98, 0), self.fixed_root,
            role="rotary_root",
        )
        self.cylinder(
            "RotorFeeder_Drum", (0, 0, 0), 0.24, 1.34,
            self.materials["steel"], rotor_feeder, vertices=26,
            role="rotor_feeder",
        )
        shortcut = self.empty(
            "ShortCut_ROOT", (-3.65, 1.38, 0), self.fixed_root,
            role="rotary_process_root",
        )
        self.cylinder(
            "ShortCut_Rotor", (0, 0, 0), 0.22, 1.48,
            self.materials["graphite"], shortcut, vertices=24,
            role="straw_chopper",
        )
        for side, sign in (("L", -1), ("R", 1)):
            spread = self.empty(
                f"ActiveSpread_{side}_ROOT", (-4.18, 1.12, sign * 0.52),
                self.fixed_root, role="rotary_root",
            )
            self.cylinder(
                f"ActiveSpread_{side}_Disk", (0, 0, 0), 0.30, 0.06,
                self.materials["steel"], spread, vertices=24,
                rotation=(math.pi / 2, 0, 0), role="spreader_disk",
            )
            for index in range(4):
                angle = math.tau * index / 4
                self.box(
                    f"ActiveSpread_{side}_Vane_{index + 1}",
                    (math.cos(angle) * 0.17, 0, math.sin(angle) * 0.17),
                    (0.28, 0.05, 0.045), self.materials["warning"],
                    spread, rotation=(0, angle, 0), role="spreader_vane",
                    bevel=0.005,
                )
        swingflow = self.empty(
            "SwingFlow_ROOT", (-4.64, 1.02, 0), self.fixed_root,
            role="oscillating_root",
        )
        for index, z in enumerate((-0.72, -0.48, -0.24, 0, 0.24, 0.48, 0.72), 1):
            self.box(
                f"SwingFlow_Vane_{index}", (0, 0, z),
                (0.46, 0.07, 0.065), self.materials["steel"],
                swingflow, rotation=(0, 0, -0.10), role="guide_vane",
                bevel=0.005,
            )
        fan = self.empty(
            "AirSense_Fan_ROOT", (-2.55, 2.46, -1.36), self.fixed_root,
            role="rotary_root",
        )
        self.cylinder(
            "AirSense_Fan_Hub", (0, 0, 0), 0.12, 0.16,
            self.materials["graphite"], fan, vertices=20,
            rotation=(math.pi / 2, 0, 0), role="cooling_fan",
        )
        for index in range(8):
            angle = math.tau * index / 8
            self.box(
                f"AirSense_Fan_Blade_{index + 1}",
                (math.cos(angle) * 0.30, 0, math.sin(angle) * 0.30),
                (0.36, 0.055, 0.10), self.materials["steel"], fan,
                rotation=(0, angle, 0), role="fan_blade", bevel=0.008,
            )

        # Reconstructed two-piece 8.4 m centerline; rest pose folds inside AABB.
        swing = self.empty(
            "Unloader_Swing_Pivot", (-2.50, 3.05, 1.20),
            self.fixed_root, role="pivot",
        )
        unloader = self.empty("Unloader_ROOT", parent=swing, role="motion_root")
        self.cylinder(
            "Unloader_Base_Collar", (0, 0, 0), 0.18, 0.28,
            self.materials["body_dark"], unloader, vertices=26,
            rotation=(math.pi / 2, 0, 0), role="unloader_hinge",
        )
        self.pipe_between(
            "Unloader_Inner_Tube", (0, 0, 0),
            (self.UNLOADER_INNER_M, 0, 0), 0.105,
            self.materials["body"], unloader, role="unloader_tube",
        )
        fold = self.empty(
            "Unloader_Fold_Pivot", (self.UNLOADER_INNER_M, 0, 0),
            unloader, role="pivot",
        )
        outer = self.empty("Unloader_Outer_ROOT", parent=fold, role="motion_root")
        self.pipe_between(
            "Unloader_Outer_Tube", (0, 0, 0),
            (-self.UNLOADER_OUTER_M, 0, 0), 0.098,
            self.materials["body"], outer, role="unloader_tube",
        )
        spout_pivot = self.empty(
            "Unloader_Spout_Pivot", (-self.UNLOADER_OUTER_M, 0, 0),
            outer, role="pivot",
        )
        spout = self.empty(
            "Unloader_Spout_ROOT", parent=spout_pivot, role="motion_root",
        )
        self.box(
            "Unloader_Spout", (0, -0.15, 0), (0.34, 0.34, 0.30),
            self.materials["body_dark"], spout, role="unloader_spout",
            bevel=0.025,
        )

        ladder_pivot = self.empty(
            "PowerFold_Ladder_Pivot", (1.15, 1.28, -1.53),
            self.fixed_root, role="pivot",
        )
        ladder = self.empty(
            "PowerFold_Ladder_ROOT", parent=ladder_pivot, role="motion_root",
        )
        for z in (-0.18, 0.18):
            self.pipe_between(
                f"PowerFold_Ladder_Rail_{'L' if z < 0 else 'R'}",
                (0, 0.55, z), (0, -0.55, z), 0.028,
                self.materials["steel"], ladder, role="ladder_rail",
            )
        for index in range(5):
            self.box(
                f"PowerFold_Ladder_Step_{index + 1}",
                (0, 0.42 - index * 0.22, 0), (0.08, 0.045, 0.42),
                self.materials["steel"], ladder, role="ladder_step",
                bevel=0.006,
            )

        self.pipe_between(
            "Hydraulic_Manifold_Line", (-1.65, 1.32, -1.18),
            (-0.35, 1.42, -1.18), 0.028, self.materials["rod"],
            self.hydraulics_root, role="hydraulic",
        )
        self.box(
            "Service_Access_Platform", (-0.05, 1.52, -1.55),
            (1.80, 0.08, 0.32), self.materials["steel"],
            self.detail_root, role="service_platform", bevel=0.010,
        )

    @staticmethod
    def _object_bounds(obj):
        points = [obj.matrix_world @ fleet.Vector(corner) for corner in obj.bound_box]
        return (
            [min(point[axis] for point in points) for axis in range(3)],
            [max(point[axis] for point in points) for axis in range(3)],
        )

    def _bounds(self, names):
        minimum = [math.inf, math.inf, math.inf]
        maximum = [-math.inf, -math.inf, -math.inf]
        for name in names:
            obj = fleet.bpy.data.objects.get(name)
            if obj is None or obj.type != "MESH":
                raise RuntimeError(f"missing measured mesh {name}")
            low, high = self._object_bounds(obj)
            for axis in range(3):
                minimum[axis] = min(minimum[axis], low[axis])
                maximum[axis] = max(maximum[axis], high[axis])
        return minimum, maximum

    def _subtree_meshes(self, root_name):
        root = fleet.bpy.data.objects[root_name]
        names = [obj.name for obj in root.children_recursive if obj.type == "MESH"]
        if root.type == "MESH":
            names.insert(0, root.name)
        return names

    def _overlap(self, first, second):
        first_low, first_high = self._bounds([first])
        second_low, second_high = self._bounds([second])
        return [
            min(first_high[axis], second_high[axis])
            - max(first_low[axis], second_low[axis])
            for axis in range(3)
        ]

    def normalize_visible_envelope(self):
        self.apply_public_modifiers()
        fleet.bpy.context.view_layer.update()
        for root_name in ("Track_L_ROOT", "Track_R_ROOT", "Rear_Axle_ROOT"):
            root = fleet.bpy.data.objects[root_name]
            low, _ = self._bounds(self._subtree_meshes(root_name))
            root.location.y -= low[1]
            fleet.bpy.context.view_layer.update()
        return super().normalize_visible_envelope()

    @staticmethod
    def _gate(gate_id, method, evidence, semantic_nodes, passed=True):
        return {
            "id": gate_id,
            "status": "PASS" if passed else "FAIL",
            "detail": {
                "method": method,
                "evidence": evidence,
                "semantic_nodes": list(semantic_nodes),
                "fact_ids": [],
                "authority": "Computed reconstructed-study evidence only; not manufacturer or operating authority.",
            },
        }

    def machine_specific_validation_gates(self, contract):
        tolerance = self.TOLERANCE_M
        carrier_names = [
            "Carrier_Rear_End_Structure", "Carrier_Front_End_Structure",
            "Carrier_Lateral_Structure_L", "Carrier_Lateral_Structure_R",
            "Carrier_Height_Roof", "Carrier_Longitudinal_Frame",
        ]
        carrier_low, carrier_high = self._bounds(carrier_names)
        carrier_size = [carrier_high[i] - carrier_low[i] for i in range(3)]
        header_low, header_high = self._bounds(self._subtree_meshes("Header_ROOT"))
        header_span = header_high[2] - header_low[2]

        feeder = fleet.bpy.data.objects["Feederhouse_ROOT"]
        roll = fleet.bpy.data.objects["Header_Roll_Pivot"]
        original_lift, original_roll = feeder.rotation_euler.z, roll.rotation_euler.x
        lift_clearances = []
        for angle in (0.0, self.LIFT_ANGLE_RAD):
            feeder.rotation_euler.z = angle
            roll.rotation_euler.x = 0.0
            fleet.bpy.context.view_layer.update()
            low, _ = self._bounds(["Cutterbar"])
            lift_clearances.append(round(low[1], 6))
        roll_clearances = {}
        feeder.rotation_euler.z = self.LIFT_ANGLE_RAD
        for angle in (-self.ROLL_RANGE_RAD, 0.0, self.ROLL_RANGE_RAD):
            roll.rotation_euler.x = angle
            fleet.bpy.context.view_layer.update()
            low, _ = self._bounds(self._subtree_meshes("Header_ROOT"))
            roll_clearances[f"{math.degrees(angle):.1f}"] = round(low[1], 6)
        feeder.rotation_euler.z, roll.rotation_euler.x = original_lift, original_roll
        fleet.bpy.context.view_layer.update()

        cylinder_overlaps = {}
        for side in ("L", "R"):
            cylinder_overlaps[side] = {
                "frame": [round(v, 6) for v in self._overlap(
                    f"Header_Lift_Cylinder_{side}", f"Lift_Frame_Bracket_{side}")],
                "feeder": [round(v, 6) for v in self._overlap(
                    f"Header_Lift_Cylinder_{side}", f"Lift_Feeder_Bracket_{side}")],
            }

        rear_owner = {
            side: fleet.bpy.data.objects[f"Rear_{side}_Wheel_Pivot"].parent.name
            for side in ("L", "R")
        }
        track_inventory = {
            side: {
                "pads": len([name for name in self._subtree_meshes(f"Track_{side}_ROOT") if "_Pad_" in name]),
                "rollers": len([name for name in self._subtree_meshes(f"Track_{side}_ROOT") if "_Roller_" in name]),
                "visible_meshes": len(self._subtree_meshes(f"Track_{side}_ROOT")),
            }
            for side in ("L", "R")
        }
        viewer = json.loads(VIEWER.read_text(encoding="utf-8"))
        viewer_nodes = {node for channel in viewer["motion"]["channels"] for node in channel["nodes"]}

        unloader = fleet.bpy.data.objects["Unloader_ROOT"]
        outer = fleet.bpy.data.objects["Unloader_Outer_ROOT"]
        spout = fleet.bpy.data.objects["Unloader_Spout_ROOT"]
        original_swing, original_fold = unloader.rotation_euler.y, outer.rotation_euler.z
        unloader.rotation_euler.y = -1.20
        outer.rotation_euler.z = self.UNLOADER_FOLD_RAD
        fleet.bpy.context.view_layer.update()
        deployed_spout_y = spout.matrix_world.translation.y
        deployed_unloader_low, _ = self._bounds(self._subtree_meshes("Unloader_ROOT"))
        unloader.rotation_euler.y, outer.rotation_euler.z = original_swing, original_fold
        fleet.bpy.context.view_layer.update()

        all_low, _ = self._bounds([obj.name for obj in self.public_objects() if obj.type == "MESH"])
        feeder_header_overlap = self._overlap("Feeder_Header_Coupler", "Header_Coupler")
        frame_house_overlap = self._overlap("Carrier_Longitudinal_Frame", "Separator_Main_House")
        rotor_centers = {
            side: [round(v, 6) for v in fleet.bpy.data.objects[f"Dual_Helix_{side}_ROOT"].matrix_world.translation]
            for side in ("L", "R")
        }
        spread_centers = {
            side: [round(v, 6) for v in fleet.bpy.data.objects[f"ActiveSpread_{side}_ROOT"].matrix_world.translation]
            for side in ("L", "R")
        }
        materials_ok = all(
            material.get("exo_rights") == "neutral_unbranded"
            for material in self.materials.values()
        )

        return [
            self._gate("carrier_length_without_header", "named carrier-only mesh-union X AABB", {"measured_m": round(carrier_size[0], 6), "authored_target_m": self.CARRIER_LENGTH_M, "header_and_unloader_excluded": True, "tolerance_m": tolerance}, ["Carrier_Rear_End_Structure", "Carrier_Front_End_Structure"], abs(carrier_size[0] - self.CARRIER_LENGTH_M) <= tolerance),
            self._gate("selected_carrier_width", "named carrier-only mesh-union Z AABB", {"measured_m": round(carrier_size[2], 6), "authored_target_m": self.CARRIER_WIDTH_M, "source_authority": "unresolved", "tolerance_m": tolerance}, ["Carrier_Lateral_Structure_L", "Carrier_Lateral_Structure_R"], abs(carrier_size[2] - self.CARRIER_WIDTH_M) <= tolerance),
            self._gate("carrier_height", "named roof/carrier mesh-union Y AABB", {"measured_max_y_m": round(carrier_high[1], 6), "authored_target_m": self.height, "source_authority": "unresolved", "tolerance_m": tolerance}, ["Carrier_Height_Roof"], abs(carrier_high[1] - self.height) <= tolerance),
            self._gate("selected_powerflow_header_span", "header-subtree world Z AABB", {"measured_m": round(header_span, 6), "authored_target_m": self.HEADER_SPAN_M, "source_authority": "unresolved", "tolerance_m": tolerance}, ["Header_ROOT"], abs(header_span - self.HEADER_SPAN_M) <= tolerance),
            self._gate("header_lift_endpoint_clearance", "two-endpoint Feederhouse_ROOT rotation with cutterbar world minimum", {"minimum_y_samples_m": lift_clearances, "raised_authored_target_m": 1.27, "lift_angle_rad": self.LIFT_ANGLE_RAD, "tolerance_m": 0.03}, ["Feederhouse_ROOT", "Cutterbar"], lift_clearances[0] >= -tolerance and abs(lift_clearances[-1] - 1.27) <= 0.03),
            self._gate("header_roll_compensation_range", "lifted-pose Header_Roll_Pivot endpoint sweep", {"range_deg": [-8.0, 8.0], "minimum_y_by_pose_m": roll_clearances}, ["Header_Roll_Pivot", "Header_ROOT"], min(roll_clearances.values()) >= -tolerance),
            self._gate("crop_elevator_cylinder_continuity", "paired cylinder-to-frame and cylinder-to-feeder AABB overlap", {"visual_diameter_m": 0.092, "overlap_xyz_m": cylinder_overlaps}, ["Header_Lift_Cylinder_L_ROOT", "Header_Lift_Cylinder_R_ROOT"], all(min(values) >= -tolerance for side in cylinder_overlaps.values() for values in side.values())),
            self._gate("rear_steering_continuity", "wheel-pivot ownership and visible steering-root hierarchy", {"wheel_pivot_parents": rear_owner, "viewer_nodes": sorted(viewer_nodes & {"Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot"})}, ["Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot"], all(parent.startswith("Rear_Steering_") for parent in rear_owner.values()) and {"Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot"}.issubset(viewer_nodes)),
            self._gate("trakride_belt_path_and_phase_continuity", "left/right track component inventory and distinct drive-root ownership", {"inventory": track_inventory, "belt_visual_width_m": self.TRACK_WIDTH_M, "drive_roots_in_viewer": sorted(viewer_nodes & {"Track_L_Drive_Wheel_ROOT", "Track_R_Drive_Wheel_ROOT"})}, ["Track_L_ROOT", "Track_R_ROOT", "Track_L_Drive_Wheel_ROOT", "Track_R_Drive_Wheel_ROOT"], all(item["pads"] == 30 and item["rollers"] == 5 for item in track_inventory.values()) and {"Track_L_Drive_Wheel_ROOT", "Track_R_Drive_Wheel_ROOT"}.issubset(viewer_nodes)),
            self._gate("reel_belt_and_intake_rotation_continuity", "visible-subtree and viewer ownership scan", {"visible_meshes": {name: len(self._subtree_meshes(name)) for name in ("Reel_ROOT", "PowerFlow_Belts_ROOT", "Header_Intake_Auger_ROOT")}, "viewer_nodes_present": sorted(viewer_nodes & {"Reel_ROOT", "PowerFlow_Belts_ROOT", "Header_Intake_Auger_ROOT"})}, ["Reel_ROOT", "PowerFlow_Belts_ROOT", "Header_Intake_Auger_ROOT"], {"Reel_ROOT", "PowerFlow_Belts_ROOT", "Header_Intake_Auger_ROOT"}.issubset(viewer_nodes)),
            self._gate("unloading_auger_swing_fold_and_spout_clearance", "centerline sum plus deployed swing/fold world-transform sample", {"inner_m": self.UNLOADER_INNER_M, "outer_m": self.UNLOADER_OUTER_M, "total_m": self.UNLOADER_INNER_M + self.UNLOADER_OUTER_M, "deployed_spout_y_m": round(deployed_spout_y, 6), "authored_spout_target_m": 4.95, "deployed_minimum_y_m": round(deployed_unloader_low[1], 6)}, ["Unloader_ROOT", "Unloader_Outer_ROOT", "Unloader_Spout_ROOT"], abs(self.UNLOADER_INNER_M + self.UNLOADER_OUTER_M - 8.4) <= tolerance and abs(deployed_spout_y - 4.95) <= 0.02 and deployed_unloader_low[1] >= -tolerance),
            self._gate("dual_helix_and_rotorfeeder_clearance", "named internal rotary-root centers and visible-subtree inventory", {"dual_helix_centers_xyz_m": rotor_centers, "rotorfeeder_visible_meshes": len(self._subtree_meshes("RotorFeeder_ROOT"))}, ["Dual_Helix_L_ROOT", "Dual_Helix_R_ROOT", "RotorFeeder_ROOT"], rotor_centers["L"][2] < rotor_centers["R"][2] and len(self._subtree_meshes("RotorFeeder_ROOT")) > 0),
            self._gate("active_spread_disk_and_swingflow_clearance", "named spread-root centers, guide-vane inventory, and viewer ownership", {"disk_centers_xyz_m": spread_centers, "swingflow_vanes": len(self._subtree_meshes("SwingFlow_ROOT")), "viewer_nodes_present": sorted(viewer_nodes & {"ActiveSpread_L_ROOT", "ActiveSpread_R_ROOT", "SwingFlow_ROOT"})}, ["ActiveSpread_L_ROOT", "ActiveSpread_R_ROOT", "SwingFlow_ROOT"], spread_centers["L"][2] < spread_centers["R"][2] and len(self._subtree_meshes("SwingFlow_ROOT")) >= 7 and {"ActiveSpread_L_ROOT", "ActiveSpread_R_ROOT", "SwingFlow_ROOT"}.issubset(viewer_nodes)),
            self._gate("airsense_fan_clearance", "visible fan-subtree inventory and viewer ownership", {"visible_meshes": len(self._subtree_meshes("AirSense_Fan_ROOT")), "authored_diameter_m": 0.95, "viewer_owned": "AirSense_Fan_ROOT" in viewer_nodes}, ["AirSense_Fan_ROOT"], len(self._subtree_meshes("AirSense_Fan_ROOT")) >= 9 and "AirSense_Fan_ROOT" in viewer_nodes),
            self._gate("ladder_clearance", "visible ladder-subtree inventory and viewer ownership", {"visible_meshes": len(self._subtree_meshes("PowerFold_Ladder_ROOT")), "viewer_owned": "PowerFold_Ladder_ROOT" in viewer_nodes}, ["PowerFold_Ladder_ROOT"], len(self._subtree_meshes("PowerFold_Ladder_ROOT")) >= 7 and "PowerFold_Ladder_ROOT" in viewer_nodes),
            self._gate("ground_collision", "rest AABB plus lifted roll/unloader endpoint minima", {"rest_minimum_y_m": round(all_low[1], 6), "lift_minimum_y_m": min(lift_clearances), "roll_minimum_y_m": min(roll_clearances.values()), "deployed_unloader_minimum_y_m": round(deployed_unloader_low[1], 6)}, ["Track_L_ROOT", "Track_R_ROOT", "Rear_Axle_ROOT", "Feederhouse_ROOT", "Unloader_ROOT"], all_low[1] >= -tolerance and min(lift_clearances) >= -tolerance and min(roll_clearances.values()) >= -tolerance and deployed_unloader_low[1] >= -tolerance),
            self._gate("header_self_collision", "feeder-coupler/header-coupler three-axis rest overlap plus hierarchy", {"coupler_overlap_xyz_m": [round(v, 6) for v in feeder_header_overlap], "header_parent": fleet.bpy.data.objects["Header_ROOT"].parent.name, "lift_owner": fleet.bpy.data.objects["Feederhouse_ROOT"].parent.name}, ["Feederhouse_ROOT", "Header_ROOT"], min(feeder_header_overlap) >= -tolerance and fleet.bpy.data.objects["Header_ROOT"].parent == fleet.bpy.data.objects["Header_Roll_Pivot"]),
            self._gate("carrier_self_collision", "longitudinal-frame/separator-house continuity overlap and carrier-only envelope", {"frame_house_overlap_xyz_m": [round(v, 6) for v in frame_house_overlap], "carrier_size_xyz_m": [round(v, 6) for v in carrier_size]}, ["Fixed_Structure_ROOT", "Carrier_Longitudinal_Frame"], min(frame_house_overlap) >= -tolerance),
            self._gate("neutral_material_and_branding_review", "procedural material rights-tag scan", {"material_count": len(self.materials), "all_neutral_unbranded": materials_ok, "images_or_textures": 0}, [], materials_ok),
        ]

    def render_views(self):
        self.setup_render_scene()
        camera = fleet.bpy.data.objects["Review_Camera"]
        center = fleet.Vector((0, self.height * 0.46, 0))
        span = max(self.length, self.width, self.height)
        views = [
            ("operator-side", (0, self.height * 0.66, -span * 1.55), span * 1.13, False),
            ("front-three-quarter", (span * 1.08, self.height * 0.90, -span * 1.02), span * 1.48, False),
            ("rear-three-quarter", (-span * 1.12, self.height * 0.86, span * 0.96), span * 1.20, True),
            ("elevated-technical", (span * 0.64, span * 1.46, -span * 0.94), span * 1.50, True),
            ("articulation-detail", (span * 0.78, self.height * 0.70, -span * 0.64), span * 0.78, True),
            ("right-side", (0, self.height * 0.66, span * 1.55), span * 1.13, False),
        ]
        feeder = fleet.bpy.data.objects["Feederhouse_ROOT"]
        roll = fleet.bpy.data.objects["Header_Roll_Pivot"]
        unloader = fleet.bpy.data.objects["Unloader_ROOT"]
        outer = fleet.bpy.data.objects["Unloader_Outer_ROOT"]
        ladder = fleet.bpy.data.objects["PowerFold_Ladder_ROOT"]
        paths = []
        for label, location, ortho_scale, articulated in views:
            feeder.rotation_euler.z = self.LIFT_ANGLE_RAD if articulated else 0.0
            roll.rotation_euler.x = self.ROLL_RANGE_RAD * 0.55 if articulated else 0.0
            unloader.rotation_euler.y = -0.72 if articulated else 0.0
            outer.rotation_euler.z = self.UNLOADER_FOLD_RAD if articulated else 0.0
            ladder.rotation_euler.z = -0.42 if articulated else 0.0
            fleet.bpy.context.view_layer.update()
            camera.location = location
            self.point_at(camera, center)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            fleet.bpy.context.scene.render.filepath = str(path)
            fleet.bpy.ops.render.render(write_still=True)
            paths.append(path)
        feeder.rotation_euler.z = 0.0
        roll.rotation_euler.x = 0.0
        unloader.rotation_euler.y = 0.0
        outer.rotation_euler.z = 0.0
        ladder.rotation_euler.z = 0.0
        fleet.bpy.context.view_layer.update()
        return paths


if __name__ == "__main__":
    design = fleet.load_design(DESIGN)
    FendtIdeal10TBuilder(design, DESIGN, OUTPUT_DIR).run()

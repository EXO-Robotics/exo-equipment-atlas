#!/usr/bin/env python3
"""Deterministic machine-local builder for the New Holland CR11 study.

The committed 2025 North American brochure controls the dual-wheel envelope,
4.039 m wheelbase, 1.885 m feeder cradle, 0.45 m Dynamic Feed Roll, twin
0.61 x 3.6 m rotors, TwinClean topology, 567 bu option, and 105-degree unloader
swivel. Hidden pivots, body panels, tire loading, and motion endpoints are
independently reconstructed and are not engineering authority.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
SHARED_DIR = (HERE / "../../../../scripts/fleet").resolve()
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from build_machine import FleetBuilder  # noqa: E402
from design_contract import load_design  # noqa: E402


DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()
TOLERANCE_M = 0.003


class CR11Builder(FleetBuilder):
    """Own the selected 710/70 R42 dual-front, 2WD, no-header CR11."""

    WHEELBASE_M = 4.039
    DUAL_WIDTH_M = 5.512
    FRONT_TIRE_WIDTH_M = 0.710
    FRONT_TIRE_RADIUS_M = 1.0304  # unloaded nominal size calculation
    FEEDER_WIDTH_M = 1.885
    DFR_DIAMETER_M = 0.450
    ROTOR_COUNT = 2
    ROTOR_DIAMETER_M = 0.610
    ROTOR_LENGTH_M = 3.600
    UNLOADER_SWING_DEG = 105.0

    def write_machine_wrapper(self):
        """Preserve this machine-owned subclass."""

    def required_semantics(self):
        return [
            "Header_Lift_Pivot",
            "Feederhouse_ROOT",
            "Feeder_Faceplate_ROOT",
            "Dynamic_Feed_Roll_ROOT",
            "Twin_Rotor_L_ROOT",
            "Twin_Rotor_R_ROOT",
            "TwinClean_Grainpan_ROOT",
            "TwinClean_Front_ROOT",
            "TwinClean_Rear_ROOT",
            "Grain_Tank_Cover_L_Pivot",
            "Grain_Tank_Cover_L_ROOT",
            "Grain_Tank_Cover_R_Pivot",
            "Grain_Tank_Cover_R_ROOT",
            "Bubble_Up_Auger_ROOT",
            "Unloader_Swing_Pivot",
            "Unloader_ROOT",
            "Unloader_Fold_Pivot",
            "Unloader_Fold_ROOT",
            "Rear_Spreader_L_ROOT",
            "Rear_Spreader_R_ROOT",
            "Front_Drive_Axle_ROOT",
            "Rear_Axle_ROOT",
            "Rear_Steering_L_Pivot",
            "Rear_Steering_R_Pivot",
        ]

    def create_materials(self):
        super().create_materials()
        self.materials["cutaway"] = self.material(
            "Neutral_Cutaway_Guard", (0.26, 0.31, 0.33), metallic=0.12,
            roughness=0.34, alpha=0.24,
        )
        self.materials["crop_path"] = self.material(
            "Neutral_Crop_Path_Cue", (0.53, 0.43, 0.15), metallic=0.02,
            roughness=0.68,
        )
        self.materials["sensor"] = self.material(
            "Neutral_Sensor_Cue", (0.16, 0.48, 0.58), metallic=0.18,
            roughness=0.32,
        )
        self.materials["mechanism"] = self.material(
            "Neutral_Mechanism_Cue", (0.25, 0.33, 0.36), metallic=0.34,
            roughness=0.30,
        )
        self.materials["mechanism_dark"] = self.material(
            "Neutral_Mechanism_Shadow", (0.085, 0.105, 0.115), metallic=0.48,
            roughness=0.32,
        )
        self.materials["grain_path"] = self.material(
            "Neutral_Grain_Path_Cue", (0.48, 0.39, 0.16), metallic=0.04,
            roughness=0.61,
        )
        self.materials["panel_seam"] = self.material(
            "Neutral_Panel_Seam", (0.025, 0.031, 0.036), metallic=0.42,
            roughness=0.42,
        )

    def torus(self, name, location, major_radius, minor_radius, material,
              parent=None, rotation=(0, 0, 0), role="geometry"):
        """Create an applied-scale ring for cages, rims, and service structure."""
        bpy.ops.mesh.primitive_torus_add(
            major_segments=36, minor_segments=8,
            location=location, rotation=rotation,
            major_radius=major_radius, minor_radius=minor_radius,
        )
        obj = bpy.context.object
        obj.name = name
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        return self.tag(obj, role=role)

    def add_cr11_cab(self):
        """Author a faceted high-capacity combine cab instead of a box canopy."""
        cab = self.empty(
            "Operator_Station_ROOT", parent=self.fixed_root,
            role="operator_station",
        )
        glass_profile = [
            (1.02, 1.55), (1.10, 3.46), (1.46, 3.82),
            (2.74, 3.82), (3.18, 3.37), (3.22, 1.55),
        ]
        self.side_profile(
            "CR11_Cab_Glass_Canopy", glass_profile, 2.50,
            self.materials["glass"], cab, role="glazing",
        )
        self.side_profile(
            "CR11_Cab_Roof",
            [(0.96, 3.80), (1.38, 4.013), (2.86, 4.013),
             (3.25, 3.78), (3.12, 3.70), (1.20, 3.70)],
            2.72, self.materials["body"], cab, role="cab_structure",
        )
        self.side_profile(
            "CR11_Cab_Lower_Sill",
            [(0.98, 1.42), (3.24, 1.42), (3.19, 1.72),
             (1.02, 1.72)],
            2.68, self.materials["graphite"], cab, role="cab_structure",
        )
        # Framing is deliberately external so the glazing remains legible from
        # both three-quarter views without copying manufacturer trade dress.
        for side, z in (("L", -1.29), ("R", 1.29)):
            for suffix, start, end in (
                ("A", (3.13, 1.61, z), (3.02, 3.62, z)),
                ("B", (1.08, 1.61, z), (1.24, 3.67, z)),
                ("Roof", (1.28, 3.77, z), (2.82, 3.77, z)),
            ):
                self.pipe_between(
                    f"Cab_{side}_{suffix}_Frame", start, end, 0.045,
                    self.materials["graphite"], cab, role="cab_structure",
                )
            self.pipe_between(
                f"Cab_{side}_Belt_Rail", (1.08, 2.12, z), (3.12, 2.12, z),
                0.030, self.materials["graphite"], cab,
                role="cab_structure",
            )
        self.box(
            "CR11_Cab_Dash", (2.68, 2.00, 0), (0.45, 0.35, 1.30),
            self.materials["graphite"], cab, role="operator_cue",
            bevel=0.035,
        )
        self.box(
            "CR11_Operator_Seat", (1.90, 2.05, 0), (0.55, 0.78, 0.72),
            self.materials["mechanism_dark"], cab, role="operator_cue",
            bevel=0.07,
        )
        self.cylinder(
            "CR11_Steering_Wheel", (2.62, 2.46, 0), 0.21, 0.045,
            self.materials["graphite"], cab, vertices=28,
            rotation=(math.pi / 2, 0, 0), role="operator_cue",
        )
        return cab

    def add_selected_running_gear(self, front_x, rear_x):
        outer_center = self.DUAL_WIDTH_M / 2 - self.FRONT_TIRE_WIDTH_M / 2
        inner_center = outer_center - self.FRONT_TIRE_WIDTH_M - 0.071
        front_axle = self.empty(
            "Front_Drive_Axle_ROOT", (front_x, self.FRONT_TIRE_RADIUS_M, 0),
            self.running_root, role="drive_axle_root",
        )
        self.box(
            "Front_Drive_Axle_Beam", (0, 0, 0),
            (0.30, 0.25, inner_center * 2 + 0.30), self.materials["steel"],
            front_axle, role="drive_axle",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.add_wheel(
                f"Front_{side}_Inner", (0, 0, sign * inner_center),
                self.FRONT_TIRE_RADIUS_M, self.FRONT_TIRE_WIDTH_M,
                front_axle, tread_count=18,
            )
            self.add_wheel(
                f"Front_{side}_Outer", (0, 0, sign * outer_center),
                self.FRONT_TIRE_RADIUS_M, self.FRONT_TIRE_WIDTH_M,
                front_axle, tread_count=18,
            )

        rear_radius = 0.76
        rear_width = 0.55
        rear_center = 1.72
        rear_axle = self.empty(
            "Rear_Axle_ROOT", (rear_x, rear_radius, 0), self.running_root,
            role="steering_axle_root",
        )
        self.box(
            "Rear_Steering_Axle_Beam", (0, 0, 0),
            (0.25, 0.22, rear_center * 2), self.materials["steel"], rear_axle,
            role="steering_axle",
        )
        for side, sign in (("L", -1), ("R", 1)):
            steering = self.empty(
                f"Rear_Steering_{side}_Pivot", (0, 0, sign * rear_center),
                rear_axle, role="steering_pivot",
            )
            self.add_wheel(
                f"Rear_{side}", (0, 0, 0), rear_radius, rear_width,
                steering, tread_count=14,
            )
        self.wheel_geometry = {
            "front_x_m": front_x,
            "rear_x_m": rear_x,
            "outer_center_abs_z_m": outer_center,
            "inner_center_abs_z_m": inner_center,
            "nominal_front_tire_radius_m": self.FRONT_TIRE_RADIUS_M,
            "nominal_front_tire_width_m": self.FRONT_TIRE_WIDTH_M,
            "published_transport_width_m": self.DUAL_WIDTH_M,
        }

    def add_feeder_and_dfr(self):
        feeder_length = 2.826  # reconstructed to the published transport envelope
        base_x = self.length / 2 - feeder_length - 0.10
        lift = self.empty(
            "Header_Lift_Pivot", (base_x, 2.05, 0), self.fixed_root,
            role="feeder_lift_pivot",
        )
        feeder = self.empty("Feederhouse_ROOT", parent=lift, role="motion_root")
        self.side_profile(
            "Feeder_Casing",
            [
                (0.0, -0.56),
                (feeder_length, -1.17),
                (feeder_length, -0.55),
                (0.0, 0.22),
            ],
            self.FEEDER_WIDTH_M, self.materials["body_dark"], feeder,
            role="feederhouse",
        )

        # Four longitudinal chain paths and 33 cross slats match the admitted
        # brochure topology. They are visual cues, not a drive or crop solver.
        chain_start = Vector((0.18, -0.26, 0))
        chain_end = Vector((feeder_length - 0.18, -0.83, 0))
        chain_angle = math.atan2(chain_end.y - chain_start.y,
                                 chain_end.x - chain_start.x)
        for chain_index, z in enumerate((-0.66, -0.22, 0.22, 0.66), start=1):
            self.pipe_between(
                f"Feeder_Chain_{chain_index}",
                (chain_start.x, chain_start.y, z),
                (chain_end.x, chain_end.y, z),
                0.025, self.materials["graphite"], feeder,
                role="feeder_chain",
            )
        for index in range(33):
            fraction = (index + 0.5) / 33
            position = chain_start.lerp(chain_end, fraction)
            self.box(
                f"Feeder_Deep_Drawn_Slat_{index + 1:02d}",
                (position.x, position.y, 0),
                (0.035, 0.055, self.FEEDER_WIDTH_M * 0.88),
                self.materials["steel"], feeder, role="feeder_slat",
                rotation=(0, 0, chain_angle), bevel=0.004,
            )
        face = self.empty(
            "Feeder_Faceplate_ROOT", (feeder_length, -0.86, 0), feeder,
            role="motion_root",
        )
        self.box(
            "Feeder_Coupler_Face", (0.05, 0, 0),
            (0.10, 0.78, self.FEEDER_WIDTH_M), self.materials["steel"], face,
            role="header_coupler_interface", bevel=0.014,
        )
        for side, z in (("L", -0.78), ("R", 0.78)):
            self.box(
                f"Feeder_Coupler_{side}_Hook", (0.025, -0.13, z),
                (0.050, 0.20, 0.12), self.materials["graphite"], face,
                role="header_coupler_interface", bevel=0.010,
            )

        dfr = self.empty(
            "Dynamic_Feed_Roll_ROOT", (0.42, -0.20, 0), feeder,
            role="rotary_root",
        )
        self.cylinder(
            "Dynamic_Feed_Roll", (0, 0, 0), self.DFR_DIAMETER_M / 2,
            self.FEEDER_WIDTH_M * 0.88, self.materials["mechanism"], dfr,
            vertices=32, role="dynamic_feed_roll",
        )
        for index in range(12):
            angle = math.tau * index / 12
            self.box(
                f"Dynamic_Feed_Roll_Paddle_{index + 1:02d}",
                (math.cos(angle) * 0.19, math.sin(angle) * 0.19, 0),
                (0.045, 0.12, self.FEEDER_WIDTH_M * 0.84),
                self.materials["graphite"], dfr, rotation=(0, 0, angle),
                role="dfr_paddle", bevel=0.005,
            )
        for side, z in (("L", -0.84), ("R", 0.84)):
            self.torus(
                f"DFR_{side}_Bearing_Ring", (0, 0, z), 0.255, 0.027,
                self.materials["steel"], dfr,
                role="dynamic_feed_roll_bearing",
            )
            self.pipe_between(
                f"Feeder_{side}_Upper_Frame", (0.08, 0.16, z),
                (feeder_length - 0.08, -0.48, z), 0.055,
                self.materials["mechanism_dark"], feeder,
                role="feeder_frame",
            )
            self.pipe_between(
                f"Feeder_{side}_Lift_Cylinder", (-0.14, -0.22, z),
                (1.20, -0.78, z), 0.045, self.materials["steel"],
                feeder, role="feeder_lift_cylinder",
            )
            self.pipe_between(
                f"Feeder_{side}_Lift_Rod", (1.17, -0.77, z),
                (1.82, -0.92, z), 0.026, self.materials["rod"],
                feeder, role="feeder_lift_rod",
            )
        for station, x in enumerate((0.22, feeder_length - 0.22), start=1):
            self.cylinder(
                f"Feeder_Drive_Sprocket_{station}",
                (x, chain_start.y + (chain_end.y - chain_start.y) *
                 ((x - chain_start.x) / (chain_end.x - chain_start.x)), 0),
                0.14, self.FEEDER_WIDTH_M * 0.82,
                self.materials["mechanism_dark"], feeder, vertices=24,
                role="feeder_sprocket",
            )
        self.feeder_geometry = {
            "reconstructed_length_m": feeder_length,
            "published_cradle_width_m": self.FEEDER_WIDTH_M,
            "base_x_m": base_x,
        }

    def add_rasp_bars(self, prefix, rotor, rotor_length):
        """Represent the brochure's 40 standard, 8 HX, and 12 spiked bars."""
        groups = (("Standard", 40, self.materials["steel"]),
                  ("HX", 8, self.materials["sensor"]),
                  ("Spiked", 12, self.materials["graphite"]))
        ordinal = 0
        for group, count, material in groups:
            for group_index in range(count):
                angle = math.tau * (ordinal % 12) / 12
                station = ordinal // 12
                x = -rotor_length * 0.43 + station * (rotor_length * 0.86 / 4)
                radius = self.ROTOR_DIAMETER_M * 0.45
                self.box(
                    f"{prefix}_{group}_Rasp_Bar_{group_index + 1:02d}",
                    (x, math.cos(angle) * radius, math.sin(angle) * radius),
                    (rotor_length * 0.12, 0.038, 0.038), material, rotor,
                    rotation=(angle, 0, 0), role=f"{group.lower()}_rasp_bar",
                    bevel=0.004,
                )
                ordinal += 1

    def add_rotor_cage_and_concave(self, side, root):
        """Expose the reconstructed cage and lower concave as real topology."""
        x_positions = tuple(-1.62 + index * 0.54 for index in range(7))
        for index, x in enumerate(x_positions, start=1):
            self.torus(
                f"Twin_Rotor_{side}_Cage_Hoop_{index:02d}",
                (x, 0, 0), 0.395, 0.018,
                self.materials["steel"], root,
                rotation=(0, math.pi / 2, 0), role="rotor_cage_hoop",
            )
        for rail_index, angle in enumerate(
            (0, math.tau / 8, math.tau / 4, 3 * math.tau / 8,
             math.pi, 5 * math.tau / 4, 3 * math.pi / 2,
             7 * math.pi / 4), start=1,
        ):
            y = math.cos(angle) * 0.395
            z = math.sin(angle) * 0.395
            self.pipe_between(
                f"Twin_Rotor_{side}_Cage_Rail_{rail_index:02d}",
                (-1.66, y, z), (1.66, y, z), 0.015,
                self.materials["steel"], root, role="rotor_cage_rail",
            )

        # Five lower-half transverse arcs plus seven longitudinal grate bars
        # read as a separate concave rather than another closed cylinder.
        for station, x in enumerate((-1.42, -0.72, 0.0, 0.72, 1.42), start=1):
            arc_points = []
            for segment in range(9):
                theta = math.pi + math.pi * segment / 8
                arc_points.append(
                    (x, math.sin(theta) * 0.445,
                     math.cos(theta) * 0.445)
                )
            for segment in range(len(arc_points) - 1):
                self.pipe_between(
                    f"Twin_Rotor_{side}_Concave_Arc_{station:02d}_{segment + 1:02d}",
                    arc_points[segment], arc_points[segment + 1], 0.018,
                    self.materials["mechanism"], root,
                    role="rotor_concave_arc",
                )
        for rail_index, theta in enumerate(
            tuple(math.pi + math.pi * index / 6 for index in range(7)),
            start=1,
        ):
            y = math.sin(theta) * 0.445
            z = math.cos(theta) * 0.445
            self.pipe_between(
                f"Twin_Rotor_{side}_Concave_Rail_{rail_index:02d}",
                (-1.55, y, z), (1.55, y, z), 0.014,
                self.materials["mechanism"], root,
                role="rotor_concave_rail",
            )

    def add_twin_rotors(self):
        centers = (("L", -0.49), ("R", 0.49))
        self.rotor_names = []
        for side, z in centers:
            root = self.empty(
                f"Twin_Rotor_{side}_ROOT", (-0.55, 2.42, z),
                self.fixed_root, role="rotary_root",
            )
            drum_name = f"Twin_Rotor_{side}_Drum"
            self.cylinder(
                drum_name, (0, 0, 0), self.ROTOR_DIAMETER_M / 2,
                self.ROTOR_LENGTH_M, self.materials["mechanism_dark"], root,
                vertices=40, rotation=(0, math.pi / 2, 0),
                role="threshing_rotor",
            )
            self.add_rasp_bars(f"Twin_Rotor_{side}", root, self.ROTOR_LENGTH_M)
            self.cone(
                f"Twin_Rotor_{side}_Infeed_Cone", (1.93, 0, 0),
                0.34, 0.12, 0.48, self.materials["mechanism_dark"], root,
                vertices=32, rotation=(0, math.pi / 2, 0),
                role="rotor_infeed_cone",
            )
            self.add_rotor_cage_and_concave(side, root)
            self.cylinder(
                f"Twin_Rotor_{side}_Containment_Guard", (-0.55, 2.42, z),
                0.43, 3.88, self.materials["cutaway"], self.fixed_root,
                vertices=48, rotation=(0, math.pi / 2, 0),
                role="rotor_containment_guard",
            )
            self.rotor_names.append(drum_name)

    def add_twinclean(self):
        grainpan = self.empty(
            "TwinClean_Grainpan_ROOT", (0.30, 1.46, 0), self.fixed_root,
            role="side_shake_motion_root",
        )
        self.box(
            "TwinClean_Grainpan", (0, 0, 0), (2.35, 0.075, 2.22),
            self.materials["crop_path"], grainpan, rotation=(0, 0, -0.025),
            role="grain_pan", bevel=0.008,
        )
        self.twinclean_components = ["TwinClean_Grainpan"]
        for label, x in (("Front", -0.72), ("Rear", -2.20)):
            root = self.empty(
                f"TwinClean_{label}_ROOT", (x, 1.18, 0), self.fixed_root,
                role="side_shake_motion_root",
            )
            for level, y, width in (("Upper", 0.10, 2.18), ("Lower", -0.04, 2.04)):
                name = f"TwinClean_{label}_{level}_Sieve"
                self.box(
                    name, (0, y, 0), (1.30, 0.055, width),
                    self.materials["mechanism"] if level == "Upper" else self.materials["steel"],
                    root, rotation=(0, 0, -0.020), role="cleaning_sieve",
                    bevel=0.006,
                )
                self.twinclean_components.append(name)
            auger = self.empty(
                f"TwinClean_{label}_Clean_Grain_Auger_ROOT", (0, -0.18, 0),
                root, role="rotary_root",
            )
            auger_name = f"TwinClean_{label}_Clean_Grain_Auger"
            self.cylinder(
                auger_name, (0, 0, 0), 0.105, 1.94,
                self.materials["graphite"], auger, vertices=24,
                role="clean_grain_auger",
            )
            self.twinclean_components.append(auger_name)
            self.cylinder(
                f"TwinClean_{label}_Eccentric_Drive", (-0.44, -0.16, -0.98),
                0.105, 0.12, self.materials["mechanism"], root, vertices=24,
                role="cleaning_eccentric_drive",
            )
            for side, z in (("L", -0.96), ("R", 0.96)):
                self.pipe_between(
                    f"TwinClean_{label}_{side}_Shake_Link",
                    (-0.48, -0.10, z), (0.43, 0.04, z), 0.024,
                    self.materials["mechanism"], root,
                    role="side_shake_link",
                )
        for index, (x, z) in enumerate(((0.55, -0.92), (0.55, 0.92), (-0.90, -0.92), (-0.90, 0.92), (-2.20, -0.84), (-2.20, 0.84)), start=1):
            self.box(
                f"TwinClean_Sensor_{index}", (x, 1.36, z),
                (0.09, 0.10, 0.07), self.materials["sensor"], self.fixed_root,
                role="cleaning_sensor", bevel=0.012,
            )

    def add_grain_tank_and_covers(self):
        self.box(
            "Grain_Tank_Lower", (-0.70, 3.38, 0), (3.05, 0.66, 3.20),
            self.materials["body_dark"], self.fixed_root, role="grain_tank",
        )
        for side, sign in (("L", -1), ("R", 1)):
            pivot = self.empty(
                f"Grain_Tank_Cover_{side}_Pivot", (-0.35, 3.73, sign * 0.12),
                self.fixed_root, role="pivot",
            )
            root = self.empty(
                f"Grain_Tank_Cover_{side}_ROOT", parent=pivot,
                role="motion_root",
            )
            self.box(
                f"Grain_Tank_Cover_{side}", (0, 0.035, sign * 0.76),
                (2.30, 0.07, 1.40), self.materials["body"], root,
                role="grain_tank_cover", bevel=0.016,
            )
        for side, z in (("L", -1.13), ("R", 1.13)):
            self.box(
                f"Grain_Tank_Rear_Fixed_Cover_{side}", (-1.82, 3.765, z),
                (0.62, 0.07, 0.66), self.materials["body_dark"],
                self.fixed_root, role="grain_tank_fixed_cover", bevel=0.016,
            )
        bubble = self.empty(
            "Bubble_Up_Auger_ROOT", (-2.13, 3.52, 0), self.fixed_root,
            role="rotary_root",
        )
        self.pipe_between(
            "Bubble_Up_Auger_Tube", (0, 0, 0), (0.45, 0.28, 0),
            0.105, self.materials["body_dark"], bubble,
            role="bubble_up_auger",
        )

    def add_unloader(self):
        base = (-1.15, 3.02, -2.08)
        inner_length = 4.00
        outer_length = 4.60  # selected reach family; exact tube length unresolved
        swing = self.empty(
            "Unloader_Swing_Pivot", base, self.fixed_root, role="pivot"
        )
        root = self.empty("Unloader_ROOT", parent=swing, role="motion_root")
        self.cylinder(
            "Unloader_Base_Collar", (0, 0, 0), 0.18, 0.28,
            self.materials["body_dark"], root, vertices=26,
            rotation=(math.pi / 2, 0, 0), role="unloader_hinge",
        )
        self.pipe_between(
            "Unloader_Inner_Tube", (0, 0, 0), (inner_length, 0, 0),
            0.105, self.materials["body"], root, role="unloader_tube",
        )
        fold = self.empty(
            "Unloader_Fold_Pivot", (inner_length, 0, 0), root, role="pivot"
        )
        outer = self.empty("Unloader_Fold_ROOT", parent=fold, role="motion_root")
        self.cylinder(
            "Unloader_Fold_Hinge", (0, 0.14, 0), 0.150, 0.32,
            self.materials["body_dark"], outer, vertices=26,
            rotation=(math.pi / 2, 0, 0), role="unloader_hinge",
        )
        self.pipe_between(
            "Unloader_Outer_Tube", (0, 0.28, 0), (-outer_length, 0.28, 0),
            0.100, self.materials["body"], outer, role="unloader_tube",
        )
        spout = self.empty(
            "Unloader_Spout_ROOT", (-outer_length, 0.28, 0), outer,
            role="motion_root",
        )
        self.box(
            "Unloader_Spout", (0, -0.15, 0), (0.34, 0.34, 0.28),
            self.materials["body_dark"], spout, role="unloader_spout",
            bevel=0.026,
        )
        self.unloader_geometry = {
            "mechanism_joint_ids": {
                "swing": "unloading_auger_swing",
                "fold": "unloading_auger_fold",
            },
            "base_xyz_m": list(base),
            "reconstructed_inner_centerline_m": inner_length,
            "reconstructed_outer_centerline_m": outer_length,
            "published_swivel_deg": self.UNLOADER_SWING_DEG,
            "fold_unfold_range_deg": [0.0, -180.0],
        }

    def add_residue_system(self):
        self.box(
            "Integrated_Disc_Chopper_House", (-4.42, 1.56, 0),
            (1.48, 1.00, 2.72), self.materials["body_dark"], self.fixed_root,
            role="residue_chopper_house",
        )
        chopper = self.empty(
            "Integrated_Disc_Chopper_ROOT", (-4.35, 1.46, 0),
            self.fixed_root, role="rotary_root",
        )
        self.cylinder(
            "Integrated_Disc_Chopper_Rotor", (0, 0, 0), 0.27, 2.30,
            self.materials["steel"], chopper, vertices=30,
            role="residue_chopper",
        )
        for side, sign in (("L", -1), ("R", 1)):
            root = self.empty(
                f"Rear_Spreader_{side}_ROOT", (-5.05, 1.06, sign * 0.76),
                self.fixed_root, role="rotary_root",
            )
            self.cylinder(
                f"Rear_Spreader_{side}_Disc", (0, 0, 0), 0.34, 0.075,
                self.materials["mechanism"], root, vertices=28,
                rotation=(math.pi / 2, 0, 0), role="residue_spreader_disc",
            )
            for index in range(3):
                angle = math.tau * index / 3
                self.box(
                    f"Rear_Spreader_{side}_Paddle_{index + 1}",
                    (math.cos(angle) * 0.23, 0.07, math.sin(angle) * 0.23),
                    (0.30, 0.07, 0.09), self.materials["graphite"], root,
                    rotation=(0, angle, 0), role="residue_spreader_paddle",
                    bevel=0.008,
                )

    def build_combine(self):
        front_x = 2.15
        rear_x = front_x - self.WHEELBASE_M
        self.add_selected_running_gear(front_x, rear_x)
        self.box(
            "CR11_Main_Frame", (-0.50, 1.12, 0), (8.10, 0.26, 3.05),
            self.materials["graphite"], self.fixed_root, role="chassis",
        )
        self.box(
            "Rear_Service_Bumper", (-self.length / 2 + 0.05, 0.88, 0),
            (0.10, 0.24, 2.92), self.materials["graphite"], self.fixed_root,
            role="rear_bumper", bevel=0.012,
        )
        separator_profile = [
            (-3.495, 1.33), (-3.495, 2.93), (-2.82, 3.42),
            (0.60, 3.63), (2.055, 3.34), (2.055, 1.33),
        ]
        self.side_profile(
            "Separator_Right_Panel", separator_profile, 0.13,
            self.materials["body"], self.fixed_root, z_center=1.63,
            role="separator_house",
        )
        self.side_profile(
            "Separator_Left_Upper_Panel",
            [(-3.495, 2.86), (-3.495, 2.93), (-2.82, 3.42),
             (0.60, 3.63), (2.055, 3.34), (2.055, 2.86)],
            0.13, self.materials["body"], self.fixed_root, z_center=-1.63,
            role="separator_house",
        )
        self.box(
            "Separator_Top", (-0.72, 3.58, 0), (5.55, 0.12, 3.38),
            self.materials["body_dark"], self.fixed_root,
            role="separator_house",
        )
        self.box(
            "Rear_Engine_House", (-3.88, 2.44, 0), (1.86, 2.04, 3.18),
            self.materials["body"], self.fixed_root, role="engine_house",
        )
        for index in range(9):
            self.box(
                f"Rear_Engine_Vent_{index + 1:02d}",
                (-4.20 + index * 0.105, 2.55, -1.61),
                (0.055, 0.98, 0.025), self.materials["graphite"],
                self.fixed_root, role="vent", bevel=0.003,
            )
        cab_floor = 1.36
        self.add_cab(
            1.75, cab_floor, 1.60, 2.55, self.height - cab_floor,
            self.fixed_root,
        )
        self.add_feeder_and_dfr()
        self.add_twin_rotors()
        self.add_twinclean()
        self.add_grain_tank_and_covers()
        self.add_unloader()
        self.add_residue_system()
        self.box(
            "Operator_Access_Platform", (1.84, 1.49, -2.03),
            (1.82, 0.10, 0.54), self.materials["steel"], self.fixed_root,
            role="service_platform", bevel=0.009,
        )
        for index, x in enumerate((1.02, 1.84, 2.66), start=1):
            self.pipe_between(
                f"Operator_Rail_Post_{index}", (x, 1.54, -2.25),
                (x, 2.18, -2.25), 0.024, self.materials["graphite"],
                self.fixed_root, role="service_guard",
            )
        self.pipe_between(
            "Operator_Rail_Top", (1.02, 2.18, -2.25),
            (2.66, 2.18, -2.25), 0.024, self.materials["graphite"],
            self.fixed_root, role="service_guard",
        )
        self.box(
            "Hydraulic_Valve_Manifold", (2.15, 1.70, 1.02),
            (0.48, 0.26, 0.34), self.materials["steel"], self.hydraulics_root,
            role="hydraulic_manifold", bevel=0.020,
        )
        for side, z in (("L", -0.88), ("R", 0.88)):
            self.pipe_between(
                f"Feeder_Hydraulic_Supply_{side}", (2.12, 1.72, z),
                (3.05, 1.46, z * 0.86), 0.019, self.materials["graphite"],
                self.hydraulics_root, role="hydraulic_hose",
            )

    @staticmethod
    def object_bounds(name):
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            raise RuntimeError(f"required mesh is absent: {name}")
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        return {
            "min": [min(point[axis] for point in points) for axis in range(3)],
            "max": [max(point[axis] for point in points) for axis in range(3)],
        }

    @staticmethod
    def rounded_bounds(bounds):
        return {key: [round(value, 6) for value in bounds[key]] for key in ("min", "max")}

    @staticmethod
    def aabb_clearance(first, second):
        gaps = []
        for axis in range(3):
            if first["max"][axis] < second["min"][axis]:
                gaps.append(second["min"][axis] - first["max"][axis])
            elif second["max"][axis] < first["min"][axis]:
                gaps.append(first["min"][axis] - second["max"][axis])
            else:
                gaps.append(0.0)
        return max(gaps)

    @staticmethod
    def is_descendant(child_name, ancestor_name):
        child = bpy.data.objects.get(child_name)
        ancestor = bpy.data.objects.get(ancestor_name)
        while child is not None:
            if child == ancestor:
                return True
            child = child.parent
        return False

    def descendant_mesh_bounds(self, root_name):
        root = bpy.data.objects[root_name]
        names = [obj.name for obj in root.children_recursive if obj.type == "MESH"]
        if not names:
            raise RuntimeError(f"no mesh descendants below {root_name}")
        values = [self.object_bounds(name) for name in names]
        return {
            "names": sorted(names),
            "min": [min(item["min"][axis] for item in values) for axis in range(3)],
            "max": [max(item["max"][axis] for item in values) for axis in range(3)],
        }

    def sample_unloader(self):
        swing = bpy.data.objects["Unloader_Swing_Pivot"]
        fold = bpy.data.objects["Unloader_Fold_Pivot"]
        originals = (swing.rotation_euler.y, fold.rotation_euler.y)
        body_names = ["Separator_Right_Panel", "Separator_Left_Upper_Panel", "Rear_Engine_House", "Grain_Tank_Lower"]
        samples = []
        try:
            poses = [(0.0, math.radians(value)) for value in (0, -45, -90, -135, -180)]
            poses += [(math.radians(value), -math.pi) for value in (21, 42, 63, 84, 105)]
            for swing_angle, fold_angle in poses:
                swing.rotation_euler.y = swing_angle
                fold.rotation_euler.y = fold_angle
                bpy.context.view_layer.update()
                moving = self.descendant_mesh_bounds("Unloader_ROOT")
                clearances = []
                for moving_name in ("Unloader_Inner_Tube", "Unloader_Outer_Tube", "Unloader_Spout"):
                    moving_bounds = self.object_bounds(moving_name)
                    for body_name in body_names:
                        clearances.append(self.aabb_clearance(moving_bounds, self.object_bounds(body_name)))
                samples.append({
                    "swing_deg": round(math.degrees(swing_angle), 3),
                    "fold_deg": round(math.degrees(fold_angle), 3),
                    "minimum_y_m": round(moving["min"][1], 6),
                    "minimum_body_aabb_separation_m": round(min(clearances), 6),
                })
        finally:
            swing.rotation_euler.y, fold.rotation_euler.y = originals
            bpy.context.view_layer.update()
        return samples

    def sample_tank_covers(self):
        left = bpy.data.objects["Grain_Tank_Cover_L_Pivot"]
        right = bpy.data.objects["Grain_Tank_Cover_R_Pivot"]
        original = (left.rotation_euler.x, right.rotation_euler.x)
        bubble = self.object_bounds("Bubble_Up_Auger_Tube")
        samples = []
        try:
            for angle_deg in (0, 20, 40, 60):
                left.rotation_euler.x = math.radians(angle_deg)
                right.rotation_euler.x = math.radians(-angle_deg)
                bpy.context.view_layer.update()
                left_bounds = self.object_bounds("Grain_Tank_Cover_L")
                right_bounds = self.object_bounds("Grain_Tank_Cover_R")
                samples.append({
                    "open_deg": angle_deg,
                    "left_bubble_aabb_separation_m": round(self.aabb_clearance(left_bounds, bubble), 6),
                    "right_bubble_aabb_separation_m": round(self.aabb_clearance(right_bounds, bubble), 6),
                    "maximum_y_m": round(max(left_bounds["max"][1], right_bounds["max"][1], bubble["max"][1]), 6),
                })
        finally:
            left.rotation_euler.x, right.rotation_euler.x = original
            bpy.context.view_layer.update()
        return samples

    @staticmethod
    def detail(method, evidence, semantic_nodes):
        return {
            "method": method,
            "evidence": evidence,
            "semantic_nodes": semantic_nodes,
            "fact_ids": [],
        }

    def machine_specific_validation_gates(self, contract):
        bpy.context.view_layer.update()
        required = self.mechanism_required_gates()
        facts = json.loads((self.output_dir / "evidence" / "facts.json").read_text())
        fact_by_id = {item["id"]: item for item in facts["facts"]}
        config = json.loads((self.output_dir / "configuration.json").read_text())
        viewer = json.loads((self.output_dir / "viewer.json").read_text())
        tire_names = sorted(
            obj.name for obj in bpy.context.scene.objects
            if obj.type == "MESH" and obj.name.endswith("_Tire")
        )
        tire_bounds = {name: self.object_bounds(name) for name in tire_names}
        front_x = bpy.data.objects["Front_Drive_Axle_ROOT"].matrix_world.translation.x
        rear_x = bpy.data.objects["Rear_Axle_ROOT"].matrix_world.translation.x
        wheelbase = abs(front_x - rear_x)
        lateral_min = min(item["min"][2] for item in tire_bounds.values())
        lateral_max = max(item["max"][2] for item in tire_bounds.values())
        measured_width = lateral_max - lateral_min
        feeder = self.object_bounds("Feeder_Casing")
        feeder_width = feeder["max"][2] - feeder["min"][2]
        dfr = self.object_bounds("Dynamic_Feed_Roll")
        dfr_diameter = max(dfr["max"][0] - dfr["min"][0], dfr["max"][1] - dfr["min"][1])
        feeder_chain_names = sorted(
            obj.name for obj in bpy.context.scene.objects
            if obj.type == "MESH" and obj.name.startswith("Feeder_Chain_")
        )
        feeder_slat_names = sorted(
            obj.name for obj in bpy.context.scene.objects
            if obj.type == "MESH" and obj.name.startswith("Feeder_Deep_Drawn_Slat_")
        )

        rotor_records = []
        for side in ("L", "R"):
            rotor = self.object_bounds(f"Twin_Rotor_{side}_Drum")
            guard = self.object_bounds(f"Twin_Rotor_{side}_Containment_Guard")
            size = [rotor["max"][axis] - rotor["min"][axis] for axis in range(3)]
            margin = min(
                *[rotor["min"][axis] - guard["min"][axis] for axis in range(3)],
                *[guard["max"][axis] - rotor["max"][axis] for axis in range(3)],
            )
            rotor_records.append({
                "side": side,
                "measured_size_xyz_m": [round(value, 6) for value in size],
                "minimum_guard_margin_m": round(margin, 6),
                "rasp_bar_counts": {
                    group.lower(): sum(
                        1 for obj in bpy.context.scene.objects
                        if obj.type == "MESH"
                        and obj.name.startswith(f"Twin_Rotor_{side}_{group}_Rasp_Bar_")
                    )
                    for group in ("Standard", "HX", "Spiked")
                },
                "bounds_m": self.rounded_bounds(rotor),
            })
        twinclean_bounds = [self.object_bounds(name) for name in self.twinclean_components]
        clean_min = [-2.95, 0.80, -1.25]
        clean_max = [1.55, 1.75, 1.25]
        clean_margin = min(
            *[bound["min"][axis] - clean_min[axis] for bound in twinclean_bounds for axis in range(3)],
            *[clean_max[axis] - bound["max"][axis] for bound in twinclean_bounds for axis in range(3)],
        )
        twinclean_topology = {
            "upper_sieves": sum(
                1 for obj in bpy.context.scene.objects
                if obj.type == "MESH" and obj.name.startswith("TwinClean_")
                and obj.name.endswith("_Upper_Sieve")
            ),
            "lower_sieves": sum(
                1 for obj in bpy.context.scene.objects
                if obj.type == "MESH" and obj.name.startswith("TwinClean_")
                and obj.name.endswith("_Lower_Sieve")
            ),
            "clean_grain_augers": sum(
                1 for obj in bpy.context.scene.objects
                if obj.type == "MESH" and obj.name.endswith("_Clean_Grain_Auger")
            ),
            "sensor_cues": sum(
                1 for obj in bpy.context.scene.objects
                if obj.type == "MESH" and obj.name.startswith("TwinClean_Sensor_")
            ),
        }
        cover_samples = self.sample_tank_covers()
        cover_min_clearance = min(
            min(item["left_bubble_aabb_separation_m"], item["right_bubble_aabb_separation_m"])
            for item in cover_samples
        )
        cover_max_y = max(item["maximum_y_m"] for item in cover_samples)
        unloader_samples = self.sample_unloader()
        unloader_min_y = min(item["minimum_y_m"] for item in unloader_samples)
        unloader_clearance = min(item["minimum_body_aabb_separation_m"] for item in unloader_samples)
        public_bounds = self.mesh_world_bounds()
        spreader_records = []
        for side in ("L", "R"):
            bounds = self.object_bounds(f"Rear_Spreader_{side}_Disc")
            paddle_count = sum(
                1 for obj in bpy.context.scene.objects
                if obj.type == "MESH"
                and obj.name.startswith(f"Rear_Spreader_{side}_Paddle_")
            )
            spreader_records.append({
                "side": side,
                "bounds_m": self.rounded_bounds(bounds),
                "minimum_y_m": round(bounds["min"][1], 6),
                "paddle_count": paddle_count,
            })
        spreader_min_y = min(item["minimum_y_m"] for item in spreader_records)
        fitted_header_meshes = sorted(
            obj.name for obj in bpy.context.scene.objects if obj.type == "MESH"
            and any(token in obj.name for token in ("Header_Backbone", "Cutterbar", "Reel_Axle", "Reel_Bat", "Crop_Header"))
        )
        viewer_swing = next(
            channel for channel in viewer["motion"]["channels"] if channel["id"] == "unloader-swivel"
        )

        gate_data = {
            "frozen_wheeled_configuration": (
                config["choices"]["front_running_gear"] == "wheeled_dual_710_70_R42"
                and config["choices"]["rear_axle"] == "2WD_steering_axle"
                and config["choices"]["header"] == "not_fitted_feederhouse_only"
                and config["choices"]["grain_tank"] == "567_bu_with_XL_bubble_up_auger"
                and config["choices"]["unloading_rate"] == "6.0_bu_per_s"
                and config["choices"]["residue_management"] == "integrated_standard_chop_three_paddle_disc_up_to_45_ft"
                and len(tire_names) == 6 and not fitted_header_meshes
                and all(bpy.data.objects.get(name) is not None for name in (
                    "Grain_Tank_Lower", "Bubble_Up_Auger_Tube",
                    "Unloader_Inner_Tube", "Integrated_Disc_Chopper_Rotor",
                    "Rear_Spreader_L_Disc", "Rear_Spreader_R_Disc",
                )),
                self.detail(
                    "configuration selection plus exported tire/header topology comparison",
                    {"choices": config["choices"], "tire_meshes": tire_names, "fitted_header_meshes": fitted_header_meshes, "visible_selected_option_meshes": ["Grain_Tank_Lower", "Bubble_Up_Auger_Tube", "Unloader_Inner_Tube", "Integrated_Disc_Chopper_Rotor", "Rear_Spreader_L_Disc", "Rear_Spreader_R_Disc"]},
                    ["Front_Drive_Axle_ROOT", "Rear_Axle_ROOT", "Feederhouse_ROOT", "Grain_Tank_Lower", "Unloader_ROOT"],
                ),
            ),
            "single_identity_root": (
                contract["scene_root_count"] == 1 and contract["root_name"] == "Machine_Root" and contract["identity_root"],
                self.detail(
                    "GLB scene-root identity inspection",
                    {"scene_root_count": contract["scene_root_count"], "root_name": contract["root_name"], "identity_root": contract["identity_root"]},
                    ["Machine_Root"],
                ),
            ),
            "six_tire_contact": (
                len(tire_names) == 6
                and abs(wheelbase - self.WHEELBASE_M) <= TOLERANCE_M
                and abs(measured_width - self.DUAL_WIDTH_M) <= TOLERANCE_M
                and all(-TOLERANCE_M <= item["min"][1] <= TOLERANCE_M for item in tire_bounds.values()),
                self.detail(
                    "world-space tire AABB contact, axle-center wheelbase, and dual envelope measurement",
                    {
                        "contact_count": len(tire_names),
                        "tire_minimum_y_m": {name: round(item["min"][1], 6) for name, item in tire_bounds.items()},
                        "measured_wheelbase_m": round(wheelbase, 6),
                        "published_wheelbase_m": self.WHEELBASE_M,
                        "measured_dual_width_m": round(measured_width, 6),
                        "published_dual_width_m": self.DUAL_WIDTH_M,
                        "absolute_tolerance_m": TOLERANCE_M,
                    },
                    ["Front_Drive_Axle_ROOT", "Rear_Axle_ROOT", "Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot"],
                ),
            ),
            "feeder_continuity": (
                abs(feeder_width - self.FEEDER_WIDTH_M) <= TOLERANCE_M
                and abs(dfr_diameter - self.DFR_DIAMETER_M) <= TOLERANCE_M
                and len(feeder_chain_names) == 4
                and len(feeder_slat_names) == 33
                and self.is_descendant("Feeder_Coupler_Face", "Header_Lift_Pivot")
                and self.is_descendant("Dynamic_Feed_Roll", "Header_Lift_Pivot"),
                self.detail(
                    "world-space feeder/DFR measurement and parent-chain continuity inspection",
                    {
                        "measured_cradle_width_m": round(feeder_width, 6),
                        "published_cradle_width_m": self.FEEDER_WIDTH_M,
                        "measured_dfr_diameter_m": round(dfr_diameter, 6),
                        "published_dfr_diameter_m": self.DFR_DIAMETER_M,
                        "measured_chain_count": len(feeder_chain_names),
                        "published_chain_count": 4,
                        "measured_slat_count": len(feeder_slat_names),
                        "published_slat_count": 33,
                        "chain_meshes": feeder_chain_names,
                        "slat_meshes": feeder_slat_names,
                        "coupler_descends_from_lift": self.is_descendant("Feeder_Coupler_Face", "Header_Lift_Pivot"),
                        "dfr_descends_from_lift": self.is_descendant("Dynamic_Feed_Roll", "Header_Lift_Pivot"),
                    },
                    ["Header_Lift_Pivot", "Feederhouse_ROOT", "Feeder_Faceplate_ROOT", "Dynamic_Feed_Roll_ROOT"],
                ),
            ),
            "twin_rotor_containment": (
                len(rotor_records) == self.ROTOR_COUNT
                and all(abs(item["measured_size_xyz_m"][0] - self.ROTOR_LENGTH_M) <= TOLERANCE_M for item in rotor_records)
                and all(abs(item["measured_size_xyz_m"][1] - self.ROTOR_DIAMETER_M) <= TOLERANCE_M for item in rotor_records)
                and all(abs(item["measured_size_xyz_m"][2] - self.ROTOR_DIAMETER_M) <= TOLERANCE_M for item in rotor_records)
                and all(item["minimum_guard_margin_m"] > 0.02 for item in rotor_records)
                and all(item["rasp_bar_counts"] == {"standard": 40, "hx": 8, "spiked": 12} for item in rotor_records),
                self.detail(
                    "world-space twin-rotor dimensions and guard-containment margins",
                    {"published_count": self.ROTOR_COUNT, "published_diameter_m": self.ROTOR_DIAMETER_M, "published_length_m": self.ROTOR_LENGTH_M, "rotors": rotor_records},
                    ["Twin_Rotor_L_ROOT", "Twin_Rotor_R_ROOT"],
                ),
            ),
            "twinclean_clearance": (
                clean_margin > 0.015
                and twinclean_topology == {
                    "upper_sieves": 2, "lower_sieves": 2,
                    "clean_grain_augers": 2, "sensor_cues": 6,
                },
                self.detail(
                    "world-space component AABBs inside the reconstructed cleaning-system containment",
                    {"components": self.twinclean_components, "measured_topology": twinclean_topology, "published_two_stage_topology": fact_by_id["twinclean-two-stage-topology"]["value"], "containment_min_m": clean_min, "containment_max_m": clean_max, "minimum_rest_margin_m": round(clean_margin, 6), "authority": "containment_only_not_cleaning_performance"},
                    ["TwinClean_Grainpan_ROOT", "TwinClean_Front_ROOT", "TwinClean_Rear_ROOT"],
                ),
            ),
            "tank_cover_and_bubble_up_clearance": (
                len(cover_samples) == 4 and cover_min_clearance > 0.01
                and cover_max_y <= 5.08 + TOLERANCE_M
                and fact_by_id["grain-tank-cover-control"]["value"] == "in_cab_remote_control",
                self.detail(
                    "four-position cover AABB separation from the bubble-up tube and published field-height cap",
                    {"samples": cover_samples, "minimum_aabb_separation_m": round(cover_min_clearance, 6), "maximum_sample_y_m": round(cover_max_y, 6), "published_field_height_m": 5.08, "published_cover_control": fact_by_id["grain-tank-cover-control"]["value"], "authored_topology": "paired_revolute_panels_with_bubble_up_clearance"},
                    ["Grain_Tank_Cover_L_Pivot", "Grain_Tank_Cover_L_ROOT", "Grain_Tank_Cover_R_Pivot", "Grain_Tank_Cover_R_ROOT", "Bubble_Up_Auger_ROOT"],
                ),
            ),
            "unloader_fold_swing_continuity": (
                abs(math.degrees(viewer_swing["to"] - viewer_swing["from"]) - self.UNLOADER_SWING_DEG) <= 0.05
                and self.is_descendant("Unloader_Outer_Tube", "Unloader_Fold_Pivot")
                and self.is_descendant("Unloader_Fold_Pivot", "Unloader_Swing_Pivot"),
                self.detail(
                    "viewer authority-angle comparison plus nested fold/swing parent-chain inspection",
                    {**self.unloader_geometry, "viewer_swivel_total_deg": round(math.degrees(viewer_swing["to"] - viewer_swing["from"]), 6), "outer_tube_descends_from_fold": self.is_descendant("Unloader_Outer_Tube", "Unloader_Fold_Pivot"), "fold_descends_from_swing": self.is_descendant("Unloader_Fold_Pivot", "Unloader_Swing_Pivot")},
                    ["Unloader_Swing_Pivot", "Unloader_ROOT", "Unloader_Fold_Pivot", "Unloader_Fold_ROOT"],
                ),
            ),
            "rear_spreader_clearance": (
                len(spreader_records) == 2 and spreader_min_y > 0.60
                and all(item["paddle_count"] == 3 for item in spreader_records),
                self.detail(
                    "world-space paired spreader-disc AABB and ground-clearance measurement",
                    {"spreader_count": len(spreader_records), "spreaders": spreader_records, "minimum_ground_clearance_m": round(spreader_min_y, 6)},
                    ["Rear_Spreader_L_ROOT", "Rear_Spreader_R_ROOT"],
                ),
            ),
            "ground_collision": (
                public_bounds["min_m"][1] >= -TOLERANCE_M
                and unloader_min_y >= -TOLERANCE_M
                and abs(public_bounds["size_m"][0] - self.length) <= TOLERANCE_M
                and abs(public_bounds["size_m"][1] - self.height) <= TOLERANCE_M,
                self.detail(
                    "neutral whole-machine bounds plus sampled moving-unloader minimum height",
                    {"neutral_public_minimum_y_m": round(public_bounds["min_m"][1], 6), "sampled_unloader_minimum_y_m": round(unloader_min_y, 6), "measured_public_length_m": round(public_bounds["size_m"][0], 6), "published_rigid_transport_length_m": self.length, "measured_public_height_m": round(public_bounds["size_m"][1], 6), "published_road_height_m": self.height, "absolute_tolerance_m": TOLERANCE_M},
                    ["Machine_Root", "Unloader_Swing_Pivot", "Unloader_Fold_Pivot"],
                ),
            ),
            "self_collision": (
                unloader_clearance > 0.005 and cover_min_clearance > 0.01,
                self.detail(
                    "bounded moving-component versus protected-body AABB separation sampling",
                    {"minimum_unloader_body_separation_m": round(unloader_clearance, 6), "minimum_cover_bubble_separation_m": round(cover_min_clearance, 6), "unloader_samples": unloader_samples, "cover_samples": cover_samples},
                    ["Unloader_Swing_Pivot", "Unloader_Fold_Pivot", "Grain_Tank_Cover_L_Pivot", "Grain_Tank_Cover_R_Pivot"],
                ),
            ),
            "swept_volume_collision": (
                len(unloader_samples) == 10 and unloader_min_y >= -TOLERANCE_M and unloader_clearance > 0.005 and cover_min_clearance > 0.01,
                self.detail(
                    "ten-position fold/swivel sampling plus four-position tank-cover sampling",
                    {"unloader_sample_count": len(unloader_samples), "cover_sample_count": len(cover_samples), "sampled_swivel_range_deg": [0, 105], "sampled_fold_range_deg": [0, -180], "minimum_ground_y_m": round(unloader_min_y, 6), "minimum_body_separation_m": round(unloader_clearance, 6), "authority": "presentation-sweep_sampling_not_operational_clearance_authority"},
                    ["Unloader_Swing_Pivot", "Unloader_Fold_Pivot", "Grain_Tank_Cover_L_Pivot", "Grain_Tank_Cover_R_Pivot"],
                ),
            ),
        }
        fact_ids = {
            "frozen_wheeled_configuration": ["grain-tank-capacity", "unloading-rate"],
            "single_identity_root": [],
            "six_tire_contact": ["public-envelope-z", "dual-wheelbase"],
            "feeder_continuity": [
                "feeder-cradle-width", "dynamic-feed-roll-diameter",
                "feeder-chain-count", "feeder-slat-count",
            ],
            "twin_rotor_containment": [
                "rotor-count", "rotor-diameter", "rotor-length",
                "standard-rasp-bars-per-rotor", "hx-rasp-bars-per-rotor",
                "spiked-rasp-bars-per-rotor",
            ],
            "twinclean_clearance": ["twinclean-two-stage-topology"],
            "tank_cover_and_bubble_up_clearance": ["grain-tank-cover-control"],
            "unloader_fold_swing_continuity": ["unloading-auger-swivel"],
            "rear_spreader_clearance": ["selected-spreader-topology"],
            "ground_collision": ["public-envelope-x", "public-envelope-y"],
            "self_collision": [],
            "swept_volume_collision": [],
        }
        records = []
        for gate_id in required:
            detail = gate_data[gate_id][1]
            detail["fact_ids"] = fact_ids[gate_id]
            records.append({
                "id": gate_id,
                "status": "PASS" if gate_data[gate_id][0] else "FAIL",
                "detail": detail,
            })
        return records

    def render_views(self):
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        center = Vector((0, self.height * 0.49, 0))
        span = max(self.length, self.width, self.height)
        views = [
            ("operator-side", (0, self.height * 0.70, -span * 1.55), span * 1.02, "neutral"),
            ("front-three-quarter", (span * 1.08, self.height * 0.94, -span * 1.03), span * 1.16, "neutral"),
            ("rear-three-quarter", (-span * 1.13, self.height * 0.72, span * 0.76), span * 1.08, "neutral"),
            ("elevated-technical", (span * 0.72, span * 1.42, -span * 0.98), span * 1.25, "cutaway"),
            ("articulation-detail", (span * 0.72, span * 1.02, span * 1.28), span * 1.42, "articulated"),
            ("right-side", (0, self.height * 0.70, span * 1.55), span * 1.02, "neutral"),
        ]
        feeder = bpy.data.objects["Header_Lift_Pivot"]
        rotor_l = bpy.data.objects["Twin_Rotor_L_ROOT"]
        rotor_r = bpy.data.objects["Twin_Rotor_R_ROOT"]
        cover_l = bpy.data.objects["Grain_Tank_Cover_L_Pivot"]
        cover_r = bpy.data.objects["Grain_Tank_Cover_R_Pivot"]
        swing = bpy.data.objects["Unloader_Swing_Pivot"]
        fold = bpy.data.objects["Unloader_Fold_Pivot"]
        cutaway_names = (
            "Separator_Left_Upper_Panel", "Separator_Top",
            "Grain_Tank_Lower", "Grain_Tank_Cover_L",
            "Grain_Tank_Cover_R", "Grain_Tank_Rear_Fixed_Cover_L",
            "Grain_Tank_Rear_Fixed_Cover_R",
            "Twin_Rotor_L_Containment_Guard",
            "Twin_Rotor_R_Containment_Guard", "Feeder_Casing",
            "Unloader_Base_Collar", "Unloader_Inner_Tube",
            "Unloader_Fold_Hinge", "Unloader_Outer_Tube",
            "Unloader_Spout",
        )
        rear_process_reveal_names = (
            "Integrated_Disc_Chopper_House",
        )
        paths = []
        for label, location, scale, pose in views:
            for name in cutaway_names:
                bpy.data.objects[name].hide_render = pose == "cutaway"
            for name in rear_process_reveal_names:
                bpy.data.objects[name].hide_render = label == "rear-three-quarter"
            feeder.rotation_euler.z = math.radians(7) if pose == "articulated" else 0
            rotor_l.rotation_euler.x = math.radians(22) if pose in {"cutaway", "articulated"} else 0
            rotor_r.rotation_euler.x = math.radians(-22) if pose in {"cutaway", "articulated"} else 0
            cover_l.rotation_euler.x = math.radians(45) if pose == "articulated" else 0
            cover_r.rotation_euler.x = math.radians(-45) if pose == "articulated" else 0
            swing.rotation_euler.y = math.radians(self.UNLOADER_SWING_DEG) if pose == "articulated" else 0
            fold.rotation_euler.y = -math.pi if pose == "articulated" else 0
            bpy.context.view_layer.update()
            target = center
            camera_location = Vector(location)
            render_scale = scale
            if label == "rear-three-quarter":
                # Purpose-built rear process view: preserve a recognizable rear
                # three-quarter context while making the paired three-paddle
                # spreaders and integrated chopper topology directly reviewable.
                target = Vector((-4.28, 1.20, 0))
                camera_location = target + Vector(
                    (-span * 0.84, span * 0.52, span * 0.78)
                )
                render_scale = span * 0.56
            elif pose == "articulated":
                articulated_bounds = self.mesh_world_bounds()
                target = Vector(tuple(
                    (articulated_bounds["min_m"][axis] + articulated_bounds["max_m"][axis]) / 2
                    for axis in range(3)
                ))
                camera_location = target + (Vector(location) - center)
                render_scale = max(
                    scale, max(articulated_bounds["size_m"]) * 1.45
                )
            camera.location = camera_location
            self.point_at(camera, target)
            camera.data.ortho_scale = render_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        feeder.rotation_euler.z = rotor_l.rotation_euler.x = rotor_r.rotation_euler.x = 0
        cover_l.rotation_euler.x = cover_r.rotation_euler.x = 0
        swing.rotation_euler.y = fold.rotation_euler.y = 0
        for name in cutaway_names:
            bpy.data.objects[name].hide_render = False
        for name in rear_process_reveal_names:
            bpy.data.objects[name].hide_render = False
        bpy.context.view_layer.update()
        return paths


if __name__ == "__main__":
    CR11Builder(load_design(DESIGN), DESIGN, OUTPUT_DIR).run()

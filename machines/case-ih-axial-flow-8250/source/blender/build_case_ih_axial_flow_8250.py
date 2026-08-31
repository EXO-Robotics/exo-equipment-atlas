#!/usr/bin/env python3
"""Deterministic machine-local builder for the Case IH Axial-Flow 8250 study.

The admitted 2022 North American brochure controls the visible feeder width and
length, 2WD wheelbase, rotor diameter, cab height, and 8.8 m unloading-auger
centerline. Hidden centers, tire sizes, body panels, cleaning-system geometry,
and motion endpoints remain explicitly reconstructed. No manufacturer CAD,
logos, textures, or scale illustrations are used.
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


class AxialFlow8250Builder(FleetBuilder):
    """Own the selected dual-front, 2WD, header-not-fitted 8250 topology."""

    WHEELBASE_M = 3.752
    FEEDER_LENGTH_M = 2.388
    FEEDER_WIDTH_M = 1.372
    ROTOR_DIAMETER_M = 0.762
    UNLOADER_LENGTH_M = 8.8
    UNLOADER_SWING_RAD = math.radians(62.0)  # reconstructed presentation range

    def write_machine_wrapper(self):
        """Preserve this machine-owned subclass instead of a generic runpy shim."""

    def required_semantics(self):
        # The selected configuration has no fitted header or reel. The
        # Header_Lift_Pivot name is retained as the viewer's established feeder
        # lift interface, but its descendants are feeder/coupler structure only.
        return [
            "Header_Lift_Pivot",
            "Feederhouse_ROOT",
            "Feeder_Lateral_Tilt_Pivot",
            "Feeder_Faceplate_ForeAft_Pivot",
            "Feeder_Faceplate_ROOT",
            "AFX_Rotor_ROOT",
            "Cleaning_System_Level_ROOT",
            "Unloader_Swing_Pivot",
            "Unloader_ROOT",
            "Unloader_Fold_Pivot",
            "Unloader_Fold_ROOT",
            "Unloader_Spout_Pivot",
            "Unloader_Spout_ROOT",
            "Front_Drive_Axle_ROOT",
            "Rear_Axle_ROOT",
            "Rear_Steering_L_Pivot",
            "Rear_Steering_R_Pivot",
        ]

    def create_materials(self):
        super().create_materials()
        # Keep the public study neutral/unbranded.  The shared combine palette
        # is deliberately generic; this machine binds its exterior to muted
        # low-chroma materials so surface-area checks cannot be dominated by a
        # manufacturer-associated saturated body color.
        self.materials["body"] = self.material(
            "Neutral_Combine_Body", (0.25, 0.29, 0.28), metallic=0.12,
            roughness=0.38,
        )
        self.materials["body_dark"] = self.material(
            "Neutral_Combine_Body_Shadow", (0.105, 0.14, 0.15), metallic=0.18,
            roughness=0.35,
        )
        self.materials["body_panel"] = self.material(
            "Neutral_Combine_Service_Panel", (0.40, 0.43, 0.41), metallic=0.10,
            roughness=0.40,
        )
        self.materials["cutaway"] = self.material(
            "Neutral_Cutaway_Guard", (0.27, 0.31, 0.34), metallic=0.12,
            roughness=0.34, alpha=0.26,
        )
        self.materials["crop_path"] = self.material(
            "Neutral_Crop_Path_Cue", (0.35, 0.36, 0.32), metallic=0.02,
            roughness=0.70,
        )
        self.materials["mechanism"] = self.material(
            "Neutral_Mechanism_Cue", (0.18, 0.31, 0.36), metallic=0.34,
            roughness=0.30,
        )
        self.materials["process"] = self.material(
            "Neutral_Process_Path", (0.40, 0.31, 0.16), metallic=0.08,
            roughness=0.46,
        )

    def torus(
        self, name, location, major_radius, minor_radius, material, parent,
        rotation=(0, 0, 0), role="geometry", major_segments=32,
    ):
        """Create an undistorted structural ring for cages and pivots."""
        bpy.ops.mesh.primitive_torus_add(
            major_radius=major_radius,
            minor_radius=minor_radius,
            major_segments=major_segments,
            minor_segments=8,
            location=location,
            rotation=rotation,
        )
        obj = bpy.context.object
        obj.name = name
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        return self.tag(obj, role=role)

    def arc_strip(
        self, name, center_xy, inner_radius, outer_radius, z_center,
        thickness, material, parent, start_deg=18.0, end_deg=162.0,
        segments=20, role="guard",
    ):
        """Author a true circular fender strip without nonuniform scale."""
        vertices = []
        for z in (z_center - thickness / 2, z_center + thickness / 2):
            for radius in (inner_radius, outer_radius):
                for index in range(segments + 1):
                    angle = math.radians(
                        start_deg + (end_deg - start_deg) * index / segments
                    )
                    vertices.append((
                        center_xy[0] + math.cos(angle) * radius,
                        center_xy[1] + math.sin(angle) * radius,
                        z,
                    ))
        ring = segments + 1
        faces = []
        for layer in (0, 1):
            base = layer * ring * 2
            for index in range(segments):
                a = base + index
                b = base + index + 1
                c = base + ring + index + 1
                d = base + ring + index
                faces.append((a, b, c, d) if layer == 1 else (d, c, b, a))
        for radius_index in (0, 1):
            low = radius_index * ring
            high = 2 * ring + radius_index * ring
            for index in range(segments):
                faces.append((low + index, high + index, high + index + 1, low + index + 1))
        for index in (0, segments):
            faces.append((index, ring + index, 3 * ring + index, 2 * ring + index))
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        bevel = obj.modifiers.new("Edge_Radius", "BEVEL")
        bevel.width = min(0.012, thickness * 0.12)
        bevel.segments = 2
        return self.tag(obj, role=role)

    def add_dual_front_running_gear(self, front_x, rear_x):
        """Author four front and two rear ground contacts at an exact wheelbase."""
        width = self.width
        front_radius = 1.02  # reconstructed because tire size is unresolved
        front_tire_width = 0.44
        outer_center = width / 2 - front_tire_width / 2
        inner_center = outer_center - front_tire_width - 0.05
        front_axle = self.empty(
            "Front_Drive_Axle_ROOT", (front_x, front_radius, 0),
            self.running_root, role="drive_axle_root",
        )
        self.box(
            "Front_Drive_Axle_Beam", (0, 0, 0),
            (0.28, 0.24, inner_center * 2 + 0.20), self.materials["steel"],
            front_axle, role="drive_axle",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.add_wheel(
                f"Front_{side}_Inner", (0, 0, sign * inner_center),
                front_radius, front_tire_width, front_axle, tread_count=16,
            )
            self.add_wheel(
                f"Front_{side}_Outer", (0, 0, sign * outer_center),
                front_radius, front_tire_width, front_axle, tread_count=16,
            )

        rear_radius = 0.72
        rear_tire_width = 0.46
        rear_center = 1.31
        rear_axle = self.empty(
            "Rear_Axle_ROOT", (rear_x, rear_radius, 0), self.running_root,
            role="steering_axle_root",
        )
        self.box(
            "Rear_Steering_Axle_Beam", (0, 0, 0),
            (0.23, 0.20, rear_center * 2), self.materials["steel"], rear_axle,
            role="steering_axle",
        )
        for side, sign in (("L", -1), ("R", 1)):
            steer = self.empty(
                f"Rear_Steering_{side}_Pivot", (0, 0, sign * rear_center),
                rear_axle, role="steering_pivot",
            )
            self.add_wheel(
                f"Rear_{side}", (0, 0, 0), rear_radius, rear_tire_width,
                steer, tread_count=14,
            )
            self.pipe_between(
                f"Rear_Steering_{side}_Arm", (0.0, 0.0, sign * rear_center),
                (0.22, 0.10, sign * (rear_center - 0.16)), 0.030,
                self.materials["steel"], rear_axle, role="steering_arm",
            )
        self.pipe_between(
            "Rear_Steering_Tie_Rod", (0.22, 0.10, -rear_center + 0.16),
            (0.22, 0.10, rear_center - 0.16), 0.026,
            self.materials["rod"], rear_axle, role="steering_tie_rod",
        )
        self.cylinder(
            "Rear_Steering_Cylinder_Barrel", (-0.08, 0.13, -0.34), 0.050,
            0.86, self.materials["graphite"], rear_axle, vertices=20,
            role="steering_hydraulic",
        )
        self.cylinder(
            "Rear_Steering_Cylinder_Rod", (-0.08, 0.13, 0.46), 0.026,
            0.74, self.materials["rod"], rear_axle, vertices=16,
            role="steering_hydraulic",
        )
        self.wheel_geometry = {
            "front_x_m": front_x,
            "rear_x_m": rear_x,
            "front_radius_m": front_radius,
            "front_tire_width_m": front_tire_width,
            "outer_center_abs_z_m": outer_center,
            "inner_center_abs_z_m": inner_center,
            "rear_radius_m": rear_radius,
        }

    def add_rotor_and_cleaning_system(self):
        """Expose the brochure-bounded AFX diameter and reconstructed crop path."""
        rotor_length = 3.10
        rotor_center = (-0.35, 2.25, 0.0)
        rotor = self.empty(
            "AFX_Rotor_ROOT", rotor_center, self.fixed_root, role="rotary_root"
        )
        self.cylinder(
            "AFX_Rotor_Drum", (0, 0, 0), self.ROTOR_DIAMETER_M / 2,
            rotor_length, self.materials["mechanism"], rotor, vertices=40,
            rotation=(0, math.pi / 2, 0), role="threshing_rotor",
        )
        for index in range(12):
            angle = math.tau * index / 12
            radius = self.ROTOR_DIAMETER_M * 0.45
            self.box(
                f"AFX_Rasp_Bar_{index + 1:02d}",
                (0, math.cos(angle) * radius, math.sin(angle) * radius),
                (rotor_length * 0.88, 0.047, 0.047), self.materials["graphite"],
                rotor, rotation=(angle, 0, 0), role="rotor_rasp_bar",
                bevel=0.006,
            )

        self.box(
            "Rotor_Containment_Guard", rotor_center,
            (3.42, 1.02, 1.25), self.materials["cutaway"], self.fixed_root,
            role="rotor_containment_guard", bevel=0.025,
        )
        for side, z in (("L", -0.58), ("R", 0.58)):
            self.pipe_between(
                f"Concave_{side}_Rail", (-1.80, 1.86, z), (1.10, 1.86, z),
                0.035, self.materials["graphite"], self.fixed_root,
                role="concave_support",
            )
        for index in range(7):
            x = -1.60 + index * 0.44
            self.pipe_between(
                f"Concave_Crossbar_{index + 1:02d}",
                (x, 1.84, -0.58), (x, 1.84, 0.58), 0.025,
                self.materials["steel"], self.fixed_root, role="concave_bar",
            )

        cleaning = self.empty(
            "Cleaning_System_Level_ROOT", (-0.65, 1.16, 0), self.fixed_root,
            role="leveling_motion_root",
        )
        self.box(
            "Cleaning_Grain_Pan", (0.65, 0.20, 0), (1.80, 0.07, 1.48),
            self.materials["crop_path"], cleaning, rotation=(0, 0, -0.035),
            role="grain_pan", bevel=0.008,
        )
        self.box(
            "Cleaning_Upper_Sieve", (-0.48, 0.04, 0), (2.05, 0.055, 1.575),
            self.materials["mechanism"], cleaning, rotation=(0, 0, -0.025),
            role="upper_sieve", bevel=0.006,
        )
        self.box(
            "Cleaning_Lower_Sieve", (-0.56, -0.10, 0), (1.86, 0.050, 1.45),
            self.materials["graphite"], cleaning, rotation=(0, 0, -0.020),
            role="lower_sieve", bevel=0.006,
        )
        fan = self.empty(
            "Crossflow_Fan_ROOT", (0.82, -0.16, 0), cleaning,
            role="rotary_root",
        )
        self.cylinder(
            "Crossflow_Fan", (0, 0, 0), 0.1955, 1.38,
            self.materials["mechanism"], fan, vertices=28, role="cleaning_fan",
        )
        for index in range(8):
            angle = math.tau * index / 8
            self.box(
                f"Crossflow_Fan_Vane_{index + 1:02d}",
                (math.cos(angle) * 0.13, math.sin(angle) * 0.13, 0),
                (0.035, 0.20, 1.30), self.materials["steel"], fan,
                rotation=(0, 0, angle), role="fan_vane", bevel=0.004,
            )
        self.cylinder(
            "Cleaning_Level_Cross_Shaft", (-0.72, -0.20, 0), 0.060, 1.66,
            self.materials["mechanism"], cleaning, vertices=24,
            role="leveling_cross_shaft",
        )
        for side, z in (("L", -0.68), ("R", 0.68)):
            self.pipe_between(
                f"Cleaning_Level_{side}_Link", (-0.88, -0.14, z),
                (-0.30, 0.12, z), 0.026, self.materials["steel"], cleaning,
                role="leveling_link",
            )

    def add_feederhouse(self):
        """Build the no-header feeder/coupler interface at published dimensions."""
        base_x = self.length / 2 - self.FEEDER_LENGTH_M - 0.080
        pivot = self.empty(
            "Header_Lift_Pivot", (base_x, 1.27, 0), self.fixed_root,
            role="feeder_lift_pivot",
        )
        feeder = self.empty("Feederhouse_ROOT", parent=pivot, role="motion_root")
        self.side_profile(
            "Feeder_Casing",
            [
                (0.0, -0.41),
                (self.FEEDER_LENGTH_M, -0.31),
                (self.FEEDER_LENGTH_M, 0.21),
                (0.0, 0.21),
            ],
            self.FEEDER_WIDTH_M, self.materials["body_dark"], feeder,
            role="feederhouse",
        )
        for index in range(3):
            y = -0.27 + index * 0.20
            self.box(
                f"Feeder_Chain_Flight_{index + 1}",
                (self.FEEDER_LENGTH_M * 0.52, y, 0),
                (self.FEEDER_LENGTH_M * 0.88, 0.035, self.FEEDER_WIDTH_M * 0.90),
                self.materials["steel"], feeder, role="feeder_chain_cue",
                bevel=0.004,
            )
        for side, z in (("L", -self.FEEDER_WIDTH_M * 0.42), ("R", self.FEEDER_WIDTH_M * 0.42)):
            self.pipe_between(
                f"Feeder_Lift_{side}_Cylinder",
                (0.20, 0.22, z), (1.18, -0.19, z), 0.034,
                self.materials["rod"], feeder, role="hydraulic",
            )

        lateral = self.empty(
            "Feeder_Lateral_Tilt_Pivot", (self.FEEDER_LENGTH_M, -0.10, 0),
            feeder, role="pivot",
        )
        fore_aft = self.empty(
            "Feeder_Faceplate_ForeAft_Pivot", parent=lateral, role="pivot"
        )
        face = self.empty(
            "Feeder_Faceplate_ROOT", parent=fore_aft, role="motion_root"
        )
        self.box(
            "Feeder_Coupler_Face", (0.040, 0, 0),
            (0.080, 0.70, self.FEEDER_WIDTH_M), self.materials["steel"], face,
            role="header_coupler_interface", bevel=0.012,
        )
        for side, z in (("L", -0.53), ("R", 0.53)):
            self.box(
                f"Feeder_Coupler_{side}_Hook", (0.025, -0.10, z),
                (0.050, 0.17, 0.10), self.materials["graphite"], face,
                role="header_coupler_interface", bevel=0.010,
            )
        self.feeder_geometry = {"base_x_m": base_x}

    def add_unloader(self):
        """Build a two-piece auger whose tube centerlines total exactly 8.8 m."""
        base = (-0.82, 2.93, -1.43)
        inner_length = 3.60
        outer_length = self.UNLOADER_LENGTH_M - inner_length
        swing = self.empty(
            "Unloader_Swing_Pivot", base, self.fixed_root, role="pivot"
        )
        unloader = self.empty("Unloader_ROOT", parent=swing, role="motion_root")
        self.cylinder(
            "Unloader_Base_Collar", (0, 0, 0), 0.16, 0.24,
            self.materials["body_dark"], unloader, vertices=24,
            rotation=(math.pi / 2, 0, 0), role="unloader_hinge",
        )
        self.pipe_between(
            "Unloader_Inner_Tube", (0, 0, 0), (inner_length, 0, 0),
            0.090, self.materials["body"], unloader, role="unloader_tube",
        )
        fold = self.empty(
            "Unloader_Fold_Pivot", (inner_length, 0, 0), unloader, role="pivot"
        )
        outer = self.empty("Unloader_Fold_ROOT", parent=fold, role="motion_root")
        self.cylinder(
            "Unloader_Fold_Hinge", (0, 0.12, 0), 0.135, 0.28,
            self.materials["body_dark"], outer, vertices=24,
            rotation=(math.pi / 2, 0, 0), role="unloader_hinge",
        )
        self.pipe_between(
            "Unloader_Outer_Tube", (0, 0.24, 0), (-outer_length, 0.24, 0),
            0.086, self.materials["body"], outer, role="unloader_tube",
        )
        spout_pivot = self.empty(
            "Unloader_Spout_Pivot", (-outer_length, 0.24, 0), outer, role="pivot"
        )
        spout = self.empty(
            "Unloader_Spout_ROOT", parent=spout_pivot, role="motion_root"
        )
        self.box(
            "Unloader_Pivoting_Spout", (0, -0.13, 0), (0.28, 0.30, 0.24),
            self.materials["body_dark"], spout, role="unloader_spout",
            bevel=0.025,
        )
        self.unloader_geometry = {
            "mechanism_joint_ids": {
                "swing": "unloading_auger_swing",
                "fold": "unloading_auger_fold",
            },
            "base_xyz_m": list(base),
            "inner_centerline_m": inner_length,
            "outer_centerline_m": outer_length,
            "total_centerline_m": inner_length + outer_length,
            "fold_unfold_range_deg": [0.0, -180.0],
            "swing_range_deg": [0.0, math.degrees(self.UNLOADER_SWING_RAD)],
        }

    def build_combine(self):
        length, height = self.length, self.height
        front_x = 1.70
        rear_x = front_x - self.WHEELBASE_M
        self.add_dual_front_running_gear(front_x, rear_x)

        self.box(
            "Combine_Main_Frame", (-0.45, 1.07, 0), (6.65, 0.24, 2.42),
            self.materials["graphite"], self.fixed_root, role="chassis",
        )
        self.box(
            "Rear_Service_Bumper", (-length / 2 + 0.05, 0.86, 0),
            (0.10, 0.22, 2.30), self.materials["graphite"], self.fixed_root,
            role="rear_bumper", bevel=0.012,
        )
        separator_profile = [
            (-2.775, 1.175), (-2.775, 2.92), (-2.30, 3.24),
            (0.55, 3.41), (1.675, 3.24), (1.675, 1.175),
        ]
        self.side_profile(
            "Separator_Right_Panel", separator_profile, 0.12,
            self.materials["body"], self.fixed_root, z_center=1.20,
            role="separator_house",
        )
        self.side_profile(
            "Separator_Left_Upper_Panel",
            [(-2.775, 2.72), (-2.775, 2.92), (-2.30, 3.24),
             (0.55, 3.41), (1.675, 3.24), (1.675, 2.72)],
            0.12, self.materials["body"], self.fixed_root, z_center=-1.20,
            role="separator_house",
        )
        self.box(
            "Separator_Top", (-0.55, 3.35, 0), (4.45, 0.12, 2.52),
            self.materials["body_dark"], self.fixed_root, role="separator_house",
        )
        self.box(
            "Rear_Engine_House", (-3.35, 2.25, 0), (1.72, 1.95, 2.48),
            self.materials["body"], self.fixed_root, role="engine_house",
        )
        for index in range(8):
            self.box(
                f"Rear_Engine_Vent_{index + 1:02d}",
                (-3.65 + index * 0.10, 2.45, -1.255),
                (0.050, 0.88, 0.025), self.materials["graphite"],
                self.fixed_root, role="vent", bevel=0.003,
            )
        self.box(
            "Grain_Tank_Lower", (-0.75, 3.38, 0), (2.65, 0.64, 2.35),
            self.materials["body_dark"], self.fixed_root, role="grain_tank",
        )
        self.box(
            "Grain_Tank_Top_Rail", (-0.75, 3.72, 0), (2.52, 0.08, 2.22),
            self.materials["steel"], self.fixed_root, role="grain_tank_rail",
        )
        self.box(
            "Grain_Tank_Cover_L_Fixed", (-0.75, 3.755, -0.55),
            (2.38, 0.055, 1.08), self.materials["body"], self.fixed_root,
            rotation=(math.radians(8.0), 0, 0),
            role="grain_tank_cover", bevel=0.012,
        )
        self.box(
            "Grain_Tank_Cover_R_Fixed", (-0.75, 3.755, 0.55),
            (2.38, 0.055, 1.08), self.materials["body"], self.fixed_root,
            rotation=(math.radians(-8.0), 0, 0),
            role="grain_tank_cover", bevel=0.012,
        )
        cab_floor = 1.34
        self.add_cab(
            1.34, cab_floor, 1.45, 2.12, height - cab_floor,
            self.fixed_root,
        )
        self.add_rotor_and_cleaning_system()
        self.add_feederhouse()
        self.add_unloader()

        # Reconstructed service-access cues preserve the selected transport
        # envelope while making the operator-side working area legible.
        self.box(
            "Operator_Access_Platform", (1.55, 1.43, -1.48),
            (1.55, 0.09, 0.44), self.materials["steel"], self.fixed_root,
            role="service_platform", bevel=0.008,
        )
        for index, x in enumerate((0.85, 1.55, 2.25), start=1):
            self.pipe_between(
                f"Operator_Rail_Post_{index}", (x, 1.47, -1.68),
                (x, 2.08, -1.68), 0.022, self.materials["graphite"],
                self.fixed_root, role="service_guard",
            )
        self.pipe_between(
            "Operator_Rail_Top", (0.85, 2.08, -1.68),
            (2.25, 2.08, -1.68), 0.022, self.materials["graphite"],
            self.fixed_root, role="service_guard",
        )

        self.box(
            "Hydraulic_Valve_Manifold", (1.58, 1.62, 0.82),
            (0.42, 0.24, 0.30), self.materials["steel"], self.hydraulics_root,
            role="hydraulic_manifold", bevel=0.018,
        )
        for side, z in (("L", -0.72), ("R", 0.72)):
            self.pipe_between(
                f"Feeder_Hydraulic_Supply_{side}", (1.55, 1.64, z),
                (2.32, 1.42, z * 0.82), 0.018, self.materials["graphite"],
                self.hydraulics_root, role="hydraulic_hose",
            )

        # The admitted brochure lists alternate chopper/beater packages, while
        # this candidate leaves the residue order unresolved.  Retain only the
        # neutral discharge interface; do not falsely fit an optional rotor.
        self.box(
            "Residue_Discharge_Interface", (-3.55, 1.35, 0),
            (0.24, 0.34, 1.86), self.materials["graphite"], self.fixed_root,
            role="unresolved_residue_interface", bevel=0.012,
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
        bounds = [self.object_bounds(name) for name in names]
        return {
            "names": sorted(names),
            "min": [min(item["min"][axis] for item in bounds) for axis in range(3)],
            "max": [max(item["max"][axis] for item in bounds) for axis in range(3)],
        }

    def sample_unloader(self):
        swing = bpy.data.objects["Unloader_Swing_Pivot"]
        fold = bpy.data.objects["Unloader_Fold_Pivot"]
        body_names = ["Separator_Right_Panel", "Separator_Left_Upper_Panel", "Rear_Engine_House", "Grain_Tank_Lower"]
        original = (swing.rotation_euler.y, fold.rotation_euler.y)
        samples = []
        try:
            poses = [(0.0, math.radians(value)) for value in (0, -45, -90, -135, -180)]
            poses += [
                (math.radians(value), -math.pi)
                for value in (15, 30, 45, 62)
            ]
            for swing_angle, fold_angle in poses:
                swing.rotation_euler.y = swing_angle
                fold.rotation_euler.y = fold_angle
                bpy.context.view_layer.update()
                moving = self.descendant_mesh_bounds("Unloader_ROOT")
                minimum_y = moving["min"][1]
                clearances = []
                for moving_name in ("Unloader_Inner_Tube", "Unloader_Outer_Tube", "Unloader_Pivoting_Spout"):
                    moving_bounds = self.object_bounds(moving_name)
                    for body_name in body_names:
                        clearances.append(self.aabb_clearance(moving_bounds, self.object_bounds(body_name)))
                samples.append({
                    "swing_deg": round(math.degrees(swing_angle), 3),
                    "fold_deg": round(math.degrees(fold_angle), 3),
                    "minimum_y_m": round(minimum_y, 6),
                    "minimum_body_aabb_separation_m": round(min(clearances), 6),
                })
        finally:
            swing.rotation_euler.y, fold.rotation_euler.y = original
            bpy.context.view_layer.update()
        return samples

    def sample_cleaning_level(self, containment_min, containment_max):
        root = bpy.data.objects["Cleaning_System_Level_ROOT"]
        original = root.rotation_euler.x
        samples = []
        try:
            for angle_deg in (-7.0, 0.0, 7.0):
                root.rotation_euler.x = math.radians(angle_deg)
                bpy.context.view_layer.update()
                bounds = self.descendant_mesh_bounds("Cleaning_System_Level_ROOT")
                margin = min(
                    *[bounds["min"][axis] - containment_min[axis] for axis in range(3)],
                    *[containment_max[axis] - bounds["max"][axis] for axis in range(3)],
                )
                samples.append({
                    "level_angle_deg": angle_deg,
                    "bounds_m": self.rounded_bounds(bounds),
                    "minimum_containment_margin_m": round(margin, 6),
                })
        finally:
            root.rotation_euler.x = original
            bpy.context.view_layer.update()
        return samples

    @staticmethod
    def rounded_bounds(bounds):
        return {
            key: [round(value, 6) for value in bounds[key]]
            for key in ("min", "max")
        }

    def machine_specific_validation_gates(self, contract):
        bpy.context.view_layer.update()
        required = self.mechanism_required_gates()
        facts = json.loads((self.output_dir / "evidence" / "facts.json").read_text())
        fact_by_id = {item["id"]: item for item in facts["facts"]}
        config = json.loads((self.output_dir / "configuration.json").read_text())
        viewer = json.loads((self.output_dir / "viewer.json").read_text())
        viewer_channels = {channel["id"]: channel for channel in viewer["motion"]["channels"]}

        tire_names = sorted(
            obj.name for obj in bpy.context.scene.objects
            if obj.type == "MESH" and obj.name.endswith("_Tire")
        )
        tire_bounds = {name: self.object_bounds(name) for name in tire_names}
        front_x = bpy.data.objects["Front_Drive_Axle_ROOT"].matrix_world.translation.x
        rear_x = bpy.data.objects["Rear_Axle_ROOT"].matrix_world.translation.x
        wheelbase = abs(front_x - rear_x)
        feeder = self.object_bounds("Feeder_Casing")
        feeder_size = [feeder["max"][axis] - feeder["min"][axis] for axis in range(3)]
        rotor = self.object_bounds("AFX_Rotor_Drum")
        rotor_guard = self.object_bounds("Rotor_Containment_Guard")
        rotor_size = [rotor["max"][axis] - rotor["min"][axis] for axis in range(3)]
        rotor_margins = [
            rotor["min"][axis] - rotor_guard["min"][axis]
            for axis in range(3)
        ] + [
            rotor_guard["max"][axis] - rotor["max"][axis]
            for axis in range(3)
        ]
        cleaning_names = ["Cleaning_Grain_Pan", "Cleaning_Upper_Sieve", "Cleaning_Lower_Sieve", "Crossflow_Fan"]
        separator_min = [-2.775, 0.65, -1.26]
        separator_max = [1.675, 3.41, 1.26]
        cleaning_samples = self.sample_cleaning_level(separator_min, separator_max)
        cleaning_margin = min(item["minimum_containment_margin_m"] for item in cleaning_samples)
        public_bounds = self.mesh_world_bounds()
        samples = self.sample_unloader()
        minimum_sample_y = min(item["minimum_y_m"] for item in samples)
        minimum_swept_clearance = min(item["minimum_body_aabb_separation_m"] for item in samples)
        header_mesh_tokens = ("Header_Backbone", "Cutterbar", "Reel_Axle", "Reel_Bat", "Crop_Header")
        fitted_header_meshes = sorted(
            obj.name for obj in bpy.context.scene.objects if obj.type == "MESH"
            and any(token in obj.name for token in header_mesh_tokens)
        )
        fitted_residue_option_meshes = sorted(
            obj.name for obj in bpy.context.scene.objects
            if obj.type == "MESH" and "Residue_Chopper" in obj.name
        )
        lateral_channel = viewer_channels["feeder-lateral-tilt"]
        faceplate_channel = viewer_channels["feeder-faceplate-fore-aft"]
        cleaning_channel = viewer_channels["cleaning-level-study"]

        gate_data = {
            "model_year_boundary_visible": (
                "unresolved" in config["identity"].get("model_year", "").lower()
                and "exact model year" in viewer["evidence"]["boundary"].lower(),
                {
                    "configuration_model_year": config["identity"].get("model_year"),
                    "viewer_boundary": viewer["evidence"]["boundary"],
                    "authority": "configuration_and_viewer_disclosure_check",
                },
            ),
            "frozen_visible_configuration": (
                config["choices"]["front_running_gear"] == "dual_drive_tires_visual_study"
                and config["choices"]["header"] == "not_fitted_feederhouse_only"
                and config["choices"]["grain_tank"] == "410_bu_14448_L"
                and len(tire_names) == 6 and not fitted_header_meshes
                and not fitted_residue_option_meshes
                and bpy.data.objects.get("Grain_Tank_Lower") is not None,
                {
                    "selected_front_running_gear": config["choices"]["front_running_gear"],
                    "selected_header": config["choices"]["header"],
                    "selected_grain_tank": config["choices"]["grain_tank"],
                    "tire_meshes": tire_names,
                    "fitted_header_meshes": fitted_header_meshes,
                    "fitted_residue_option_meshes": fitted_residue_option_meshes,
                    "visible_grain_tank_mesh": "Grain_Tank_Lower",
                },
            ),
            "single_identity_root": (
                contract["scene_root_count"] == 1 and contract["root_name"] == "Machine_Root" and contract["identity_root"],
                {
                    "scene_root_count": contract["scene_root_count"],
                    "root_name": contract["root_name"],
                    "identity_root": contract["identity_root"],
                },
            ),
            "wheeled_contact": (
                len(tire_names) == 6
                and abs(wheelbase - self.WHEELBASE_M) <= TOLERANCE_M
                and all(-TOLERANCE_M <= bound["min"][1] <= TOLERANCE_M for bound in tire_bounds.values()),
                {
                    "contact_count": len(tire_names),
                    "tire_minimum_y_m": {name: round(bound["min"][1], 6) for name, bound in tire_bounds.items()},
                    "measured_wheelbase_m": round(wheelbase, 6),
                    "published_2wd_wheelbase_m": self.WHEELBASE_M,
                    "wheelbase_fact": fact_by_id.get("wheelbase-2wd"),
                    "absolute_tolerance_m": TOLERANCE_M,
                },
            ),
            "feeder_and_faceplate_continuity": (
                abs(feeder_size[0] - self.FEEDER_LENGTH_M) <= TOLERANCE_M
                and abs(feeder_size[2] - self.FEEDER_WIDTH_M) <= TOLERANCE_M
                and self.is_descendant("Feeder_Coupler_Face", "Header_Lift_Pivot")
                and abs(math.degrees(lateral_channel["from"]) + 5.0) <= 0.01
                and abs(math.degrees(lateral_channel["to"]) - 5.0) <= 0.01
                and abs(math.degrees(faceplate_channel["to"] - faceplate_channel["from"]) - 12.0) <= 0.01,
                {
                    "measured_feeder_length_m": round(feeder_size[0], 6),
                    "published_feeder_length_m": self.FEEDER_LENGTH_M,
                    "measured_feeder_width_m": round(feeder_size[2], 6),
                    "published_feeder_width_m": self.FEEDER_WIDTH_M,
                    "coupler_descends_from_lift_pivot": self.is_descendant("Feeder_Coupler_Face", "Header_Lift_Pivot"),
                    "viewer_lateral_tilt_range_deg": [
                        round(math.degrees(lateral_channel["from"]), 6),
                        round(math.degrees(lateral_channel["to"]), 6),
                    ],
                    "published_lateral_tilt_each_side_deg": 5.0,
                    "viewer_faceplate_total_range_deg": round(
                        math.degrees(faceplate_channel["to"] - faceplate_channel["from"]), 6
                    ),
                    "published_faceplate_total_range_deg": 12.0,
                    "feeder_bounds_m": self.rounded_bounds(feeder),
                },
            ),
            "rotor_containment": (
                abs(rotor_size[1] - self.ROTOR_DIAMETER_M) <= TOLERANCE_M
                and abs(rotor_size[2] - self.ROTOR_DIAMETER_M) <= TOLERANCE_M
                and min(rotor_margins) > 0.02,
                {
                    "measured_rotor_size_xyz_m": [round(value, 6) for value in rotor_size],
                    "published_rotor_diameter_m": self.ROTOR_DIAMETER_M,
                    "minimum_guard_margin_m": round(min(rotor_margins), 6),
                    "rotor_bounds_m": self.rounded_bounds(rotor),
                    "guard_bounds_m": self.rounded_bounds(rotor_guard),
                },
            ),
            "cleaning_system_clearance": (
                len(cleaning_samples) == 3 and cleaning_margin > 0.015
                and abs(math.degrees(cleaning_channel["from"]) + 7.0) <= 0.01
                and abs(math.degrees(cleaning_channel["to"]) - 7.0) <= 0.01,
                {
                    "component_names": cleaning_names,
                    "reconstructed_separator_bounds_m": {
                        "min": separator_min, "max": separator_max,
                    },
                    "samples": cleaning_samples,
                    "minimum_sampled_margin_m": round(cleaning_margin, 6),
                    "viewer_level_range_deg": [
                        round(math.degrees(cleaning_channel["from"]), 6),
                        round(math.degrees(cleaning_channel["to"]), 6),
                    ],
                    "published_level_range_deg": [-7.0, 7.0],
                    "authority": "reconstructed_containment_not_cleaning_performance",
                },
            ),
            "unloader_fold_swing_continuity": (
                abs(self.unloader_geometry["total_centerline_m"] - self.UNLOADER_LENGTH_M) <= TOLERANCE_M
                and self.is_descendant("Unloader_Outer_Tube", "Unloader_Fold_Pivot")
                and self.is_descendant("Unloader_Fold_Pivot", "Unloader_Swing_Pivot"),
                {
                    **self.unloader_geometry,
                    "published_total_centerline_m": self.UNLOADER_LENGTH_M,
                    "outer_tube_descends_from_fold_pivot": self.is_descendant("Unloader_Outer_Tube", "Unloader_Fold_Pivot"),
                    "fold_pivot_descends_from_swing_pivot": self.is_descendant("Unloader_Fold_Pivot", "Unloader_Swing_Pivot"),
                },
            ),
            "ground_collision": (
                public_bounds["min_m"][1] >= -TOLERANCE_M
                and minimum_sample_y >= -TOLERANCE_M
                and abs(public_bounds["size_m"][1] - self.height) <= TOLERANCE_M,
                {
                    "neutral_public_minimum_y_m": round(public_bounds["min_m"][1], 6),
                    "measured_public_height_m": round(public_bounds["size_m"][1], 6),
                    "published_cab_height_m": self.height,
                    "sampled_unloader_minimum_y_m": round(minimum_sample_y, 6),
                    "absolute_tolerance_m": TOLERANCE_M,
                },
            ),
            "self_collision": (
                minimum_swept_clearance > 0.005,
                {
                    "sampled_unloader_minimum_body_aabb_separation_m": round(minimum_swept_clearance, 6),
                    "samples": samples,
                    "method": "conservative moving-component versus protected-body AABB separation",
                },
            ),
            "swept_volume_collision": (
                len(samples) == 9 and minimum_sample_y >= -TOLERANCE_M and minimum_swept_clearance > 0.005,
                {
                    "sample_count": len(samples),
                    "sampled_fold_range_deg": [0, -180],
                    "sampled_swing_range_deg": [0, 62],
                    "minimum_ground_y_m": round(minimum_sample_y, 6),
                    "minimum_body_aabb_separation_m": round(minimum_swept_clearance, 6),
                    "authority": "bounded_presentation_sampling_not_operational_clearance_authority",
                },
            ),
        }
        gate_meta = {
            "model_year_boundary_visible": (
                "configuration and viewer boundary disclosure comparison",
                [],
                [],
            ),
            "frozen_visible_configuration": (
                "selected-option record compared with authored tire and attachment topology",
                ["Front_Drive_Axle_ROOT", "Rear_Axle_ROOT", "Feederhouse_ROOT", "Grain_Tank_Lower"],
                ["grain-tank-capacity"],
            ),
            "single_identity_root": (
                "GLB scene-root identity inspection",
                ["Machine_Root"],
                [],
            ),
            "wheeled_contact": (
                "world-space tire AABB contact and axle-center wheelbase measurement",
                ["Front_Drive_Axle_ROOT", "Rear_Axle_ROOT", "Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot"],
                ["wheelbase-2wd"],
            ),
            "feeder_and_faceplate_continuity": (
                "world-space feeder dimensions plus parent-chain continuity inspection",
                ["Header_Lift_Pivot", "Feederhouse_ROOT", "Feeder_Lateral_Tilt_Pivot", "Feeder_Faceplate_ForeAft_Pivot", "Feeder_Faceplate_ROOT"],
                ["feeder-width", "feeder-length", "feeder-lateral-tilt", "feeder-faceplate-tilt"],
            ),
            "rotor_containment": (
                "world-space rotor diameter and containment-guard margin measurement",
                ["AFX_Rotor_ROOT"],
                ["rotor-diameter"],
            ),
            "cleaning_system_clearance": (
                "world-space cleaning-component AABBs inside reconstructed containment",
                ["Cleaning_System_Level_ROOT", "Crossflow_Fan_ROOT"],
                ["self-leveling-slope"],
            ),
            "unloader_fold_swing_continuity": (
                "centerline-length sum and nested fold/swing parent-chain inspection",
                ["Unloader_Swing_Pivot", "Unloader_ROOT", "Unloader_Fold_Pivot", "Unloader_Fold_ROOT", "Unloader_Spout_Pivot", "Unloader_Spout_ROOT"],
                ["unloading-auger-length"],
            ),
            "ground_collision": (
                "neutral whole-machine bounds plus sampled moving-unloader minimum height",
                ["Machine_Root", "Unloader_Swing_Pivot", "Unloader_Fold_Pivot"],
                ["public-envelope-y"],
            ),
            "self_collision": (
                "bounded moving-component versus protected-body AABB separation sampling",
                ["Unloader_Swing_Pivot", "Unloader_Fold_Pivot"],
                [],
            ),
            "swept_volume_collision": (
                "nine-position fold and swing presentation-sweep sampling",
                ["Unloader_Swing_Pivot", "Unloader_Fold_Pivot"],
                [],
            ),
        }
        records = []
        for gate_id in required:
            method, semantic_nodes, fact_ids = gate_meta[gate_id]
            records.append({
                "id": gate_id,
                "status": "PASS" if gate_data[gate_id][0] else "FAIL",
                "detail": {
                    "method": method,
                    "evidence": gate_data[gate_id][1],
                    "semantic_nodes": semantic_nodes,
                    "fact_ids": fact_ids,
                },
            })
        return records

    def render_views(self):
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        center = Vector((0, self.height * 0.48, 0))
        span = max(self.length, self.width, self.height)
        views = [
            ("operator-side", (0, self.height * 0.67, -span * 1.55), span * 1.04, "neutral"),
            ("front-three-quarter", (span * 1.05, self.height * 0.90, -span * 1.02), span * 1.15, "neutral"),
            ("rear-three-quarter", (-span * 1.12, self.height * 0.72, span * 0.78), span * 1.08, "neutral"),
            ("elevated-technical", (span * 0.70, span * 1.38, -span * 0.96), span * 1.24, "cutaway"),
            ("articulation-detail", (span * 0.72, span * 1.02, span * 1.28), span * 1.48, "articulated"),
            ("right-side", (0, self.height * 0.67, span * 1.55), span * 1.04, "neutral"),
        ]
        feeder = bpy.data.objects["Header_Lift_Pivot"]
        rotor = bpy.data.objects["AFX_Rotor_ROOT"]
        swing = bpy.data.objects["Unloader_Swing_Pivot"]
        fold = bpy.data.objects["Unloader_Fold_Pivot"]
        cutaway_names = (
            "Separator_Left_Upper_Panel", "Separator_Top",
            "Grain_Tank_Lower", "Grain_Tank_Top_Rail",
            "Grain_Tank_Cover_L_Fixed", "Grain_Tank_Cover_R_Fixed",
            "Rotor_Containment_Guard", "Feeder_Casing",
            "Unloader_Base_Collar", "Unloader_Inner_Tube",
            "Unloader_Fold_Hinge", "Unloader_Outer_Tube",
            "Unloader_Pivoting_Spout",
        )
        paths = []
        for label, location, scale, pose in views:
            for name in cutaway_names:
                bpy.data.objects[name].hide_render = pose == "cutaway"
            feeder.rotation_euler.z = math.radians(7) if pose == "articulated" else 0
            rotor.rotation_euler.x = math.radians(24) if pose in {"cutaway", "articulated"} else 0
            swing.rotation_euler.y = self.UNLOADER_SWING_RAD if pose == "articulated" else 0
            fold.rotation_euler.y = math.radians(-180) if pose == "articulated" else 0
            bpy.context.view_layer.update()
            target = center
            camera_location = Vector(location)
            render_scale = scale
            if pose == "articulated":
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
        feeder.rotation_euler.z = rotor.rotation_euler.x = 0
        swing.rotation_euler.y = fold.rotation_euler.y = 0
        for name in cutaway_names:
            bpy.data.objects[name].hide_render = False
        bpy.context.view_layer.update()
        return paths


if __name__ == "__main__":
    AxialFlow8250Builder(load_design(DESIGN), DESIGN, OUTPUT_DIR).run()

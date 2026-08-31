#!/usr/bin/env python3
"""Build the neutral cross-market Steiger 715 Quadtrac structural study.

The worldwide metric sheet controls the visible 715/30-inch envelope.  The
North American brochure separately controls the HDS and Category 4N subsystem
cues.  Their combination is a study freeze, not a dealer-order claim.  Hidden
geometry and all motion remain independently reconstructed.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()

spec = importlib.util.spec_from_file_location("exo_fleet_builder_steiger715", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load shared fleet builder: {SHARED_GENERATOR}")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)


class Steiger715Builder(shared.FleetBuilder):
    WHEELBASE_M = 3.912
    BELT_WIDTH_M = 0.762
    TRACK_LENGTH_M = 2.34
    TRACK_HEIGHT_M = 1.14
    TRACK_CENTER_Z_M = 1.1175
    AXLE_X_M = WHEELBASE_M / 2
    HDS_TOTAL_M = 0.1778
    HDS_UP_M = 0.0762
    HDS_DOWN_M = 0.1016

    def write_machine_wrapper(self):
        """Preserve this checked-in machine-local builder."""

    def required_semantics(self):
        names = list(super().required_semantics())
        names.extend([
            "Front_Frame_Oscillation_Pivot", "Rear_Hitch_Pivot", "Rear_Hitch_ROOT",
            "HDS_FL_ROOT", "HDS_FR_ROOT", "HDS_RL_ROOT", "HDS_RR_ROOT",
            "Track_FL_Drive_Pivot", "Track_FR_Drive_Pivot",
            "Track_RL_Drive_Pivot", "Track_RR_Drive_Pivot",
        ])
        return list(dict.fromkeys(names))

    @staticmethod
    def _descendants(root):
        return list(root.children_recursive)

    @staticmethod
    def _world_location(obj):
        point = obj.matrix_world.translation
        return [float(point.x), float(point.y), float(point.z)]

    @staticmethod
    def _mesh_bounds(obj):
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        return (
            [min(float(point[axis]) for point in points) for axis in range(3)],
            [max(float(point[axis]) for point in points) for axis in range(3)],
        )

    def _scene_min_y(self):
        bpy.context.view_layer.update()
        minimum = math.inf
        for obj in self.public_objects():
            if obj.type != "MESH":
                continue
            low, _ = self._mesh_bounds(obj)
            minimum = min(minimum, low[1])
        return minimum

    def _add_hds_track(self, prefix, center, parent):
        hds = self.empty(f"HDS_{prefix}_ROOT", center, parent, role="hds_suspension_root")
        self.box(f"HDS_{prefix}_Upper_Carrier", (0, 1.18, 0), (1.18, 0.20, 0.46),
                 self.materials["graphite"], hds, role="hds_upper_carrier", bevel=0.045)
        axis_a = self.empty(f"HDS_{prefix}_Axis_A_Pivot", (0, 1.05, 0), hds,
                            role="hds_first_axis")
        self.pipe_between(f"HDS_{prefix}_Axis_A_Link_L", (-0.43, 0, -0.20),
                          (-0.25, -0.54, -0.20), 0.055, self.materials["steel"], axis_a,
                          role="hds_double_axis_link")
        self.pipe_between(f"HDS_{prefix}_Axis_A_Link_R", (-0.43, 0, 0.20),
                          (-0.25, -0.54, 0.20), 0.055, self.materials["steel"], axis_a,
                          role="hds_double_axis_link")
        axis_b = self.empty(f"HDS_{prefix}_Axis_B_Pivot", (0, -1.05, 0), axis_a,
                            role="hds_second_axis")
        self.pipe_between(f"HDS_{prefix}_Axis_B_Link_L", (-0.25, 0.51, -0.20),
                          (0.38, 0.78, -0.20), 0.050, self.materials["rod"], axis_b,
                          role="hds_double_axis_link")
        self.pipe_between(f"HDS_{prefix}_Axis_B_Link_R", (-0.25, 0.51, 0.20),
                          (0.38, 0.78, 0.20), 0.050, self.materials["rod"], axis_b,
                          role="hds_double_axis_link")
        self.cylinder(f"HDS_{prefix}_Hydraulic_Cue", (0.34, 0.83, 0), 0.075, 0.56,
                      self.materials["graphite"], axis_b, vertices=20,
                      rotation=(math.pi / 2, 0, 0), role="hds_hydraulic_cue")

        root = self.empty(f"Track_{prefix}_ROOT", parent=axis_b,
                          role="independent_track_module_pivot")
        half_l = self.TRACK_LENGTH_M / 2
        half_h = self.TRACK_HEIGHT_M / 2
        pad_length = 0.18
        pad_depth = 0.055
        for surface, y in (("Bottom", pad_depth / 2),
                           ("Top", self.TRACK_HEIGHT_M - pad_depth / 2)):
            for index in range(12):
                x = -half_l + pad_length / 2 + index * ((self.TRACK_LENGTH_M - pad_length) / 11)
                self.box(f"Track_{prefix}_Pad_{surface}_{index + 1:02d}", (x, y, 0),
                         (pad_length, pad_depth, self.BELT_WIDTH_M), self.materials["rubber"],
                         root, role="track_pad", bevel=0.010)
        for end, x in (("Rear", -half_l + pad_depth / 2),
                       ("Front", half_l - pad_depth / 2)):
            for index in range(6):
                y = 0.15 + index * ((self.TRACK_HEIGHT_M - 0.30) / 5)
                self.box(f"Track_{prefix}_Pad_{end}_{index + 1:02d}", (x, y, 0),
                         (pad_depth, 0.18, self.BELT_WIDTH_M), self.materials["rubber"],
                         root, role="track_pad", bevel=0.010)

        for label, x in (("Idler", -0.77),):
            self.cylinder(f"Track_{prefix}_{label}", (x, half_h, 0), 0.43,
                          self.BELT_WIDTH_M * 0.72, self.materials["steel"], root,
                          vertices=28, role="track_wheel")
        drive = self.empty(f"Track_{prefix}_Drive_Pivot", (0.77, half_h, 0), root,
                           role="positive_drive_wheel_root")
        self.cylinder(f"Track_{prefix}_Drive_Wheel", (0, 0, 0), 0.43,
                      self.BELT_WIDTH_M * 0.72, self.materials["steel"], drive,
                      vertices=28, role="positive_drive_wheel")
        for index in range(8):
            angle = math.tau * index / 8
            self.box(f"Track_{prefix}_Drive_Lug_{index + 1:02d}",
                     (math.cos(angle) * 0.34, math.sin(angle) * 0.34, 0),
                     (0.11, 0.055, self.BELT_WIDTH_M * 0.76), self.materials["graphite"],
                     drive, rotation=(0, 0, angle), role="positive_drive_lug", bevel=0.008)
        for index in range(5):
            x = -0.48 + index * 0.24
            self.cylinder(f"Track_{prefix}_Midroller_{index + 1:02d}", (x, 0.28, 0),
                          0.18, self.BELT_WIDTH_M * 0.64, self.materials["graphite"], root,
                          vertices=20, role="track_midroller")
        self.box(f"Track_{prefix}_Undercarriage_Frame", (0, 0.70, 0),
                 (1.68, 0.20, 0.48), self.materials["graphite"], root,
                 role="track_undercarriage", bevel=0.045)
        return hds, root

    def _add_machine_structure(self):
        rear = self.empty("Rear_Frame_ROOT", parent=self.fixed_root, role="rear_frame_motion_root")
        roll = self.empty("Front_Frame_Oscillation_Pivot", (0, 1.30, 0), rear,
                          role="front_frame_oscillation_pivot")
        yaw = self.empty("Chassis_Yaw_Pivot", parent=roll, role="chassis_articulation_pivot")
        front = self.empty("Front_Frame_ROOT", (0, -1.30, 0), yaw,
                           role="front_frame_motion_root")

        self.box("Rear_Main_Frame", (-1.18, 1.36, 0), (2.75, 0.36, 1.24),
                 self.materials["graphite"], rear, role="rear_chassis", bevel=0.075)
        self.box("Front_Main_Frame", (1.48, 1.34, 0), (3.20, 0.38, 1.22),
                 self.materials["graphite"], front, role="front_chassis", bevel=0.075)
        for side, z in (("L", -0.46), ("R", 0.46)):
            self.box(f"Rear_Articulation_Yoke_{side}", (-0.14, 1.30, z),
                     (0.62, 0.34, 0.22), self.materials["steel"], rear,
                     role="articulation_yoke", bevel=0.035)
        self.box("Front_Articulation_Tongue", (0.12, 1.30, 0), (0.56, 0.30, 0.70),
                 self.materials["steel"], front, role="articulation_tongue", bevel=0.04)
        self.cylinder("Articulation_Vertical_Pin", (0, 1.30, 0), 0.11, 0.76,
                      self.materials["rod"], rear, vertices=28,
                      rotation=(math.pi / 2, 0, 0), role="articulation_pin")
        self.cylinder("Oscillation_Longitudinal_Bearing", (0, 1.30, 0), 0.16, 0.52,
                      self.materials["graphite"], rear, vertices=28,
                      rotation=(0, math.pi / 2, 0), role="oscillation_bearing")
        for side, z in (("L", -0.54), ("R", 0.54)):
            self.pipe_between(f"Steering_{side}_Cylinder", (-0.50, 1.13, z),
                              (0.50, 1.17, z), 0.055, self.materials["steel"], rear,
                              role="articulation_hydraulic")

        self.side_profile("Steiger_715_Engine_Hood",
                          [(0.55, 1.48), (3.82, 1.48), (4.02, 1.78),
                           (3.70, 2.74), (0.88, 2.76), (0.55, 2.43)],
                          1.66, self.materials["body"], front, role="engine_house")
        self.box("Front_Nose_End_Plate", (4.05, 1.60, 0), (0.19, 0.40, 1.18),
                 self.materials["body_dark"], front, role="front_end_structure", bevel=0.025)
        for index in range(12):
            self.box(f"Cooling_Louver_{index + 1:02d}", (3.40 - index * 0.12, 2.18, -0.842),
                     (0.07, 0.62, 0.022), self.materials["graphite"], front,
                     role="cooling_louver", bevel=0.003)
        self.cylinder("Exhaust_Stack", (0.98, 3.15, 0.62), 0.085, 0.88,
                      self.materials["graphite"], front, vertices=22,
                      rotation=(math.pi / 2, 0, 0), role="exhaust")

        self.add_cab(-1.05, 1.48, 1.96, 2.05, 2.438, rear)
        self.box("Cab_Sun_Visor", (-0.20, 3.54, -1.04), (0.54, 0.09, 0.12),
                 self.materials["body_dark"], rear, role="cab_detail", bevel=0.012)
        for index in range(4):
            self.box(f"Access_Step_{index + 1:02d}", (-0.80 + index * 0.05, 0.70 + index * 0.19, -1.02),
                     (0.42, 0.055, 0.36), self.materials["steel"], rear,
                     role="access_step", bevel=0.008)
        self.pipe_between("Cab_Left_Handrail", (-1.16, 1.30, -1.12),
                          (-0.64, 2.28, -1.12), 0.026, self.materials["steel"], rear,
                          role="handrail")

        for axle, frame, x in (("F", front, self.AXLE_X_M), ("R", rear, -self.AXLE_X_M)):
            for side, z in (("L", -self.TRACK_CENTER_Z_M), ("R", self.TRACK_CENTER_Z_M)):
                self._add_hds_track(f"{axle}{side}", (x, 0, z), frame)
        self.box("Running_Gear_Center_Bearing", (0, 0.92, 0), (0.44, 0.22, 0.62),
                 self.materials["graphite"], self.running_root,
                 role="running_gear_interface", bevel=0.045)

        hitch = self.empty("Rear_Hitch_Pivot", (-3.23, 0.94, 0), rear,
                           role="category_4n_hitch_pivot")
        hitch_root = self.empty("Rear_Hitch_ROOT", parent=hitch, role="category_4n_hitch_root")
        for side, z in (("L", -0.36), ("R", 0.36)):
            self.pipe_between(f"Category4N_{side}_Lower_Link", (0, 0, z),
                              (-0.67, -0.17, z), 0.050, self.materials["steel"], hitch_root,
                              role="category_4n_lower_link")
            self.pipe_between(f"Category4N_{side}_Lift_Rod", (-0.08, 0.34, z),
                              (-0.45, -0.05, z), 0.033, self.materials["rod"], hitch_root,
                              role="hitch_lift_rod")
            self.cylinder(f"Category4N_{side}_Ball_End", (-0.69, -0.18, z), 0.070, 0.10,
                          self.materials["graphite"], hitch_root, vertices=24,
                          role="hitch_ball_end")
        self.pipe_between("Category4N_Top_Link", (-0.02, 0.46, 0), (-0.58, 0.12, 0),
                          0.043, self.materials["steel"], hitch_root,
                          role="category_4n_top_link")
        self.box("Category4N_Rockshaft", (-0.02, 0.42, 0), (0.22, 0.20, 1.05),
                 self.materials["graphite"], hitch_root, role="hitch_rockshaft", bevel=0.035)

        drawbar = self.empty("Drawbar_Pivot", (-3.55, 0.55, 0), rear, role="drawbar_yaw_pivot")
        self.box("Category4_Drawbar", (-0.2975, 0, 0), (0.595, 0.16, 0.24),
                 self.materials["steel"], drawbar, role="category_4_drawbar", bevel=0.025)
        self.cylinder("Drawbar_Pin", (-0.54, 0.10, 0), 0.055, 0.20,
                      self.materials["rod"], drawbar, vertices=24,
                      rotation=(math.pi / 2, 0, 0), role="drawbar_pin")
        self.box("Hydraulic_Valve_Block", (-2.78, 1.42, 0), (0.42, 0.24, 0.58),
                 self.materials["steel"], self.hydraulics_root,
                 role="hydraulic_valve_block", bevel=0.035)
        for side, z in (("L", -0.22), ("R", 0.22)):
            self.pipe_between(f"Rear_Hydraulic_Hose_{side}", (-2.78, 1.42, z),
                              (-3.28, 1.15, z), 0.022, self.materials["rubber"],
                              self.hydraulics_root, role="hydraulic_hose")

    def build_model(self):
        self.build_common_roots()
        self._add_machine_structure()
        missing = [name for name in self.required_semantics() if bpy.data.objects.get(name) is None]
        if missing:
            raise RuntimeError(f"Steiger 715 builder omitted semantic nodes: {', '.join(missing)}")
        return self.root

    def _pose_nodes(self):
        return [
            "Front_Frame_Oscillation_Pivot", "Chassis_Yaw_Pivot",
            "Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT",
            "HDS_FL_ROOT", "HDS_FR_ROOT", "HDS_RL_ROOT", "HDS_RR_ROOT",
            "Rear_Hitch_Pivot", "Drawbar_Pivot",
            "Track_FL_Drive_Pivot", "Track_FR_Drive_Pivot",
            "Track_RL_Drive_Pivot", "Track_RR_Drive_Pivot",
        ]

    def _capture_pose(self):
        return {name: (bpy.data.objects[name].location.copy(),
                       bpy.data.objects[name].rotation_euler.copy()) for name in self._pose_nodes()}

    @staticmethod
    def _restore_pose(pose):
        for name, (location, rotation) in pose.items():
            bpy.data.objects[name].location = location
            bpy.data.objects[name].rotation_euler = rotation
        bpy.context.view_layer.update()

    def render_views(self):
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        neutral = self._capture_pose()
        views = [
            ("operator-side", (0.8, 3.0, -12.5), (0, 1.75, 0), 9.2, "hds"),
            ("front-three-quarter", (10.5, 6.8, -9.0), (0.4, 1.75, 0), 9.7, "yaw_right"),
            ("rear-three-quarter", (-10.0, 6.2, 8.4), (-1.0, 1.55, 0), 9.6, "hitch"),
            ("elevated-technical", (9.0, 12.8, -10.8), (0, 1.45, 0), 11.2, "yaw_left"),
            ("articulation-detail", (5.4, 3.1, -5.1), (0, 1.18, 0), 5.8, "articulation"),
            ("right-side", (0.5, 3.0, 12.5), (0, 1.70, 0), 9.2, "drive"),
        ]
        paths = []
        try:
            for label, location, target, scale, pose_name in views:
                self._restore_pose(neutral)
                if pose_name == "hds":
                    bpy.data.objects["HDS_FL_ROOT"].location.y += 0.035
                    bpy.data.objects["HDS_RR_ROOT"].location.y += 0.035
                elif pose_name == "yaw_right":
                    bpy.data.objects["Chassis_Yaw_Pivot"].rotation_euler.y = 0.11
                elif pose_name == "yaw_left":
                    bpy.data.objects["Chassis_Yaw_Pivot"].rotation_euler.y = -0.10
                elif pose_name == "hitch":
                    bpy.data.objects["Rear_Hitch_Pivot"].rotation_euler.z = 0.12
                    bpy.data.objects["Drawbar_Pivot"].rotation_euler.y = -0.06
                elif pose_name == "articulation":
                    bpy.data.objects["Chassis_Yaw_Pivot"].rotation_euler.y = 0.12
                    bpy.data.objects["HDS_FL_ROOT"].location.y += 0.045
                    bpy.data.objects["Track_FL_ROOT"].rotation_euler.z = 0.012
                elif pose_name == "drive":
                    for name in ("Track_FL_Drive_Pivot", "Track_FR_Drive_Pivot",
                                 "Track_RL_Drive_Pivot", "Track_RR_Drive_Pivot"):
                        bpy.data.objects[name].rotation_euler.z = 0.38
                bpy.context.view_layer.update()
                camera.location = location
                self.point_at(camera, target)
                camera.data.ortho_scale = scale
                path = self.render_dir / f"{self.machine_id}-{label}.png"
                bpy.context.scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True)
                paths.append(path)
        finally:
            self._restore_pose(neutral)
        return paths

    @staticmethod
    def _sine(cycle, phase=0.0):
        return 0.5 - 0.5 * math.cos(((cycle + phase) % 1.0) * math.tau)

    def _sample_autoplay(self):
        neutral = self._capture_pose()
        minimum_y = math.inf
        minimum_track_spacing = math.inf
        samples = 73
        try:
            for index in range(samples):
                cycle = index / (samples - 1)
                bpy.data.objects["Chassis_Yaw_Pivot"].rotation_euler.y = -0.12 + 0.24 * self._sine(cycle)
                bpy.data.objects["Front_Frame_Oscillation_Pivot"].rotation_euler.x = -0.0002 + 0.0004 * self._sine(cycle, 0.12)
                for name in ("Track_FL_ROOT", "Track_RL_ROOT"):
                    bpy.data.objects[name].rotation_euler.z = -0.0005 + 0.001 * self._sine(cycle, 0.18)
                for name in ("Track_FR_ROOT", "Track_RR_ROOT"):
                    bpy.data.objects[name].rotation_euler.z = 0.0005 - 0.001 * self._sine(cycle, 0.68)
                lift = 0.018 * self._sine(cycle, 0.32)
                for name in ("HDS_FL_ROOT", "HDS_FR_ROOT", "HDS_RL_ROOT", "HDS_RR_ROOT"):
                    bpy.data.objects[name].location.y = neutral[name][0].y + lift
                bpy.data.objects["Rear_Hitch_Pivot"].rotation_euler.z = -0.06 + 0.14 * self._sine(cycle, 0.44)
                bpy.data.objects["Drawbar_Pivot"].rotation_euler.y = -0.08 + 0.16 * self._sine(cycle, 0.50)
                bpy.context.view_layer.update()
                minimum_y = min(minimum_y, self._scene_min_y())
                fronts = [self._world_location(bpy.data.objects[name]) for name in ("Track_FL_ROOT", "Track_FR_ROOT")]
                rears = [self._world_location(bpy.data.objects[name]) for name in ("Track_RL_ROOT", "Track_RR_ROOT")]
                minimum_track_spacing = min(minimum_track_spacing, *[
                    math.hypot(front[0] - rear[0], front[2] - rear[2])
                    for front in fronts for rear in rears
                ])
        finally:
            self._restore_pose(neutral)
        return {
            "duration_seconds": 18,
            "sample_count": samples,
            "sample_interval_seconds": 0.25,
            "minimum_public_y_m": round(minimum_y, 6),
            "minimum_front_rear_track_center_separation_xz_m": round(minimum_track_spacing, 6),
            "boundary": "Discrete sampling of the exact viewer target ranges; not continuous collision detection, terrain response, belt deformation, suspension loading or a safety limit.",
        }

    def machine_specific_validation_gates(self, contract):
        statuses = []
        object_names = set(bpy.data.objects.keys())
        track_roots = [bpy.data.objects[f"Track_{name}_ROOT"] for name in ("FL", "FR", "RL", "RR")]
        centers = {obj.name: self._world_location(obj) for obj in track_roots}
        front_wheelbase = abs(centers["Track_FL_ROOT"][0] - centers["Track_RL_ROOT"][0])
        rear_wheelbase = abs(centers["Track_FR_ROOT"][0] - centers["Track_RR_ROOT"][0])
        belt_low, belt_high = self._mesh_bounds(bpy.data.objects["Track_FL_Pad_Bottom_01"])
        belt_width = belt_high[2] - belt_low[2]
        contacts = []
        for name in ("FL", "FR", "RL", "RR"):
            lows = [self._mesh_bounds(obj)[0][1] for obj in self._descendants(bpy.data.objects[f"Track_{name}_ROOT"])
                    if obj.type == "MESH" and obj.name.startswith(f"Track_{name}_Pad_Bottom_")]
            contacts.append({"track": name, "minimum_bottom_pad_y_m": round(min(lows), 6)})
        pads = sorted(name for name in object_names if "_Pad_" in name and name.startswith("Track_"))
        hds_links = sorted(name for name in object_names if "Axis_" in name and "Link_" in name)
        hitch_links = sorted(name for name in object_names if name.startswith("Category4N_") and "Link" in name)
        autoplay = self._sample_autoplay()
        sizes = contract["bounds"]["size_m"]

        methods = {
            "frozen_visible_configuration": "Compare the exact configuration identity, GLB bounds, belt width and selected HDS / Category 4N component census with the two explicitly separated market-source roles.",
            "single_identity_root": "Inspect the exported root contract and traverse all four track, HDS, hitch and chassis branches from Machine_Root.",
            "four_track_contact": "Measure every bottom-pad world AABB in the neutral pose and the exact four track-root centers.",
            "chassis_articulation_continuity": "Inspect the rear-frame -> oscillation -> yaw -> front-frame hierarchy and measure the two 3.912 m track-center wheelbases.",
            "track_module_and_HDS_clearance": "Count four independent track roots and the visible two-axis HDS link sets, then sample their exact viewer ranges for ground clearance.",
            "belt_phase_continuity": "Count and compare closed visible pad loops plus four independently rooted positive-drive wheels; belt deformation is deliberately not solved.",
            "rear_hitch_clearance": "Traverse the Category 4N hitch root and count paired lower links, top link, lift rods and ball-end cues.",
            "ground_collision": "Sample all public mesh AABBs at 0.25-second intervals across the exact 18-second Auto target path.",
            "self_collision": "Sample front-to-rear track-center separation across the declared yaw path and compare it with the reconstructed pod length.",
            "swept_volume_collision": "Record the exact phased target-path sample count, ground minimum and track separation while preserving the solver boundary.",
        }
        semantics = {
            "frozen_visible_configuration": ["Front_Nose_End_Plate", "Track_FL_ROOT", "HDS_FL_ROOT", "Rear_Hitch_ROOT"],
            "single_identity_root": ["Machine_Root", "Front_Frame_ROOT", "Rear_Frame_ROOT"],
            "four_track_contact": ["Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT"],
            "chassis_articulation_continuity": ["Front_Frame_Oscillation_Pivot", "Chassis_Yaw_Pivot", "Front_Frame_ROOT", "Rear_Frame_ROOT"],
            "track_module_and_HDS_clearance": ["HDS_FL_ROOT", "HDS_FR_ROOT", "HDS_RL_ROOT", "HDS_RR_ROOT", "Track_FL_ROOT"],
            "belt_phase_continuity": ["Track_FL_Pad_Bottom_01", "Track_FL_Drive_Pivot", "Track_FR_Drive_Pivot", "Track_RL_Drive_Pivot", "Track_RR_Drive_Pivot"],
            "rear_hitch_clearance": ["Rear_Hitch_Pivot", "Rear_Hitch_ROOT", "Category4N_Top_Link", "Category4N_L_Lower_Link", "Category4N_R_Lower_Link"],
            "ground_collision": ["Track_FL_Pad_Bottom_01", "Track_FR_Pad_Bottom_01", "Track_RL_Pad_Bottom_01", "Track_RR_Pad_Bottom_01"],
            "self_collision": ["Chassis_Yaw_Pivot", "Track_FL_ROOT", "Track_FR_ROOT", "Track_RL_ROOT", "Track_RR_ROOT"],
            "swept_volume_collision": ["Chassis_Yaw_Pivot", "Front_Frame_Oscillation_Pivot", "HDS_FL_ROOT", "Rear_Hitch_Pivot"],
        }
        facts = {
            "frozen_visible_configuration": ["public-envelope-x", "public-envelope-y", "public-envelope-z", "selected-track-width", "quadtrac-topology", "hds-total-travel", "hitch-category"],
            "single_identity_root": ["quadtrac-topology"],
            "four_track_contact": ["quadtrac-topology", "selected-track-width"],
            "chassis_articulation_continuity": ["wheelbase", "quadtrac-topology"],
            "track_module_and_HDS_clearance": ["hds-total-travel", "hds-up-travel", "hds-down-travel"],
            "belt_phase_continuity": ["selected-track-width", "quadtrac-topology"],
            "rear_hitch_clearance": ["hitch-category", "hitch-lift-capacity"],
            "ground_collision": ["public-envelope-y", "selected-track-width"],
            "self_collision": ["wheelbase", "public-envelope-z"],
            "swept_volume_collision": ["wheelbase", "hds-total-travel"],
        }

        def gate(gate_id, ok, evidence):
            statuses.append({
                "id": gate_id,
                "status": "PASS" if ok else "FAIL",
                "detail": {
                    "method": methods[gate_id],
                    "evidence": evidence,
                    "semantic_nodes": semantics[gate_id],
                    "fact_ids": facts[gate_id],
                },
            })

        gate("frozen_visible_configuration",
             self.configuration_id == "CASEIH-STEIGER715-XMARKET-30IN-HDS-CAT4N-STUDY-CANDIDATE"
             and all(abs(actual - expected) <= 0.003 for actual, expected in zip(sizes, (8.29, 3.918, 2.997)))
             and abs(belt_width - self.BELT_WIDTH_M) <= 0.001,
             {"configuration_id": self.configuration_id, "measured_glb_xyz_m": sizes,
              "published_visible_xyz_m": [8.29, 3.918, 2.997], "measured_belt_width_m": round(belt_width, 6),
              "published_belt_width_m": self.BELT_WIDTH_M,
              "applicability": "Worldwide 715/30-inch envelope with separately sourced North American HDS and Category 4N subsystem cues; no dealer-order claim."})
        gate("single_identity_root", contract["scene_root_count"] == 1 and contract["root_name"] == "Machine_Root",
             {"scene_root_count": contract["scene_root_count"], "identity_root": contract["root_name"],
              "tracked_branches": [obj.name for obj in track_roots]})
        gate("four_track_contact", len(contacts) == 4 and all(abs(item["minimum_bottom_pad_y_m"]) <= 0.002 for item in contacts),
             {"track_count": len(track_roots), "neutral_contacts": contacts, "contact_tolerance_m": 0.002})
        articulation_ok = (bpy.data.objects["Chassis_Yaw_Pivot"].parent == bpy.data.objects["Front_Frame_Oscillation_Pivot"]
                           and bpy.data.objects["Front_Frame_ROOT"].parent == bpy.data.objects["Chassis_Yaw_Pivot"]
                           and abs(front_wheelbase - self.WHEELBASE_M) <= 0.001
                           and abs(rear_wheelbase - self.WHEELBASE_M) <= 0.001)
        gate("chassis_articulation_continuity", articulation_ok,
             {"hierarchy": ["Rear_Frame_ROOT", "Front_Frame_Oscillation_Pivot", "Chassis_Yaw_Pivot", "Front_Frame_ROOT"],
              "left_wheelbase_m": round(front_wheelbase, 6), "right_wheelbase_m": round(rear_wheelbase, 6),
              "published_wheelbase_m": self.WHEELBASE_M})
        gate("track_module_and_HDS_clearance", len(hds_links) == 16 and autoplay["minimum_public_y_m"] >= -0.002,
             {"hds_root_count": 4, "visible_double_axis_link_meshes": len(hds_links),
              "published_travel_m": {"total": self.HDS_TOTAL_M, "up": self.HDS_UP_M, "down": self.HDS_DOWN_M},
              "viewer_cue_travel_m": 0.018, "sampled_auto_path": autoplay})
        per_track_pads = {name: len([pad for pad in pads if pad.startswith(f"Track_{name}_")]) for name in ("FL", "FR", "RL", "RR")}
        gate("belt_phase_continuity", len(pads) == 144 and len(set(per_track_pads.values())) == 1,
             {"total_visible_pad_meshes": len(pads), "per_track_pad_meshes": per_track_pads,
              "positive_drive_roots": [f"Track_{name}_Drive_Pivot" for name in ("FL", "FR", "RL", "RR")],
              "boundary": "Pad-loop and drive-root continuity only; no belt deformation, slip or traction solver."})
        gate("rear_hitch_clearance", len(hitch_links) == 3,
             {"category": "4N", "counted_primary_links": hitch_links,
              "lift_rod_count": len([name for name in object_names if name.endswith("Lift_Rod")]),
              "ball_end_count": len([name for name in object_names if name.endswith("Ball_End")])})
        gate("ground_collision", autoplay["minimum_public_y_m"] >= -0.002,
             {"neutral_minimum_y_m": contract["bounds"]["min_m"][1], "sampled_auto_path": autoplay,
              "tolerance_m": -0.002})
        separation_ok = autoplay["minimum_front_rear_track_center_separation_xz_m"] > self.TRACK_LENGTH_M + 0.30
        gate("self_collision", separation_ok,
             {"sampled_auto_path": autoplay, "reconstructed_track_length_m": self.TRACK_LENGTH_M,
              "required_center_separation_m": self.TRACK_LENGTH_M + 0.30})
        gate("swept_volume_collision", separation_ok and autoplay["minimum_public_y_m"] >= -0.002,
             {"sampled_auto_path": autoplay, "continuous_solver": False,
              "scope": "Declared viewer target-path ground and major front/rear track separation only."})
        return statuses


if __name__ == "__main__":
    Steiger715Builder(shared.load_design(DESIGN), DESIGN, OUTPUT_DIR).run()

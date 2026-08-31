#!/usr/bin/env python3
"""Build the neutral Trident 5550 liquid-applicator structural study.

The folded carrier remains inside the published transport envelope.  Three
nested stages per side encode a reconstructed section-length arithmetic study
that totals the published 36.5 m working span.  It is not manufacturer CAD,
spray guidance, a hydraulic solver, or an operating-limit model.
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

spec = importlib.util.spec_from_file_location("exo_fleet_builder_trident5550", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load shared fleet builder: {SHARED_GENERATOR}")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)


class Trident5550Builder(shared.FleetBuilder):
    WHEELBASE_M = 4.32
    TIRE_RADIUS_M = 1.00
    TIRE_WIDTH_M = 0.46
    TIRE_CENTER_Z_M = 1.875
    FRONT_X_M = WHEELBASE_M / 2
    REAR_X_M = -WHEELBASE_M / 2
    TANK_RADIUS_M = 1.05
    TANK_LENGTH_M = 1.75
    TANK_CAPACITY_M3 = 1600 * 0.003785411784
    BOOM_CENTER_M = 3.5
    BOOM_INNER_M = 6.0
    BOOM_MID_M = 5.6
    BOOM_TIP_M = 4.9
    BOOM_SPAN_M = BOOM_CENTER_M + 2 * (BOOM_INNER_M + BOOM_MID_M + BOOM_TIP_M)

    def write_machine_wrapper(self):
        """Preserve this checked-in machine-local builder."""

    def required_semantics(self):
        names = list(super().required_semantics())
        names.extend([
            "Rear_Axle_ROOT", "Front_L_Suspension_ROOT", "Front_R_Suspension_ROOT",
            "Rear_L_Suspension_ROOT", "Rear_R_Suspension_ROOT",
            "Front_L_Steering_Pivot", "Front_R_Steering_Pivot",
            "Rear_L_Steering_Pivot", "Rear_R_Steering_Pivot",
            "Boom_Center_Lift_ROOT", "Boom_Center_Roll_Pivot",
            "Boom_L_Mid_Fold_Pivot", "Boom_L_Mid_ROOT", "Boom_L_Tip_Fold_Pivot", "Boom_L_Tip_ROOT",
            "Boom_R_Mid_Fold_Pivot", "Boom_R_Mid_ROOT", "Boom_R_Tip_Fold_Pivot", "Boom_R_Tip_ROOT",
            "Solution_Pump_ROOT", "Nozzle_Valve_Pulse_ROOT",
        ])
        return list(dict.fromkeys(names))

    @staticmethod
    def _descendants(root):
        return list(root.children_recursive)

    @staticmethod
    def _mesh_bounds(obj):
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        return (
            [min(float(point[axis]) for point in points) for axis in range(3)],
            [max(float(point[axis]) for point in points) for axis in range(3)],
        )

    @staticmethod
    def _world_location(obj):
        point = obj.matrix_world.translation
        return [float(point.x), float(point.y), float(point.z)]

    @staticmethod
    def _aabb_intersects(first, second, tolerance=0.003):
        return all(min(first[1][axis], second[1][axis]) - max(first[0][axis], second[0][axis]) > tolerance
                   for axis in range(3))

    def _scene_min_y(self):
        bpy.context.view_layer.update()
        lows = [self._mesh_bounds(obj)[0][1] for obj in self.public_objects() if obj.type == "MESH"]
        return min(lows)

    def _add_suspension_corner(self, axle_root, axle, side, sign):
        suspension = self.empty(f"{axle}_{side}_Suspension_ROOT",
                                (0, 0, sign * self.TIRE_CENTER_Z_M), axle_root,
                                role="load_compensating_suspension_root")
        self.box(f"{axle}_{side}_Axle_Slide", (0, 0.32, -sign * 0.62),
                 (0.30, 0.18, 1.34), self.materials["steel"], suspension,
                 role="adjustable_axle_slide", bevel=0.018)
        for index, x in enumerate((-0.14, 0.14), 1):
            self.cylinder(f"{axle}_{side}_Suspension_Barrel_{index}", (x, 0.52, 0),
                          0.075, 0.68, self.materials["graphite"], suspension,
                          vertices=20, rotation=(math.pi / 2, 0, 0),
                          role="load_compensating_strut")
            self.cylinder(f"{axle}_{side}_Suspension_Rod_{index}", (x, 0.82, 0),
                          0.040, 0.48, self.materials["rod"], suspension,
                          vertices=16, rotation=(math.pi / 2, 0, 0),
                          role="suspension_rod")
        steering = self.empty(f"{axle}_{side}_Steering_Pivot", parent=suspension,
                              role="four_wheel_steering_pivot")
        self.box(f"{axle}_{side}_Steering_Knuckle", (0, 0.18, -sign * 0.12),
                 (0.25, 0.40, 0.18), self.materials["graphite"], steering,
                 role="steering_knuckle", bevel=0.025)
        self.add_wheel(f"{axle}_{side}", (0, 0, 0), self.TIRE_RADIUS_M,
                       self.TIRE_WIDTH_M, steering, tread_count=18)
        return suspension

    def _add_running_gear(self):
        front_pivot = self.empty("Front_Axle_Oscillation_Pivot",
                                 (self.FRONT_X_M, self.TIRE_RADIUS_M, 0),
                                 self.running_root, role="front_axle_oscillation_root")
        front = self.empty("Front_Axle_ROOT", parent=front_pivot, role="front_axle_root")
        self.box("Front_Adjustable_Axle_Beam", (0, 0.30, 0), (0.34, 0.22, 3.38),
                 self.materials["graphite"], front, role="front_axle_beam", bevel=0.025)
        rear = self.empty("Rear_Axle_ROOT", (self.REAR_X_M, self.TIRE_RADIUS_M, 0),
                          self.running_root, role="rear_axle_root")
        self.box("Rear_Adjustable_Axle_Beam", (0, 0.30, 0), (0.34, 0.22, 3.38),
                 self.materials["graphite"], rear, role="rear_axle_beam", bevel=0.025)
        for axle, root in (("Front", front), ("Rear", rear)):
            for side, sign in (("L", -1), ("R", 1)):
                self._add_suspension_corner(root, axle, side, sign)
            self.pipe_between(f"{axle}_Steering_Tie_Rod", (-0.12, 0.20, -1.68),
                              (-0.12, 0.20, 1.68), 0.032, self.materials["rod"], root,
                              role="steering_tie_rod")
            for side, sign in (("L", -1), ("R", 1)):
                self.pipe_between(f"{axle}_{side}_Steering_Cylinder", (-0.15, 0.28, sign * 0.45),
                                  (-0.15, 0.28, sign * 1.56), 0.046,
                                  self.materials["steel"], root, role="steering_cylinder")

    def _add_carrier(self):
        self.box("High_Clearance_Frame", (0, 1.62, 0), (7.30, 0.24, 1.45),
                 self.materials["graphite"], self.fixed_root, role="high_clearance_chassis", bevel=0.03)
        for x in (self.FRONT_X_M, self.REAR_X_M):
            for side, sign in (("L", -1), ("R", 1)):
                self.pipe_between(f"Frame_Leg_{'Front' if x > 0 else 'Rear'}_{side}",
                                  (x, 1.54, sign * 0.58), (x, 1.94, sign * self.TIRE_CENTER_Z_M),
                                  0.075, self.materials["steel"], self.fixed_root,
                                  role="high_clearance_frame_leg")
        self.box("Front_End_Structure", (4.80, 1.76, 0), (0.12, 0.52, 1.32),
                 self.materials["graphite"], self.fixed_root, role="carrier_end_structure", bevel=0.015)
        self.box("Rear_End_Structure", (-4.80, 1.78, 0), (0.12, 0.56, 1.30),
                 self.materials["graphite"], self.fixed_root, role="carrier_end_structure", bevel=0.015)
        self.box("Engine_House", (1.36, 2.35, 0), (1.92, 1.25, 1.62),
                 self.materials["body_dark"], self.fixed_root, role="engine_house", bevel=0.06)
        for index in range(9):
            self.box(f"Engine_Vent_{index + 1:02d}", (1.02 + index * 0.13, 2.42, -0.822),
                     (0.075, 0.64, 0.026), self.materials["graphite"], self.fixed_root,
                     role="cooling_vent", bevel=0.004)

        self.add_cab(3.34, 1.48, 2.02, 2.00, 2.53, self.fixed_root)
        self.box("Cab_Front_Visibility_Brow", (4.31, 3.58, 0), (0.16, 0.10, 1.82),
                 self.materials["body"], self.fixed_root, role="cab_detail", bevel=0.012)
        for index in range(4):
            self.box(f"Cab_Access_Step_{index + 1:02d}", (2.45, 0.68 + index * 0.20, -1.02),
                     (0.44, 0.055, 0.36), self.materials["steel"], self.detail_root,
                     role="access_step", bevel=0.008)

        self.cylinder("Solution_Tank_1600gal_Exterior", (-0.52, 2.60, 0),
                      self.TANK_RADIUS_M, self.TANK_LENGTH_M, self.materials["steel"],
                      self.fixed_root, vertices=48, rotation=(0, math.pi / 2, 0),
                      role="solution_tank")
        self.cylinder("Solution_Tank_Fill_Lid", (-0.52, 3.69, 0), 0.23, 0.10,
                      self.materials["graphite"], self.fixed_root, vertices=24,
                      role="tank_fill_lid")
        for side, sign in (("L", -1), ("R", 1)):
            self.box(f"Tank_Saddle_{side}", (-0.52, 1.62, sign * 0.66),
                     (1.90, 0.17, 0.20), self.materials["graphite"], self.fixed_root,
                     role="tank_saddle", bevel=0.02)

        pump = self.empty("Solution_Pump_ROOT", (-2.08, 1.92, 0), self.hydraulics_root,
                          role="solution_pump_root")
        self.cylinder("Solution_Centrifugal_Pump", (0, 0, 0), 0.24, 0.42,
                      self.materials["graphite"], pump, vertices=28,
                      rotation=(0, math.pi / 2, 0), role="solution_pump")
        self.box("Hydraulic_Valve_Manifold", (-2.55, 2.02, 0), (0.40, 0.26, 0.62),
                 self.materials["steel"], self.hydraulics_root, role="hydraulic_manifold", bevel=0.025)
        self.pipe_between("Tank_To_Pump_Wet_Line", (-1.40, 2.18, 0), (-2.08, 1.92, 0),
                          0.050, self.materials["rod"], self.hydraulics_root, role="wet_plumbing")
        self.pipe_between("Pump_To_Boom_Wet_Line", (-2.08, 1.92, 0), (-3.66, 2.48, 0),
                          0.043, self.materials["rod"], self.hydraulics_root, role="wet_plumbing")

    def _add_truss_segment(self, side, label, length, direction, parent):
        center_x = direction * length / 2
        for rail, y in (("Lower", -0.15), ("Upper", 0.15)):
            self.box(f"Boom_{side}_{label}_{rail}_Rail", (center_x, y, 0),
                     (length, 0.085, 0.12), self.materials["steel"], parent,
                     role="boom_truss_rail", bevel=0.009)
        bays = max(4, int(round(length / 0.75)))
        for index in range(bays + 1):
            x = direction * index * length / bays
            self.pipe_between(f"Boom_{side}_{label}_Post_{index + 1:02d}", (x, -0.15, 0),
                              (x, 0.15, 0), 0.022, self.materials["steel"], parent,
                              role="boom_truss_post")
        for index in range(bays):
            x0 = direction * index * length / bays
            x1 = direction * (index + 1) * length / bays
            low = index % 2 == 0
            self.pipe_between(f"Boom_{side}_{label}_Diagonal_{index + 1:02d}",
                              (x0, -0.15 if low else 0.15, 0),
                              (x1, 0.15 if low else -0.15, 0), 0.020,
                              self.materials["steel"], parent, role="boom_truss_diagonal")
        self.box(f"Boom_{side}_{label}_Wet_Pipe", (center_x, -0.22, 0),
                 (length * 0.98, 0.035, 0.035), self.materials["rod"], parent,
                 role="boom_wet_plumbing", bevel=0.006)
        nozzle_count = max(5, int(round(length / 0.75)))
        for index in range(nozzle_count):
            x = direction * (index + 0.5) * length / nozzle_count
            self.cylinder(f"Boom_{side}_{label}_Nozzle_{index + 1:02d}", (x, -0.28, 0),
                          0.025, 0.08, self.materials["warning"], parent, vertices=10,
                          rotation=(math.pi / 2, 0, 0), role="spray_nozzle")

    def _add_boom(self):
        lift = self.empty("Boom_Center_Lift_ROOT", (-3.66, 2.54, 0), self.fixed_root,
                          role="boom_center_lift_root")
        roll = self.empty("Boom_Center_Roll_Pivot", parent=lift, role="boom_roll_pivot")
        center = self.empty("Boom_Center_ROOT", parent=roll, role="boom_center_root")
        for rail, y in (("Lower", -0.15), ("Upper", 0.15)):
            self.box(f"Boom_Center_{rail}_Rail", (0, y, 0), (0.16, 0.085, self.BOOM_CENTER_M),
                     self.materials["steel"], center, role="boom_center_truss", bevel=0.009)
        for index in range(8):
            z = -self.BOOM_CENTER_M / 2 + index * self.BOOM_CENTER_M / 7
            self.pipe_between(f"Boom_Center_Post_{index + 1:02d}", (0, -0.15, z),
                              (0, 0.15, z), 0.022, self.materials["steel"], center,
                              role="boom_truss_post")
        self.box("Boom_Center_Wet_Pipe", (0, -0.22, 0), (0.035, 0.035, self.BOOM_CENTER_M * 0.98),
                 self.materials["rod"], center, role="boom_wet_plumbing", bevel=0.006)

        for side, sign in (("L", -1), ("R", 1)):
            inner_pivot = self.empty(f"Boom_{side}_Fold_Pivot", (0, 0, sign * self.BOOM_CENTER_M / 2),
                                     center, role="inner_boom_fold_pivot")
            inner = self.empty(f"Boom_{side}_ROOT", parent=inner_pivot, role="inner_boom_stage_root")
            self._add_truss_segment(side, "Inner", self.BOOM_INNER_M, 1, inner)
            mid_pivot = self.empty(f"Boom_{side}_Mid_Fold_Pivot", (self.BOOM_INNER_M, 0, 0),
                                   inner, role="middle_boom_fold_pivot")
            mid = self.empty(f"Boom_{side}_Mid_ROOT", parent=mid_pivot, role="middle_boom_stage_root")
            self._add_truss_segment(side, "Mid", self.BOOM_MID_M, -1, mid)
            tip_pivot = self.empty(f"Boom_{side}_Tip_Fold_Pivot", (-self.BOOM_MID_M, 0, 0),
                                   mid, role="tip_boom_fold_pivot")
            tip = self.empty(f"Boom_{side}_Tip_ROOT", parent=tip_pivot, role="tip_boom_stage_root")
            self._add_truss_segment(side, "Tip", self.BOOM_TIP_M, 1, tip)
            self.box(f"Boom_{side}_Breakaway_End", (self.BOOM_TIP_M, 0, 0),
                     (0.16, 0.36, 0.18), self.materials["graphite"], tip,
                     role="reconstructed_breakaway", bevel=0.015)
            self.pipe_between(f"Boom_{side}_Self_Centering_Link", (0, 0.26, sign * 0.08),
                              (0.62, 0.42, sign * 0.08), 0.032, self.materials["rod"],
                              inner, role="self_centering_link_cue")

        pulse = self.empty("Nozzle_Valve_Pulse_ROOT", (0, -0.28, 0), center,
                           role="pwm_valve_visual_root")
        for index, z in enumerate((-1.2, -0.4, 0.4, 1.2), 1):
            self.box(f"AIM_Command_Valve_Cue_{index:02d}", (0, 0, z), (0.14, 0.11, 0.12),
                     self.materials["warning"], pulse, role="pwm_valve_cue", bevel=0.012)
        for side, sign in (("L", -1), ("R", 1)):
            self.box(f"Boom_Lift_Mast_{side}", (-3.76, 2.47, sign * 0.52),
                     (0.20, 1.36, 0.18), self.materials["graphite"], self.fixed_root,
                     role="boom_lift_mast")
            self.pipe_between(f"Boom_Lift_Cylinder_{side}", (-3.56, 1.92, sign * 0.44),
                              (-3.66, 2.86, sign * 0.44), 0.055, self.materials["steel"],
                              self.hydraulics_root, role="boom_lift_cylinder")

    def build_model(self):
        self.build_common_roots()
        self._add_running_gear()
        self._add_carrier()
        self._add_boom()
        missing = [name for name in self.required_semantics() if bpy.data.objects.get(name) is None]
        if missing:
            raise RuntimeError(f"Trident 5550 builder omitted semantic nodes: {', '.join(missing)}")
        return self.root

    def _pose_nodes(self):
        return [
            "Front_L_Steering_Pivot", "Front_R_Steering_Pivot",
            "Rear_L_Steering_Pivot", "Rear_R_Steering_Pivot",
            "Front_L_Suspension_ROOT", "Front_R_Suspension_ROOT",
            "Rear_L_Suspension_ROOT", "Rear_R_Suspension_ROOT",
            "Boom_Center_Lift_ROOT", "Boom_Center_Roll_Pivot",
            "Boom_L_Fold_Pivot", "Boom_R_Fold_Pivot",
            "Boom_L_Mid_Fold_Pivot", "Boom_R_Mid_Fold_Pivot",
            "Boom_L_Tip_Fold_Pivot", "Boom_R_Tip_Fold_Pivot",
            "Nozzle_Valve_Pulse_ROOT",
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

    def _set_staged_boom_pose(self, amount=1.0):
        bpy.data.objects["Boom_L_Fold_Pivot"].rotation_euler.y = 1.18 * amount
        bpy.data.objects["Boom_R_Fold_Pivot"].rotation_euler.y = -1.18 * amount
        bpy.data.objects["Boom_L_Mid_Fold_Pivot"].rotation_euler.y = -2.34 * amount
        bpy.data.objects["Boom_R_Mid_Fold_Pivot"].rotation_euler.y = 2.34 * amount
        bpy.data.objects["Boom_L_Tip_Fold_Pivot"].rotation_euler.y = 2.28 * amount
        bpy.data.objects["Boom_R_Tip_Fold_Pivot"].rotation_euler.y = -2.28 * amount

    def render_views(self):
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        neutral = self._capture_pose()
        views = [
            ("operator-side", (0.6, 3.4, -14.5), (0, 2.0, 0), 10.8, "suspension"),
            ("front-three-quarter", (12.0, 8.0, -11.0), (0.5, 2.1, 0), 11.3, "steering"),
            ("rear-three-quarter", (-11.5, 7.0, 10.0), (-1.2, 2.2, 0), 11.4, "lift"),
            ("elevated-technical", (18.0, 24.0, -21.0), (-1.2, 2.0, 0), 27.0, "staged"),
            ("articulation-detail", (-7.0, 4.6, -6.4), (-3.3, 2.55, -0.7), 6.6, "half_staged"),
            ("right-side", (0.4, 3.5, 14.5), (0, 2.0, 0), 10.8, "roll"),
        ]
        paths = []
        try:
            for label, location, target, scale, pose_name in views:
                self._restore_pose(neutral)
                if pose_name == "suspension":
                    bpy.data.objects["Front_L_Suspension_ROOT"].location.y += 0.05
                    bpy.data.objects["Rear_R_Suspension_ROOT"].location.y += 0.05
                elif pose_name == "steering":
                    for name in ("Front_L_Steering_Pivot", "Front_R_Steering_Pivot"):
                        bpy.data.objects[name].rotation_euler.y = 0.16
                    for name in ("Rear_L_Steering_Pivot", "Rear_R_Steering_Pivot"):
                        bpy.data.objects[name].rotation_euler.y = -0.10
                elif pose_name == "lift":
                    bpy.data.objects["Boom_Center_Lift_ROOT"].location.y += 0.16
                    bpy.data.objects["Boom_Center_Roll_Pivot"].rotation_euler.x = 0.035
                elif pose_name == "staged":
                    self._set_staged_boom_pose(0.88)
                    bpy.data.objects["Boom_Center_Lift_ROOT"].location.y += 0.12
                elif pose_name == "half_staged":
                    self._set_staged_boom_pose(0.52)
                elif pose_name == "roll":
                    bpy.data.objects["Boom_Center_Roll_Pivot"].rotation_euler.x = -0.04
                    bpy.data.objects["Nozzle_Valve_Pulse_ROOT"].location.y += 0.018
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
        boom_meshes = [obj for side in ("L", "R")
                       for obj in self._descendants(bpy.data.objects[f"Boom_{side}_Fold_Pivot"])
                       if obj.type == "MESH"]
        carrier_meshes = [bpy.data.objects[name] for name in
                          ("Solution_Tank_1600gal_Exterior", "Engine_House",
                           "Cab_Floor", "Cab_Roof", "Cab_Front_Glass", "Cab_Rear_Glass")]
        minimum_y = math.inf
        collisions = []
        samples = 73
        try:
            for index in range(samples):
                cycle = index / (samples - 1)
                front_angle = -0.12 + 0.24 * self._sine(cycle)
                rear_angle = 0.08 - 0.16 * self._sine(cycle, 0.50)
                for name in ("Front_L_Steering_Pivot", "Front_R_Steering_Pivot"):
                    bpy.data.objects[name].rotation_euler.y = front_angle
                for name in ("Rear_L_Steering_Pivot", "Rear_R_Steering_Pivot"):
                    bpy.data.objects[name].rotation_euler.y = rear_angle
                lift = 0.03 * self._sine(cycle, 0.18)
                for name in ("Front_L_Suspension_ROOT", "Front_R_Suspension_ROOT",
                             "Rear_L_Suspension_ROOT", "Rear_R_Suspension_ROOT"):
                    bpy.data.objects[name].location.y = neutral[name][0].y + lift
                bpy.data.objects["Boom_Center_Lift_ROOT"].location.y = neutral["Boom_Center_Lift_ROOT"][0].y + 0.16 * self._sine(cycle, 0.30)
                bpy.data.objects["Boom_Center_Roll_Pivot"].rotation_euler.x = -0.03 + 0.06 * self._sine(cycle, 0.42)
                inner = self._sine(cycle, 0.52)
                middle = self._sine(cycle, 0.60)
                tip = self._sine(cycle, 0.68)
                bpy.data.objects["Boom_L_Fold_Pivot"].rotation_euler.y = 1.05 * inner
                bpy.data.objects["Boom_R_Fold_Pivot"].rotation_euler.y = -1.05 * inner
                bpy.data.objects["Boom_L_Mid_Fold_Pivot"].rotation_euler.y = -2.10 * middle
                bpy.data.objects["Boom_R_Mid_Fold_Pivot"].rotation_euler.y = 2.10 * middle
                bpy.data.objects["Boom_L_Tip_Fold_Pivot"].rotation_euler.y = 2.10 * tip
                bpy.data.objects["Boom_R_Tip_Fold_Pivot"].rotation_euler.y = -2.10 * tip
                bpy.context.view_layer.update()
                minimum_y = min(minimum_y, self._scene_min_y())
                if len(collisions) < 12:
                    carrier_bounds = [(obj.name, self._mesh_bounds(obj)) for obj in carrier_meshes]
                    for boom_obj in boom_meshes:
                        boom_bounds = self._mesh_bounds(boom_obj)
                        for carrier_name, bounds in carrier_bounds:
                            if self._aabb_intersects(boom_bounds, bounds):
                                collisions.append({"sample": index, "boom": boom_obj.name,
                                                   "carrier": carrier_name})
                                break
                        if len(collisions) >= 12:
                            break
        finally:
            self._restore_pose(neutral)
        return {
            "duration_seconds": 18,
            "sample_count": samples,
            "sample_interval_seconds": 0.25,
            "minimum_public_y_m": round(minimum_y, 6),
            "major_carrier_collision_count": len(collisions),
            "first_collisions": collisions,
            "boundary": "Discrete AABB sampling of the exact viewer target ranges; not continuous collision detection, a boom-control solver, hydraulic response, wind or an operating limit.",
        }

    def machine_specific_validation_gates(self, contract):
        statuses = []
        object_names = set(bpy.data.objects.keys())
        sizes = contract["bounds"]["size_m"]
        autoplay = self._sample_autoplay()
        tire_records = []
        for axle in ("Front", "Rear"):
            for side in ("L", "R"):
                name = f"{axle}_{side}_Tire"
                low, high = self._mesh_bounds(bpy.data.objects[name])
                tire_records.append({"node": name, "minimum_y_m": round(low[1], 6),
                                     "diameter_x_m": round(high[0] - low[0], 6),
                                     "diameter_y_m": round(high[1] - low[1], 6)})
        centers = {name: self._world_location(bpy.data.objects[name]) for name in
                   ("Front_L_Wheel_Pivot", "Rear_L_Wheel_Pivot",
                    "Front_R_Wheel_Pivot", "Rear_R_Wheel_Pivot")}
        wheelbases = [abs(centers["Front_L_Wheel_Pivot"][0] - centers["Rear_L_Wheel_Pivot"][0]),
                      abs(centers["Front_R_Wheel_Pivot"][0] - centers["Rear_R_Wheel_Pivot"][0])]
        segment_arithmetic = self.BOOM_CENTER_M + 2 * (self.BOOM_INNER_M + self.BOOM_MID_M + self.BOOM_TIP_M)

        methods = {
            "frozen_liquid_configuration": "Compare configuration identity, selected tank and boom topology nodes, section-span arithmetic and hydrostatic four-wheel-drive running gear.",
            "single_identity_root": "Inspect the exported GLB root contract and traverse carrier, four-corner running gear, liquid system and boom from Machine_Root.",
            "four_tire_contact": "Measure the four neutral tire AABBs, radial equality and two 4.32 m wheelbase lines.",
            "suspension_continuity": "Traverse four independent suspension roots through steering pivots to wheel pivots and count visible twin-strut descendants.",
            "boom_fold_symmetry": "Compare mirrored inner/middle/tip stage descendant mesh counts and sum the reconstructed stage lengths to the published 36.5 m span.",
            "boom_center_and_roll_continuity": "Inspect the lift -> roll -> center -> paired three-stage fold hierarchy and visible mast/cylinder support.",
            "tank_boom_cab_clearance": "Measure neutral tank, cab and boom-center AABBs plus the tank exterior cylindrical cue volume.",
            "transport_envelope": "Compare the exported neutral GLB AABB and measured wheelbases with the published folded carrier envelope and visible-study target.",
            "ground_collision": "Sample every public mesh AABB at 0.25-second intervals over the exact 18-second Auto target path.",
            "self_collision": "Sample every articulated boom mesh against major tank, engine and cab AABBs over the exact viewer target path.",
            "swept_volume_collision": "Combine phased path ground and major carrier AABB results while retaining the continuous-solver boundary.",
        }
        semantics = {
            "frozen_liquid_configuration": ["Solution_Tank_1600gal_Exterior", "Boom_Center_ROOT", "Boom_L_ROOT", "Boom_R_ROOT", "Solution_Pump_ROOT"],
            "single_identity_root": ["Machine_Root", "Fixed_Structure_ROOT", "Running_Gear_ROOT", "Hydraulics_ROOT"],
            "four_tire_contact": ["Front_L_Tire", "Front_R_Tire", "Rear_L_Tire", "Rear_R_Tire"],
            "suspension_continuity": ["Front_L_Suspension_ROOT", "Front_R_Suspension_ROOT", "Rear_L_Suspension_ROOT", "Rear_R_Suspension_ROOT"],
            "boom_fold_symmetry": ["Boom_L_ROOT", "Boom_L_Mid_ROOT", "Boom_L_Tip_ROOT", "Boom_R_ROOT", "Boom_R_Mid_ROOT", "Boom_R_Tip_ROOT"],
            "boom_center_and_roll_continuity": ["Boom_Center_Lift_ROOT", "Boom_Center_Roll_Pivot", "Boom_Center_ROOT", "Boom_L_Fold_Pivot", "Boom_R_Fold_Pivot"],
            "tank_boom_cab_clearance": ["Solution_Tank_1600gal_Exterior", "Cab_Rear_Glass", "Boom_Center_ROOT", "Solution_Pump_ROOT"],
            "transport_envelope": ["Front_End_Structure", "Rear_End_Structure", "Cab_Roof", "Front_L_Tire", "Front_R_Tire"],
            "ground_collision": ["Front_L_Tire", "Front_R_Tire", "Rear_L_Tire", "Rear_R_Tire"],
            "self_collision": ["Boom_L_Fold_Pivot", "Boom_R_Fold_Pivot", "Solution_Tank_1600gal_Exterior", "Cab_Rear_Glass"],
            "swept_volume_collision": ["Boom_Center_Lift_ROOT", "Boom_Center_Roll_Pivot", "Boom_L_Mid_Fold_Pivot", "Boom_R_Mid_Fold_Pivot"],
        }
        facts = {
            "frozen_liquid_configuration": ["boom-working-span", "selected-boom-width", "liquid-tank-capacity", "drive-system"],
            "single_identity_root": ["drive-system"],
            "four_tire_contact": ["wheelbase", "drive-system"],
            "suspension_continuity": ["suspension-function", "drive-system"],
            "boom_fold_symmetry": ["boom-working-span", "selected-boom-width"],
            "boom_center_and_roll_continuity": ["boom-working-span", "pwm-frequency"],
            "tank_boom_cab_clearance": ["liquid-tank-capacity", "cab-volume"],
            "transport_envelope": ["public-envelope-x", "public-envelope-y", "public-envelope-z", "wheelbase"],
            "ground_collision": ["public-envelope-y", "drive-system"],
            "self_collision": ["public-envelope-z", "boom-working-span"],
            "swept_volume_collision": ["boom-working-span", "wheelbase"],
        }

        def gate(gate_id, ok, evidence):
            statuses.append({"id": gate_id, "status": "PASS" if ok else "FAIL",
                             "detail": {"method": methods[gate_id], "evidence": evidence,
                                        "semantic_nodes": semantics[gate_id], "fact_ids": facts[gate_id]}})

        stage_roots = [f"Boom_{side}{suffix}" for side in ("L", "R")
                       for suffix in ("_ROOT", "_Mid_ROOT", "_Tip_ROOT")]
        gate("frozen_liquid_configuration",
             self.configuration_id == "CASEIH-TRIDENT5550-NAM-LIQ1600-ALBOOM120-AIMCF2-4WD-CANDIDATE"
             and abs(segment_arithmetic - 36.5) <= 0.001
             and all(name in object_names for name in stage_roots),
             {"configuration_id": self.configuration_id, "tank_selection_US_gal": 1600,
              "published_working_span_m": 36.5,
              "reconstructed_section_arithmetic_m": {"center": self.BOOM_CENTER_M,
                  "per_side": [self.BOOM_INNER_M, self.BOOM_MID_M, self.BOOM_TIP_M],
                  "total": segment_arithmetic},
              "boundary": "Section allocation and all folds are reconstructed; arithmetic equality is not manufacturer geometry."})
        gate("single_identity_root", contract["scene_root_count"] == 1 and contract["root_name"] == "Machine_Root",
             {"scene_root_count": contract["scene_root_count"], "root_name": contract["root_name"],
              "major_branches": ["Fixed_Structure_ROOT", "Running_Gear_ROOT", "Hydraulics_ROOT"]})
        tire_ok = len(tire_records) == 4 and all(abs(item["minimum_y_m"]) <= 0.002
                                                and abs(item["diameter_x_m"] - item["diameter_y_m"]) <= 0.002
                                                for item in tire_records)
        gate("four_tire_contact", tire_ok and all(abs(value - self.WHEELBASE_M) <= 0.001 for value in wheelbases),
             {"tire_count": len(tire_records), "tires": tire_records,
              "measured_left_right_wheelbase_m": [round(value, 6) for value in wheelbases],
              "visible_study_wheelbase_m": self.WHEELBASE_M})
        struts = sorted(name for name in object_names if "Suspension_Barrel" in name)
        suspension_ok = len(struts) == 8 and all(bpy.data.objects[f"{axle}_{side}_Steering_Pivot"].parent
                                                == bpy.data.objects[f"{axle}_{side}_Suspension_ROOT"]
                                                for axle in ("Front", "Rear") for side in ("L", "R"))
        gate("suspension_continuity", suspension_ok,
             {"independent_suspension_roots": 4, "visible_strut_barrels": len(struts),
              "steering_pivots": [f"{axle}_{side}_Steering_Pivot" for axle in ("Front", "Rear") for side in ("L", "R")],
              "boundary": "Travel and load response are reconstructed visualization cues."})
        symmetry = []
        symmetric = True
        for suffix in ("_ROOT", "_Mid_ROOT", "_Tip_ROOT"):
            counts = [len([obj for obj in self._descendants(bpy.data.objects[f"Boom_{side}{suffix}"]) if obj.type == "MESH"])
                      for side in ("L", "R")]
            symmetry.append({"stage_suffix": suffix, "mesh_counts_L_R": counts})
            symmetric = symmetric and counts[0] == counts[1] and counts[0] > 0
        gate("boom_fold_symmetry", symmetric and abs(segment_arithmetic - self.BOOM_SPAN_M) <= 0.001,
             {"mirrored_stage_records": symmetry, "reconstructed_total_span_m": segment_arithmetic,
              "published_working_span_m": self.BOOM_SPAN_M})
        center_chain_ok = (bpy.data.objects["Boom_Center_Roll_Pivot"].parent == bpy.data.objects["Boom_Center_Lift_ROOT"]
                           and bpy.data.objects["Boom_Center_ROOT"].parent == bpy.data.objects["Boom_Center_Roll_Pivot"])
        gate("boom_center_and_roll_continuity", center_chain_ok,
             {"hierarchy": ["Boom_Center_Lift_ROOT", "Boom_Center_Roll_Pivot", "Boom_Center_ROOT",
                            "Boom_L_Fold_Pivot/Boom_R_Fold_Pivot"],
              "lift_mast_count": 2, "lift_cylinder_count": 2, "pwm_valve_cue_count": 4})
        tank_bounds = self._mesh_bounds(bpy.data.objects["Solution_Tank_1600gal_Exterior"])
        cab_bounds = self._mesh_bounds(bpy.data.objects["Cab_Rear_Glass"])
        boom_x = self._world_location(bpy.data.objects["Boom_Center_ROOT"])[0]
        tank_volume = math.pi * self.TANK_RADIUS_M ** 2 * self.TANK_LENGTH_M
        tank_to_boom = tank_bounds[0][0] - boom_x
        tank_to_cab = cab_bounds[0][0] - tank_bounds[1][0]
        gate("tank_boom_cab_clearance", tank_volume >= self.TANK_CAPACITY_M3 and tank_to_boom > 1.0 and tank_to_cab > 1.0,
             {"tank_exterior_cylinder_volume_m3": round(tank_volume, 6),
              "published_capacity_m3": round(self.TANK_CAPACITY_M3, 6),
              "neutral_boom_to_tank_x_gap_m": round(tank_to_boom, 6),
              "neutral_tank_to_cab_x_gap_m": round(tank_to_cab, 6),
              "internal_volume_claimed": False})
        envelope_ok = all(abs(actual - expected) <= 0.003 for actual, expected in zip(sizes, (9.72, 4.01, 4.21)))
        gate("transport_envelope", envelope_ok and all(abs(value - self.WHEELBASE_M) <= 0.001 for value in wheelbases),
             {"measured_glb_xyz_m": sizes, "published_folded_carrier_xyz_m": [9.72, 4.01, 4.21],
              "measured_wheelbase_m": [round(value, 6) for value in wheelbases],
              "transport_pose": "nested folded three-stage wings"})
        gate("ground_collision", autoplay["minimum_public_y_m"] >= -0.002,
             {"neutral_minimum_y_m": contract["bounds"]["min_m"][1],
              "sampled_auto_path": autoplay, "tolerance_m": -0.002})
        gate("self_collision", autoplay["major_carrier_collision_count"] == 0,
             {"sampled_auto_path": autoplay, "major_carrier_nodes": [obj.name for obj in
               [bpy.data.objects[name] for name in ("Solution_Tank_1600gal_Exterior", "Engine_House", "Cab_Floor", "Cab_Roof")]]})
        gate("swept_volume_collision", autoplay["minimum_public_y_m"] >= -0.002
             and autoplay["major_carrier_collision_count"] == 0,
             {"sampled_auto_path": autoplay, "continuous_solver": False,
              "scope": "Exact viewer target path versus ground and major carrier AABBs only."})
        return statuses


if __name__ == "__main__":
    Trident5550Builder(shared.load_design(DESIGN), DESIGN, OUTPUT_DIR).run()

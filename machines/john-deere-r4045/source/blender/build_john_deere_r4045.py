#!/usr/bin/env python3
"""Deterministic machine-local R4045 technical structural-study builder.

The admitted MY2020 order guide constrains the selected 06W5N carrier,
1,200 U.S. gallon stainless solution tank, 120 ft steel boom, 20 in
off-center plumbing, 72 five-position nozzle bodies, 11 section valves,
five-sensor leveling package, 1.47 m crop clearance, and 3.05-4.06 m tread
range. Hidden coordinates and articulation limits remain explicitly
reconstructed visualization choices; this is not manufacturer CAD.
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

spec = importlib.util.spec_from_file_location("exo_fleet_builder_r4045", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load shared fleet builder: {SHARED_GENERATOR}")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)


class R4045Builder(shared.FleetBuilder):
    """Author the selected sprayer as a component-readable local topology."""

    TREAD_CENTER_M = 3.658
    TIRE_RADIUS_M = 1.0
    TIRE_WIDTH_M = 0.42
    FRONT_X_M = 2.55
    REAR_X_M = -2.55
    FRAME_UNDERSIDE_M = 1.47
    TANK_RADIUS_M = 1.05
    TANK_LENGTH_M = 1.40
    TANK_CAPACITY_M3 = 1200.0 * 0.003785411784
    # The order guide names a nominal 36 m (120 ft) option; it does not publish
    # an exact tip-to-tip drawing.  This independently authored 36.20 m span is
    # a presentation choice that contains 72 bodies at 0.508 m pitch without
    # masquerading as manufacturer dimensional authority.
    BOOM_PRESENTATION_SPAN_M = 36.20
    BOOM_CENTER_SPAN_M = 3.66
    BOOM_INNER_SPAN_M = 6.096
    BOOM_MID_SPAN_M = 6.096
    NOZZLE_SPACING_M = 0.508
    NOZZLE_COUNT = 72
    VALVE_COUNT = 11
    SENSOR_COUNT = 5

    def write_machine_wrapper(self):
        """Keep this audited machine-local subclass intact."""

    def required_semantics(self):
        names = [
            name for name in super().required_semantics()
            if name != "Front_Axle_Oscillation_Pivot"
        ]
        names.extend(
            [
                "Front_Axle_Group_ROOT",
                "Front_L_Suspension_ROOT",
                "Front_R_Suspension_ROOT",
                "Rear_L_Suspension_ROOT",
                "Rear_R_Suspension_ROOT",
                "Steering_L_Pivot",
                "Steering_R_Pivot",
                "Boom_Center_Lift_ROOT",
                "Boom_Center_Roll_Pivot",
                "Boom_L_Mid_Fold_Pivot",
                "Boom_L_Mid_ROOT",
                "Boom_L_Tip_Fold_Pivot",
                "Boom_L_Tip_ROOT",
                "Boom_R_Mid_Fold_Pivot",
                "Boom_R_Mid_ROOT",
                "Boom_R_Tip_Fold_Pivot",
                "Boom_R_Tip_ROOT",
                "Solution_Pump_ROOT",
            ]
        )
        return list(dict.fromkeys(names))

    @staticmethod
    def _descendants(root):
        result = []
        stack = list(root.children)
        while stack:
            child = stack.pop()
            result.append(child)
            stack.extend(child.children)
        return result

    @staticmethod
    def _world_center(obj):
        return obj.matrix_world.translation.copy()

    @staticmethod
    def _mesh_bounds(obj):
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        minimum = [min(point[axis] for point in points) for axis in range(3)]
        maximum = [max(point[axis] for point in points) for axis in range(3)]
        return minimum, maximum

    @staticmethod
    def _parent_path(obj):
        path = []
        current = obj
        while current is not None:
            path.append(current.name)
            current = current.parent
        return path

    def _add_adjustable_leg(self, axle_root, axle, side, sign, steerable):
        """Add one independent twin-strut leg and its adjustable axle sleeve."""
        suspension = self.empty(
            f"{axle}_{side}_Suspension_ROOT",
            (0, 0, sign * self.TREAD_CENTER_M / 2),
            axle_root,
            role="independent_suspension_root",
        )
        inboard = -sign
        self.box(
            f"{axle}_{side}_Tread_Adjust_Slide",
            (0, 0, inboard * 0.72),
            (0.28, 0.16, 1.56),
            self.materials["steel"],
            suspension,
            role="tread_adjust_slide",
            bevel=0.014,
        )
        self.cylinder(
            f"{axle}_{side}_Wheel_Motor_Housing",
            (0, 0, 0),
            0.20,
            0.31,
            self.materials["graphite"],
            suspension,
            vertices=24,
            role="wheel_motor_housing",
        )
        for index, x in enumerate((-0.13, 0.13), 1):
            self.cylinder(
                f"{axle}_{side}_Air_Strut_{index}_Barrel",
                (x, 0.42, 0),
                0.072,
                0.64,
                self.materials["graphite"],
                suspension,
                vertices=20,
                rotation=(math.pi / 2, 0, 0),
                role="air_suspension_barrel",
            )
            self.cylinder(
                f"{axle}_{side}_Air_Strut_{index}_Rod",
                (x, 0.68, 0),
                0.040,
                0.50,
                self.materials["rod"],
                suspension,
                vertices=16,
                rotation=(math.pi / 2, 0, 0),
                role="air_suspension_rod",
            )
        self.box(
            f"{axle}_{side}_Upper_Strut_Mount",
            (0, 0.75, 0),
            (0.42, 0.14, 0.36),
            self.materials["graphite"],
            suspension,
            role="suspension_mount",
        )

        wheel_parent = suspension
        if steerable:
            wheel_parent = self.empty(
                f"Steering_{side}_Pivot",
                (0, 0, 0),
                suspension,
                role="steering_pivot",
            )
            self.box(
                f"Front_{side}_Steering_Knuckle",
                (0, 0, -sign * 0.08),
                (0.24, 0.34, 0.16),
                self.materials["steel"],
                wheel_parent,
                role="steering_knuckle",
            )
            self.box(
                f"Front_{side}_Steering_Arm",
                (-0.13, 0.11, -sign * 0.19),
                (0.34, 0.08, 0.10),
                self.materials["steel"],
                wheel_parent,
                role="steering_arm",
            )
            # These visible linkage cues live below the steering pivot, so the
            # rods and ram move with the knuckle instead of remaining as a
            # disconnected fixed-axle graphic.  Link lengths and closure remain
            # reconstructed and are not an Ackermann or hydraulic solution.
            self.pipe_between(
                f"Front_{side}_Steering_Link_Rod",
                (-0.13, 0.11, -sign * 0.19),
                (-0.13, 0.11, -sign * 0.68),
                0.028,
                self.materials["rod"],
                wheel_parent,
                role="steering_link",
            )
            self.pipe_between(
                f"Front_{side}_Steering_Ram_Cue",
                (-0.10, 0.06, -sign * 0.28),
                (0.20, 0.08, -sign * 0.72),
                0.043,
                self.materials["steel"],
                wheel_parent,
                role="steering_cylinder_cue",
            )

        return self.add_wheel(
            f"{axle}_{side}",
            (0, 0, 0),
            self.TIRE_RADIUS_M,
            self.TIRE_WIDTH_M,
            wheel_parent,
            tread_count=18,
        )

    def _add_running_gear(self):
        front_group = self.empty(
            "Front_Axle_Group_ROOT",
            (self.FRONT_X_M, self.TIRE_RADIUS_M, 0),
            self.running_root,
            role="front_axle_group",
        )
        front_axle = self.empty("Front_Axle_ROOT", parent=front_group, role="front_axle_root")
        self.box(
            "Front_Tread_Adjust_Crossmember",
            (0, 0, 0),
            (0.34, 0.18, 2.48),
            self.materials["graphite"],
            front_axle,
            role="axle_crossmember",
        )
        self.cylinder(
            "Front_Axle_Center_Housing",
            (0, 0, 0),
            0.22,
            0.42,
            self.materials["steel"],
            front_axle,
            vertices=24,
            rotation=(math.pi / 2, 0, 0),
            role="axle_center_housing",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self._add_adjustable_leg(front_axle, "Front", side, sign, steerable=True)

        rear_axle = self.empty(
            "Rear_Axle_ROOT",
            (self.REAR_X_M, self.TIRE_RADIUS_M, 0),
            self.running_root,
            role="rear_axle_root",
        )
        self.box(
            "Rear_Tread_Adjust_Crossmember",
            (0, 0, 0),
            (0.34, 0.18, 2.48),
            self.materials["graphite"],
            rear_axle,
            role="axle_crossmember",
        )
        self.cylinder(
            "Rear_Axle_Center_Housing",
            (0, 0, 0),
            0.22,
            0.42,
            self.materials["steel"],
            rear_axle,
            vertices=24,
            rotation=(math.pi / 2, 0, 0),
            role="axle_center_housing",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self._add_adjustable_leg(rear_axle, "Rear", side, sign, steerable=False)

    def _add_carrier(self):
        frame_height = 0.20
        self.box(
            "High_Clearance_Frame",
            (0, self.FRAME_UNDERSIDE_M + frame_height / 2, 0),
            (6.45, frame_height, 1.35),
            self.materials["graphite"],
            self.fixed_root,
            role="chassis",
            bevel=0.018,
        )
        for x in (-2.55, 2.55):
            for side, sign in (("L", -1), ("R", 1)):
                self.pipe_between(
                    f"Frame_Leg_{'Rear' if x < 0 else 'Front'}_{side}",
                    (x, self.FRAME_UNDERSIDE_M + 0.02, sign * 0.54),
                    (x, 1.72, sign * self.TREAD_CENTER_M / 2),
                    0.072,
                    self.materials["steel"],
                    self.fixed_root,
                    role="chassis_leg",
                )
        self.box("Engine_House", (2.24, 2.20, 0), (2.56, 1.16, 1.48), self.materials["body_dark"], self.fixed_root, role="engine_house", bevel=0.055)
        for index in range(8):
            self.box(f"Engine_Side_Vent_{index + 1:02d}", (2.44 + index * 0.12, 2.28, -0.755), (0.075, 0.58, 0.028), self.materials["graphite"], self.fixed_root, role="cooling_vent", bevel=0.006)

        cab = self.empty("Operator_Station_ROOT", (3.45, 1.57, 0), self.fixed_root, role="operator_station")
        self.box("Cab_Floor", (0, 0.09, 0), (1.55, 0.18, 1.84), self.materials["graphite"], cab, role="cab_structure")
        self.box("Cab_Roof", (0, 2.16, 0), (1.64, 0.16, 1.92), self.materials["body"], cab, role="cab_structure", bevel=0.032)
        self.box("Cab_Front_Glass", (0.72, 1.15, 0), (0.10, 1.72, 1.70), self.materials["glass"], cab, role="glazing", bevel=0.025)
        self.box("Cab_Rear_Glass", (-0.72, 1.15, 0), (0.10, 1.60, 1.66), self.materials["glass"], cab, role="glazing", bevel=0.025)
        for side, sign in (("L", -1), ("R", 1)):
            self.box(f"Cab_{side}_Glass", (0, 1.17, sign * 0.88), (1.30, 1.62, 0.08), self.materials["glass"], cab, role="glazing", bevel=0.022)
            for x, suffix in ((-0.70, "Rear"), (0.70, "Front")):
                self.box(f"Cab_{side}_{suffix}_Post", (x, 1.14, sign * 0.91), (0.10, 1.84, 0.10), self.materials["graphite"], cab, role="cab_structure", bevel=0.012)
            self.pipe_between(f"Cab_{side}_Mirror_Arm", (0.48, 1.72, sign * 0.91), (0.56, 1.77, sign * 1.13), 0.022, self.materials["steel"], cab, role="mirror_support")
            self.box(f"Cab_{side}_Mirror", (0.56, 1.77, sign * 1.16), (0.20, 0.30, 0.08), self.materials["graphite"], cab, role="mirror", bevel=0.012)
        self.box("Operator_Seat", (-0.10, 0.62, 0), (0.52, 0.78, 0.66), self.materials["graphite"], cab, role="operator_cue", bevel=0.032)
        self.box("Cab_Top_Lightbar", (0, 2.25, 0), (0.78, 0.08, 0.16), self.materials["warning"], cab, role="lighting", bevel=0.010)
        for side, z in (("L", -0.25), ("R", 0.25)):
            self.pipe_between(
                f"Cab_Top_Lightbar_{side}_Bracket",
                (0, 2.22, z), (0, 2.16, z), 0.018,
                self.materials["steel"], cab, role="lighting_mount",
            )

        self.cylinder("Solution_Tank_1200gal_Exterior", (-0.42, 2.57, 0), self.TANK_RADIUS_M, self.TANK_LENGTH_M, self.materials["steel"], self.fixed_root, vertices=48, rotation=(0, math.pi / 2, 0), role="solution_tank")
        self.cylinder("Solution_Tank_Fill_Lid", (-0.42, 3.66, 0), 0.22, 0.10, self.materials["graphite"], self.fixed_root, vertices=24, role="tank_lid")
        self.box("Tank_Left_Saddle", (-0.42, 1.57, -0.68), (1.58, 0.16, 0.18), self.materials["graphite"], self.fixed_root, role="tank_mount")
        self.box("Tank_Right_Saddle", (-0.42, 1.57, 0.68), (1.58, 0.16, 0.18), self.materials["graphite"], self.fixed_root, role="tank_mount")

        pump = self.empty("Solution_Pump_ROOT", (-2.35, 1.82, 0), self.hydraulics_root, role="pump_root")
        self.cylinder("Solution_Centrifugal_Pump", (0, 0, 0), 0.24, 0.38, self.materials["graphite"], pump, vertices=28, rotation=(0, math.pi / 2, 0), role="solution_pump")
        self.pipe_between("Tank_To_Pump_Wet_Line", (-1.12, 2.15, 0), (-2.35, 1.82, 0), 0.045, self.materials["rod"], self.hydraulics_root, role="wet_plumbing")
        self.pipe_between("Pump_To_Boom_Wet_Line", (-2.35, 1.82, 0), (-3.62, 2.44, 0), 0.040, self.materials["rod"], self.hydraulics_root, role="wet_plumbing")

    def _add_truss_segment(self, side, label, length, parent):
        sign = -1 if side == "L" else 1
        center_z = sign * length / 2
        for rail, y in (("Lower", -0.13), ("Upper", 0.13)):
            self.box(f"Boom_{side}_{label}_{rail}_Rail", (0, y, center_z), (0.10, 0.075, length), self.materials["steel"], parent, role="boom_truss_rail", bevel=0.010)
        bay_count = max(2, int(round(length / 0.76)))
        bay = length / bay_count
        inset = 0.04
        for index in range(bay_count + 1):
            z = sign * (inset + index * ((length - 2 * inset) / bay_count))
            self.pipe_between(f"Boom_{side}_{label}_Post_{index + 1:02d}", (0, -0.13, z), (0, 0.13, z), 0.024, self.materials["steel"], parent, role="boom_truss_post")
        for index in range(bay_count):
            z0 = sign * (inset + index * ((length - 2 * inset) / bay_count))
            z1 = sign * (inset + (index + 1) * ((length - 2 * inset) / bay_count))
            low_first = index % 2 == 0
            self.pipe_between(f"Boom_{side}_{label}_Diagonal_{index + 1:02d}", (0, -0.13 if low_first else 0.13, z0), (0, 0.13 if low_first else -0.13, z1), 0.021, self.materials["steel"], parent, role="boom_truss_diagonal")
        self.pipe_between(f"Boom_{side}_{label}_Wet_Pipe", (0.08, -0.18, sign * 0.04), (0.08, -0.18, sign * (length - 0.04)), 0.021, self.materials["rod"], parent, role="wet_plumbing")

    def _boom_parent_for_abs_z(self, side, abs_z):
        inner_boundary = self.BOOM_CENTER_SPAN_M / 2 + self.BOOM_INNER_SPAN_M
        mid_boundary = inner_boundary + self.BOOM_MID_SPAN_M
        if abs_z < self.BOOM_CENTER_SPAN_M / 2:
            return bpy.data.objects["Boom_Center_ROOT"], abs_z
        if abs_z < inner_boundary:
            return bpy.data.objects[f"Boom_{side}_ROOT"], abs_z - self.BOOM_CENTER_SPAN_M / 2
        if abs_z < mid_boundary:
            return bpy.data.objects[f"Boom_{side}_Mid_ROOT"], abs_z - inner_boundary
        return bpy.data.objects[f"Boom_{side}_Tip_ROOT"], abs_z - mid_boundary

    def _add_nozzle(self, number, world_z):
        side = "L" if world_z < 0 else "R"
        sign = -1 if side == "L" else 1
        parent, local_abs_z = self._boom_parent_for_abs_z(side, abs(world_z))
        local_z = sign * local_abs_z
        root = self.empty(f"Nozzle_Assembly_{number:02d}_ROOT", (0.08, -0.245, local_z), parent, role="nozzle_assembly_root")
        if parent.name == "Boom_Center_ROOT":
            feed_pipe_name = "Boom_Center_Wet_Pipe"
        elif parent.name.endswith("_Mid_ROOT"):
            feed_pipe_name = f"Boom_{side}_Mid_Wet_Pipe"
        elif parent.name.endswith("_Tip_ROOT"):
            feed_pipe_name = f"Boom_{side}_Tip_Wet_Pipe"
        else:
            feed_pipe_name = f"Boom_{side}_Inner_Wet_Pipe"
        drop = self.pipe_between(
            f"Nozzle_Drop_Line_{number:02d}",
            (0.08, -0.18, local_z),
            (0.08, -0.245, local_z),
            0.012,
            self.materials["rod"],
            parent,
            role="nozzle_branch_plumbing",
        )
        drop["exo_feed_pipe"] = feed_pipe_name
        self.cylinder(f"Nozzle_Body_{number:02d}", (0, 0, 0), 0.034, 0.075, self.materials["warning"], root, vertices=10, rotation=(math.pi / 2, 0, 0), role="five_position_nozzle_body")
        for port in range(5):
            angle = math.tau * port / 5
            self.cone(f"Nozzle_{number:02d}_Turret_Port_{port + 1}", (math.cos(angle) * 0.040, -0.052, math.sin(angle) * 0.040), 0.010, 0.006, 0.026, self.materials["graphite"], root, vertices=8, rotation=(math.pi / 2, 0, 0), role="nozzle_turret_port")

    def _add_boom(self):
        center_x = -3.70
        center_y = 2.62
        lift = self.empty("Boom_Center_Lift_ROOT", (center_x, center_y, 0), self.fixed_root, role="boom_lift_root")
        roll = self.empty("Boom_Center_Roll_Pivot", parent=lift, role="boom_roll_pivot")
        center = self.empty("Boom_Center_ROOT", parent=roll, role="motion_root")
        self.box("Boom_Center_Lower_Rail", (0, -0.13, 0), (0.16, 0.075, self.BOOM_CENTER_SPAN_M), self.materials["steel"], center, role="boom_center_truss", bevel=0.010)
        self.box("Boom_Center_Upper_Rail", (0, 0.13, 0), (0.16, 0.075, self.BOOM_CENTER_SPAN_M), self.materials["steel"], center, role="boom_center_truss", bevel=0.010)
        for index, z in enumerate((-1.80, -1.20, -0.60, 0, 0.60, 1.20, 1.80), 1):
            self.pipe_between(f"Boom_Center_Post_{index:02d}", (0, -0.13, z), (0, 0.13, z), 0.024, self.materials["steel"], center, role="boom_truss_post")
        self.pipe_between("Boom_Center_Wet_Pipe", (0.08, -0.18, -1.78), (0.08, -0.18, 1.78), 0.021, self.materials["rod"], center, role="wet_plumbing")
        self.cylinder(
            "Boom_Center_Feed_Manifold", (0.08, -0.18, 0), 0.052, 0.15,
            self.materials["graphite"], center, vertices=20,
            rotation=(math.pi / 2, 0, 0), role="wet_plumbing_manifold",
        )

        tip_length = self.BOOM_PRESENTATION_SPAN_M / 2 - self.BOOM_CENTER_SPAN_M / 2 - self.BOOM_INNER_SPAN_M - self.BOOM_MID_SPAN_M
        for side, sign in (("L", -1), ("R", 1)):
            inner_pivot = self.empty(f"Boom_{side}_Fold_Pivot", (0, 0, sign * self.BOOM_CENTER_SPAN_M / 2), center, role="inner_fold_pivot")
            inner = self.empty(f"Boom_{side}_ROOT", parent=inner_pivot, role="motion_root")
            self._add_truss_segment(side, "Inner", self.BOOM_INNER_SPAN_M, inner)
            self.pipe_between(
                f"Boom_{side}_Center_Inner_Flex_Hose",
                (0.08, -0.18, -sign * 0.05), (0.08, -0.18, sign * 0.04),
                0.026, self.materials["rod"], inner_pivot,
                role="fold_flex_plumbing",
            )
            mid_pivot = self.empty(f"Boom_{side}_Mid_Fold_Pivot", (0, 0, sign * self.BOOM_INNER_SPAN_M), inner, role="mid_fold_pivot")
            mid = self.empty(f"Boom_{side}_Mid_ROOT", parent=mid_pivot, role="motion_root")
            self._add_truss_segment(side, "Mid", self.BOOM_MID_SPAN_M, mid)
            self.pipe_between(
                f"Boom_{side}_Inner_Mid_Flex_Hose",
                (0.08, -0.18, -sign * 0.04), (0.08, -0.18, sign * 0.04),
                0.026, self.materials["rod"], mid_pivot,
                role="fold_flex_plumbing",
            )
            tip_pivot = self.empty(f"Boom_{side}_Tip_Fold_Pivot", (0, 0, sign * self.BOOM_MID_SPAN_M), mid, role="tip_fold_pivot")
            tip = self.empty(f"Boom_{side}_Tip_ROOT", parent=tip_pivot, role="motion_root")
            self._add_truss_segment(side, "Tip", tip_length, tip)
            self.pipe_between(
                f"Boom_{side}_Mid_Tip_Flex_Hose",
                (0.08, -0.18, -sign * 0.04), (0.08, -0.18, sign * 0.04),
                0.026, self.materials["rod"], tip_pivot,
                role="fold_flex_plumbing",
            )
            self.box(f"Boom_{side}_Tip_End_Structure", (0, 0, sign * (tip_length - 0.04)), (0.14, 0.30, 0.08), self.materials["graphite"], tip, role="boom_end_structure", bevel=0.006)

        for index in range(self.NOZZLE_COUNT):
            world_z = (index - (self.NOZZLE_COUNT - 1) / 2) * self.NOZZLE_SPACING_M
            self._add_nozzle(index + 1, world_z)

        valve_positions = [-15.80, -12.70, -9.60, -6.50, -3.35, 0.0, 3.35, 6.50, 9.60, 12.70, 15.80]
        for index, world_z in enumerate(valve_positions, 1):
            if world_z == 0:
                parent, local_z = center, 0.0
            else:
                side = "L" if world_z < 0 else "R"
                sign = -1 if side == "L" else 1
                parent, local_abs_z = self._boom_parent_for_abs_z(side, abs(world_z))
                local_z = sign * local_abs_z
            self.box(f"Section_Control_Valve_{index:02d}", (-0.03, -0.19, local_z), (0.16, 0.15, 0.12), self.materials["graphite"], parent, role="section_control_valve", bevel=0.015)

        sensor_positions = [(-14.6, "L_Outer"), (-7.2, "L_Inner"), (0.0, "Center"), (7.2, "R_Inner"), (14.6, "R_Outer")]
        for world_z, label in sensor_positions:
            if world_z == 0:
                parent, local_z = center, 0.0
            else:
                side = "L" if world_z < 0 else "R"
                sign = -1 if side == "L" else 1
                parent, local_abs_z = self._boom_parent_for_abs_z(side, abs(world_z))
                local_z = sign * local_abs_z
            sensor = self.empty(f"Boom_Level_Sensor_{label}_ROOT", (0.02, -0.25, local_z), parent, role="sensor_root")
            self.box(f"Boom_Level_Sensor_{label}_Body", (0, 0, 0), (0.13, 0.10, 0.16), self.materials["graphite"], sensor, role="boom_level_sensor", bevel=0.012)
            self.cone(f"Boom_Level_Sensor_{label}_Field_Cue", (0, -0.09, 0), 0.038, 0.010, 0.08, self.materials["warning"], sensor, vertices=12, rotation=(math.pi / 2, 0, 0), role="sensor_optic")

        for side, sign in (("L", -1), ("R", 1)):
            self.box(f"Boom_Lift_{side}_Mast_Rail", (-3.73, 2.54, sign * 0.48), (0.18, 1.24, 0.16), self.materials["graphite"], self.fixed_root, role="boom_lift_mast")
            self.pipe_between(f"Boom_Lift_{side}_Cylinder", (-3.58, 1.93, sign * 0.42), (-3.70, 2.88, sign * 0.42), 0.054, self.materials["steel"], self.hydraulics_root, role="boom_lift_cylinder")

    def build_high_clearance_sprayer(self):
        self._add_running_gear()
        self._add_carrier()
        self._add_boom()

    def build_model(self):
        self.build_common_roots()
        self.build_high_clearance_sprayer()
        missing = [name for name in self.required_semantics() if bpy.data.objects.get(name) is None]
        if missing:
            raise RuntimeError(f"R4045 builder omitted semantic nodes: {', '.join(missing)}")
        return self.root

    def render_views(self):
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        pose_nodes = [
            "Steering_L_Pivot", "Steering_R_Pivot",
            "Boom_Center_Lift_ROOT", "Boom_Center_Roll_Pivot",
            "Boom_L_Fold_Pivot", "Boom_R_Fold_Pivot",
            "Boom_L_Mid_Fold_Pivot", "Boom_R_Mid_Fold_Pivot",
            "Boom_L_Tip_Fold_Pivot", "Boom_R_Tip_Fold_Pivot",
        ]
        neutral = {
            name: (
                bpy.data.objects[name].location.copy(),
                bpy.data.objects[name].rotation_euler.copy(),
            )
            for name in pose_nodes
        }
        folded_pose = {
            "Boom_L_Fold_Pivot": (0, -1.42, 0),
            "Boom_R_Fold_Pivot": (0, 1.42, 0),
            "Boom_L_Mid_Fold_Pivot": (0, 2.84, 0),
            "Boom_R_Mid_Fold_Pivot": (0, -2.84, 0),
            "Boom_L_Tip_Fold_Pivot": (0, -2.84, 0),
            "Boom_R_Tip_Fold_Pivot": (0, 2.84, 0),
        }
        views = [
            ("operator-side", (1.0, 3.15, -13.0), (0.4, 2.0, 0), 10.8, {}),
            ("front-three-quarter", (11.0, 7.2, -10.0), (0.2, 2.0, 0), 11.2,
             {"Boom_Center_Lift_ROOT": (0, 0.14, 0), "Boom_Center_Roll_Pivot": (0.02, 0, 0)}),
            # A true endpoint proof image: all six reconstructed wing hinges are
            # posed at their declared fold targets rather than merely changing
            # the camera around an otherwise neutral model.
            ("rear-three-quarter", (-11.5, 8.0, -12.5), (-0.8, 2.05, 0), 14.5, folded_pose),
            ("elevated-technical", (24.0, 31.0, -29.0), (-1.0, 1.9, 0), 39.0, {}),
            # Close front-axle endpoint proof.  Both steering pivots carry their
            # own visible link rod and ram cue as descendants.
            ("articulation-detail", (5.4, 2.7, -4.8), (self.FRONT_X_M, 1.12, 0), 4.4,
             {"Steering_L_Pivot": (0, 0.18, 0), "Steering_R_Pivot": (0, 0.18, 0)}),
            ("right-side", (0.5, 3.2, 13.0), (0.2, 2.0, 0), 10.8,
             {"Steering_L_Pivot": (0, -0.18, 0), "Steering_R_Pivot": (0, -0.18, 0)}),
        ]
        paths = []
        for label, location, target, ortho_scale, pose in views:
            for name, (location_neutral, rotation_neutral) in neutral.items():
                bpy.data.objects[name].location = location_neutral
                bpy.data.objects[name].rotation_euler = rotation_neutral
            for name, value in pose.items():
                if name == "Boom_Center_Lift_ROOT":
                    bpy.data.objects[name].location.y = neutral[name][0].y + value[1]
                else:
                    bpy.data.objects[name].rotation_euler = value
            bpy.context.view_layer.update()
            camera.location = location
            self.point_at(camera, target)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        for name, (location_neutral, rotation_neutral) in neutral.items():
            bpy.data.objects[name].location = location_neutral
            bpy.data.objects[name].rotation_euler = rotation_neutral
        bpy.context.view_layer.update()
        return paths

    @staticmethod
    def _autoplay_progress(cycle, phase, mode="sine"):
        value = (cycle + phase) % 1.0
        if mode == "ping-pong":
            return value * 2 if value < 0.5 else (1.0 - value) * 2
        return 0.5 - 0.5 * math.cos(value * math.tau)

    @staticmethod
    def _aabb_intersects(first, second, tolerance=0.002):
        first_min, first_max = first
        second_min, second_max = second
        return all(
            min(first_max[axis], second_max[axis])
            - max(first_min[axis], second_min[axis]) > tolerance
            for axis in range(3)
        )

    @staticmethod
    def _aabb_surface_distance(first, second):
        """Return the Euclidean separation between two world-space AABBs."""
        first_min, first_max = first
        second_min, second_max = second
        separated = [
            max(0.0, max(first_min[axis], second_min[axis]) - min(first_max[axis], second_max[axis]))
            for axis in range(3)
        ]
        return math.sqrt(sum(value * value for value in separated))

    def _sample_autoplay_clearance(self):
        """Sample the exact phased 18 s Auto target path without claiming physics."""
        controlled = [
            "Steering_L_Pivot", "Steering_R_Pivot",
            "Front_L_Suspension_ROOT", "Rear_L_Suspension_ROOT",
            "Front_R_Suspension_ROOT", "Rear_R_Suspension_ROOT",
            "Boom_Center_Lift_ROOT", "Boom_Center_Roll_Pivot",
            "Boom_L_Fold_Pivot", "Boom_R_Fold_Pivot",
            "Boom_L_Mid_Fold_Pivot", "Boom_R_Mid_Fold_Pivot",
            "Boom_L_Tip_Fold_Pivot", "Boom_R_Tip_Fold_Pivot",
        ]
        originals = {
            name: (
                bpy.data.objects[name].location.copy(),
                bpy.data.objects[name].rotation_euler.copy(),
            )
            for name in controlled
        }
        wing_meshes = [
            obj
            for root_name in ("Boom_L_Fold_Pivot", "Boom_R_Fold_Pivot")
            for obj in self._descendants(bpy.data.objects[root_name])
            if obj.type == "MESH"
        ]
        carrier_names = [
            "Solution_Tank_1200gal_Exterior", "Engine_House", "High_Clearance_Frame",
            "Cab_Floor", "Cab_Roof", "Cab_Front_Glass", "Cab_Rear_Glass",
            "Cab_L_Glass", "Cab_R_Glass",
            "Front_L_Tire", "Front_R_Tire", "Rear_L_Tire", "Rear_R_Tire",
        ]
        public_meshes = [obj for obj in self.public_objects() if obj.type == "MESH"]
        samples = 73
        minimum_y = math.inf
        collisions = []
        try:
            for sample in range(samples):
                cycle = sample / (samples - 1)
                steering = -0.18 + 0.36 * self._autoplay_progress(cycle, 0.0)
                for side in ("L", "R"):
                    bpy.data.objects[f"Steering_{side}_Pivot"].rotation_euler.y = steering

                tread = 0.18 * self._autoplay_progress(cycle, 0.16)
                for axle in ("Front", "Rear"):
                    bpy.data.objects[f"{axle}_L_Suspension_ROOT"].location.z = originals[f"{axle}_L_Suspension_ROOT"][0].z - tread
                    bpy.data.objects[f"{axle}_R_Suspension_ROOT"].location.z = originals[f"{axle}_R_Suspension_ROOT"][0].z + tread

                lift_progress = self._autoplay_progress(cycle, 0.30)
                bpy.data.objects["Boom_Center_Lift_ROOT"].location.y = originals["Boom_Center_Lift_ROOT"][0].y + 0.18 * lift_progress
                roll_progress = self._autoplay_progress(cycle, 0.42)
                bpy.data.objects["Boom_Center_Roll_Pivot"].rotation_euler.x = -0.025 + 0.05 * roll_progress

                inner = self._autoplay_progress(cycle, 0.56, "ping-pong")
                mid = self._autoplay_progress(cycle, 0.62, "ping-pong")
                tip = self._autoplay_progress(cycle, 0.68, "ping-pong")
                bpy.data.objects["Boom_L_Fold_Pivot"].rotation_euler.y = -1.42 * inner
                bpy.data.objects["Boom_R_Fold_Pivot"].rotation_euler.y = 1.42 * inner
                bpy.data.objects["Boom_L_Mid_Fold_Pivot"].rotation_euler.y = 2.84 * mid
                bpy.data.objects["Boom_R_Mid_Fold_Pivot"].rotation_euler.y = -2.84 * mid
                bpy.data.objects["Boom_L_Tip_Fold_Pivot"].rotation_euler.y = -2.84 * tip
                bpy.data.objects["Boom_R_Tip_Fold_Pivot"].rotation_euler.y = 2.84 * tip
                bpy.context.view_layer.update()

                for obj in public_meshes:
                    obj_min, _ = self._mesh_bounds(obj)
                    minimum_y = min(minimum_y, obj_min[1])

                carrier_bounds = {name: self._mesh_bounds(bpy.data.objects[name]) for name in carrier_names}
                for wing in wing_meshes:
                    wing_bounds = self._mesh_bounds(wing)
                    for carrier_name, bounds in carrier_bounds.items():
                        if self._aabb_intersects(wing_bounds, bounds):
                            collisions.append({"sample": sample, "cycle": round(cycle, 6), "wing": wing.name, "carrier": carrier_name})
                            if len(collisions) >= 12:
                                break
                    if len(collisions) >= 12:
                        break
                if len(collisions) >= 12:
                    break
        finally:
            for name, (location, rotation) in originals.items():
                bpy.data.objects[name].location = location
                bpy.data.objects[name].rotation_euler = rotation
            bpy.context.view_layer.update()
        return {
            "duration_seconds": 18,
            "sample_count": samples,
            "sample_interval_seconds": round(18 / (samples - 1), 6),
            "minimum_public_y_m": round(minimum_y, 6),
            "major_carrier_collision_count": len(collisions),
            "first_collisions": collisions,
            "sampled_carrier_nodes": carrier_names,
            "sampled_wing_mesh_count": len(wing_meshes),
            "boundary": "Discrete target-path AABB audit of the exact viewer channel ranges and phases; not continuous collision detection, a hydraulic solver, terrain response, or a safety limit.",
        }

    def machine_specific_validation_gates(self, contract):
        bpy.context.view_layer.update()
        statuses = []

        methods = {
            "frozen_06W5N_4920_5165_4995_configuration": "Compare the runtime configuration identity and counted selected-package component nodes with the hash-bound MY2020 order-guide selections.",
            "selected_120ft_boom_presence": "Verify a complete bilateral three-stage steel-boom presentation for the nominal catalog 36 m (120 ft) option, while recording the authored span as reconstructed rather than a published tip-to-tip dimension.",
            "four_tire_contact": "Measure each authored tire mesh world AABB in the neutral pose; require four zero-plane contacts and equal X/Y tire diameters.",
            "front_axle_continuity": "Traverse both front tire and steering-link parent chains and measure tread centers, frame underside, and visible front running-gear descendants without asserting axle oscillation.",
            "boom_fold_symmetry": "Compare mirrored inner, mid, and tip fold-root descendant mesh counts and record the paired reconstructed fold targets.",
            "boom_center_tank_cab_clearance": "Measure neutral-pose tank, center-rail and cab world AABB surfaces and the gross cylindrical tank enclosure volume against the selected capacity.",
            "application_plumbing_topology": "Count the selected nozzle, valve and sensor topology, measure nozzle pitch, and verify neutral-pose AABB contact through the tank-pump-center feed, six fold flex connectors, 72 branch drops and nozzle bodies.",
            "ground_collision": "Measure the exported neutral-pose minimum Y, then sample all public mesh AABBs at 0.25-second intervals across the exact phased 18-second Auto target path.",
            "self_collision": "Measure neutral major-volume gaps, then sample every articulated wing mesh against the tank, engine, frame, cab and tire AABBs across the exact phased 18-second Auto target path.",
            "neutral_unbranded_material_review": "Enumerate every used Blender material and image datablock; reject branded names or image textures.",
        }
        semantic_nodes = {
            "frozen_06W5N_4920_5165_4995_configuration": ["Solution_Tank_1200gal_Exterior", "Boom_Center_ROOT", "Nozzle_Body_01", "Nozzle_Body_72", "Section_Control_Valve_01", "Section_Control_Valve_11", "Boom_Level_Sensor_Center_ROOT"],
            "selected_120ft_boom_presence": ["Boom_Center_ROOT", "Boom_L_ROOT", "Boom_L_Mid_ROOT", "Boom_L_Tip_ROOT", "Boom_R_ROOT", "Boom_R_Mid_ROOT", "Boom_R_Tip_ROOT", "Boom_L_Tip_End_Structure", "Boom_R_Tip_End_Structure"],
            "four_tire_contact": ["Front_L_Tire", "Front_R_Tire", "Rear_L_Tire", "Rear_R_Tire"],
            "front_axle_continuity": ["Front_Axle_ROOT", "Front_L_Suspension_ROOT", "Front_R_Suspension_ROOT", "Steering_L_Pivot", "Steering_R_Pivot", "Front_L_Wheel_Pivot", "Front_R_Wheel_Pivot"],
            "boom_fold_symmetry": ["Boom_L_Fold_Pivot", "Boom_L_ROOT", "Boom_L_Mid_Fold_Pivot", "Boom_L_Mid_ROOT", "Boom_L_Tip_Fold_Pivot", "Boom_L_Tip_ROOT", "Boom_R_Fold_Pivot", "Boom_R_ROOT", "Boom_R_Mid_Fold_Pivot", "Boom_R_Mid_ROOT", "Boom_R_Tip_Fold_Pivot", "Boom_R_Tip_ROOT"],
            "boom_center_tank_cab_clearance": ["Boom_Center_ROOT", "Solution_Tank_1200gal_Exterior", "Cab_Rear_Glass"],
            "application_plumbing_topology": ["Solution_Pump_ROOT", "Tank_To_Pump_Wet_Line", "Pump_To_Boom_Wet_Line", "Boom_Center_Wet_Pipe", "Boom_Center_Feed_Manifold", "Boom_L_Center_Inner_Flex_Hose", "Boom_L_Inner_Mid_Flex_Hose", "Boom_L_Mid_Tip_Flex_Hose", "Boom_R_Center_Inner_Flex_Hose", "Boom_R_Inner_Mid_Flex_Hose", "Boom_R_Mid_Tip_Flex_Hose", "Nozzle_Drop_Line_01", "Nozzle_Drop_Line_72", "Nozzle_Body_01", "Nozzle_Body_72", "Section_Control_Valve_01", "Section_Control_Valve_11", "Boom_Level_Sensor_Center_ROOT"],
            "ground_collision": ["Front_L_Tire", "Front_R_Tire", "Rear_L_Tire", "Rear_R_Tire"],
            "self_collision": ["Solution_Tank_1200gal_Exterior", "Engine_House", "Boom_Center_ROOT"],
            "neutral_unbranded_material_review": [],
        }
        fact_ids = {
            "frozen_06W5N_4920_5165_4995_configuration": ["model-identity"],
            "selected_120ft_boom_presence": ["selected-boom"],
            "four_tire_contact": [],
            "front_axle_continuity": ["crop-clearance", "hydraulic-tread-range"],
            "boom_fold_symmetry": [],
            "boom_center_tank_cab_clearance": ["solution-tank-capacity"],
            "application_plumbing_topology": ["selected-nozzle-spacing", "selected-boom-plumbing", "selected-auto-boom-leveling"],
            "ground_collision": [],
            "self_collision": [],
            "neutral_unbranded_material_review": [],
        }

        def gate(gate_id, ok, evidence):
            statuses.append(
                {
                    "id": gate_id,
                    "status": "PASS" if ok else "FAIL",
                    "detail": {
                        "method": methods[gate_id],
                        "evidence": evidence,
                        "semantic_nodes": semantic_nodes[gate_id],
                        "fact_ids": fact_ids[gate_id],
                    },
                }
            )

        object_names = set(bpy.data.objects.keys())
        body_names = sorted(name for name in object_names if name.startswith("Nozzle_Body_"))
        port_names = sorted(name for name in object_names if "_Turret_Port_" in name)
        valve_names = sorted(name for name in object_names if name.startswith("Section_Control_Valve_"))
        sensor_bodies = sorted(name for name in object_names if name.startswith("Boom_Level_Sensor_") and name.endswith("_Body"))
        autoplay_clearance = self._sample_autoplay_clearance()

        gate(
            "frozen_06W5N_4920_5165_4995_configuration",
            self.configuration_id == "JD-R4045-MY2020-NA-06W5N-4920-5165-4995-CANDIDATE" and len(body_names) == self.NOZZLE_COUNT and len(valve_names) == self.VALVE_COUNT and len(sensor_bodies) == self.SENSOR_COUNT,
            {
                "configuration_id": self.configuration_id,
                "selected_codes": ["06W5N", "4920", "5165", "4995", "5465"],
                "measured_component_counts": {"five_position_nozzle_bodies": len(body_names), "nozzle_turret_ports": len(port_names), "section_control_valves": len(valve_names), "boom_level_sensor_bodies": len(sensor_bodies)},
                "authority": "Counts are checked against the admitted MY2020 order-guide configuration; positions remain reconstructed.",
            },
        )

        measured_span = contract["bounds"]["size_m"][2]
        boom_roots = [
            "Boom_Center_ROOT", "Boom_L_ROOT", "Boom_L_Mid_ROOT", "Boom_L_Tip_ROOT",
            "Boom_R_ROOT", "Boom_R_Mid_ROOT", "Boom_R_Tip_ROOT",
        ]
        gate(
            "selected_120ft_boom_presence",
            all(name in object_names for name in boom_roots)
            and abs(measured_span - self.BOOM_PRESENTATION_SPAN_M) <= 0.002,
            {
                "catalog_option_label": "36 m (120 ft) steel boom",
                "catalog_authority": "nominal selected option identity only",
                "authored_visible_z_span_m": measured_span,
                "authored_presentation_target_m": self.BOOM_PRESENTATION_SPAN_M,
                "tip_to_tip_manufacturer_dimension_claimed": False,
                "boundary": "The 36.20 m visible span is reconstructed to stage the selected 72-body, 0.508 m-pitch package; it is not a Deere tip-to-tip measurement.",
            },
        )

        tire_records = []
        tire_ok = True
        for axle in ("Front", "Rear"):
            for side in ("L", "R"):
                name = f"{axle}_{side}_Tire"
                obj = bpy.data.objects[name]
                minimum, maximum = self._mesh_bounds(obj)
                diameter_x = maximum[0] - minimum[0]
                diameter_y = maximum[1] - minimum[1]
                tire_records.append({"node": name, "minimum_y_m": round(minimum[1], 6), "diameter_x_m": round(diameter_x, 6), "diameter_y_m": round(diameter_y, 6), "radial_difference_m": round(abs(diameter_x - diameter_y), 6)})
                tire_ok = tire_ok and abs(minimum[1]) <= 0.002 and abs(diameter_x - diameter_y) <= 0.002
        gate("four_tire_contact", tire_ok and len(tire_records) == 4, {"tire_count": len(tire_records), "neutral_contact_tolerance_m": 0.002, "circularity_tolerance_m": 0.002, "tires": tire_records, "tire_configuration_authority": "Reconstructed generic row-crop tire envelope; exact order code remains unresolved."})

        front_paths = {side: self._parent_path(bpy.data.objects[f"Front_{side}_Tire"]) for side in ("L", "R")}
        expected_chain = {side: [f"Front_{side}_Tire", f"Front_{side}_Wheel_ROOT", f"Front_{side}_Wheel_Pivot", f"Steering_{side}_Pivot", f"Front_{side}_Suspension_ROOT", "Front_Axle_ROOT", "Front_Axle_Group_ROOT", "Running_Gear_ROOT", "Machine_Root"] for side in ("L", "R")}
        steering_link_paths = {
            side: self._parent_path(bpy.data.objects[f"Front_{side}_Steering_Link_Rod"])
            for side in ("L", "R")
        }
        steering_ram_paths = {
            side: self._parent_path(bpy.data.objects[f"Front_{side}_Steering_Ram_Cue"])
            for side in ("L", "R")
        }
        steering_descends = all(
            f"Steering_{side}_Pivot" in steering_link_paths[side]
            and f"Steering_{side}_Pivot" in steering_ram_paths[side]
            for side in ("L", "R")
        )
        tread_centers = [self._world_center(bpy.data.objects[f"Front_{side}_Wheel_Pivot"])[2] for side in ("L", "R")]
        measured_tread = abs(tread_centers[1] - tread_centers[0])
        frame_min, _ = self._mesh_bounds(bpy.data.objects["High_Clearance_Frame"])
        front_descendant_meshes = [obj.name for obj in self._descendants(bpy.data.objects["Front_Axle_ROOT"]) if obj.type == "MESH"]
        gate(
            "front_axle_continuity",
            all(front_paths[side] == expected_chain[side] for side in ("L", "R")) and steering_descends and 3.05 <= measured_tread <= 4.06 and abs(frame_min[1] - self.FRAME_UNDERSIDE_M) <= 0.002 and len(front_descendant_meshes) >= 20,
            {"measured_parent_paths": front_paths, "steering_link_parent_paths": steering_link_paths, "steering_ram_parent_paths": steering_ram_paths, "linkage_descends_from_steering_pivots": steering_descends, "front_axle_oscillation_claimed": False, "measured_front_tread_center_m": round(measured_tread, 6), "published_tread_range_m": [3.05, 4.06], "measured_frame_underside_m": round(frame_min[1], 6), "published_crop_clearance_m": self.FRAME_UNDERSIDE_M, "front_axle_visible_descendant_meshes": len(front_descendant_meshes), "hierarchy": "front group -> independent suspension/tread roots -> steering pivots with linkage cues -> wheel pivots -> circular tires"},
        )

        symmetry_pairs = [("Boom_L_ROOT", "Boom_R_ROOT"), ("Boom_L_Mid_ROOT", "Boom_R_Mid_ROOT"), ("Boom_L_Tip_ROOT", "Boom_R_Tip_ROOT")]
        pair_records = []
        symmetric = True
        for left_name, right_name in symmetry_pairs:
            left_meshes = [obj for obj in self._descendants(bpy.data.objects[left_name]) if obj.type == "MESH"]
            right_meshes = [obj for obj in self._descendants(bpy.data.objects[right_name]) if obj.type == "MESH"]
            pair_ok = len(left_meshes) == len(right_meshes) and len(left_meshes) > 0
            symmetric = symmetric and pair_ok
            pair_records.append({"roots": [left_name, right_name], "mesh_counts": [len(left_meshes), len(right_meshes)], "symmetric": pair_ok})
        gate("boom_fold_symmetry", symmetric, {"neutral_pose_pairs": pair_records, "viewer_transport_fold_targets_rad": {"inner": [-1.42, 1.42], "mid": [2.84, -2.84], "tip": [-2.84, 2.84]}, "boundary": "Alternating accordion-fold pivots and target angles are reconstructed and deliberately bounded; they are not operator limits."})

        tank_min, tank_max = self._mesh_bounds(bpy.data.objects["Solution_Tank_1200gal_Exterior"])
        cab_min, _ = self._mesh_bounds(bpy.data.objects["Cab_Rear_Glass"])
        boom_rail_bounds = self._mesh_bounds(bpy.data.objects["Boom_Center_Lower_Rail"])
        tank_volume = math.pi * self.TANK_RADIUS_M ** 2 * self.TANK_LENGTH_M
        tank_to_boom_x = tank_min[0] - boom_rail_bounds[1][0]
        cab_to_boom_x = cab_min[0] - boom_rail_bounds[1][0]
        gate("boom_center_tank_cab_clearance", tank_volume >= self.TANK_CAPACITY_M3 and tank_to_boom_x >= 1.0 and cab_to_boom_x >= 4.0, {"measured_tank_exterior_cylinder_volume_m3": round(tank_volume, 6), "published_solution_capacity_m3": round(self.TANK_CAPACITY_M3, 6), "boom_center_lower_rail_x_max_m": round(boom_rail_bounds[1][0], 6), "tank_x_min_m": round(tank_min[0], 6), "tank_to_boom_center_rail_aabb_surface_clearance_m": round(tank_to_boom_x, 6), "cab_to_boom_center_rail_aabb_surface_clearance_m": round(cab_to_boom_x, 6), "tank_internal_volume_claimed": False})

        nozzle_z = sorted(round(self._world_center(bpy.data.objects[name])[2], 6) for name in body_names)
        spacings = [round(nozzle_z[index + 1] - nozzle_z[index], 6) for index in range(len(nozzle_z) - 1)]
        max_spacing_error = max((abs(value - self.NOZZLE_SPACING_M) for value in spacings), default=math.inf)
        end_margins = [nozzle_z[0] + self.BOOM_PRESENTATION_SPAN_M / 2, self.BOOM_PRESENTATION_SPAN_M / 2 - nozzle_z[-1]] if nozzle_z else []

        flex_links = []
        for side in ("L", "R"):
            flex_links.extend([
                (f"Boom_{side}_Center_Inner_Flex_Hose", "Boom_Center_Wet_Pipe", f"Boom_{side}_Inner_Wet_Pipe"),
                (f"Boom_{side}_Inner_Mid_Flex_Hose", f"Boom_{side}_Inner_Wet_Pipe", f"Boom_{side}_Mid_Wet_Pipe"),
                (f"Boom_{side}_Mid_Tip_Flex_Hose", f"Boom_{side}_Mid_Wet_Pipe", f"Boom_{side}_Tip_Wet_Pipe"),
            ])
        flex_contact_records = []
        for flex_name, upstream_name, downstream_name in flex_links:
            flex_bounds = self._mesh_bounds(bpy.data.objects[flex_name])
            upstream_gap = self._aabb_surface_distance(flex_bounds, self._mesh_bounds(bpy.data.objects[upstream_name]))
            downstream_gap = self._aabb_surface_distance(flex_bounds, self._mesh_bounds(bpy.data.objects[downstream_name]))
            flex_contact_records.append({
                "flex": flex_name,
                "upstream": upstream_name,
                "downstream": downstream_name,
                "upstream_aabb_surface_gap_m": round(upstream_gap, 6),
                "downstream_aabb_surface_gap_m": round(downstream_gap, 6),
            })
        max_flex_gap = max((max(record["upstream_aabb_surface_gap_m"], record["downstream_aabb_surface_gap_m"]) for record in flex_contact_records), default=math.inf)

        drop_names = sorted(name for name in object_names if name.startswith("Nozzle_Drop_Line_"))
        drop_contact_records = []
        for drop_name in drop_names:
            number = drop_name.rsplit("_", 1)[-1]
            drop = bpy.data.objects[drop_name]
            feed_name = str(drop["exo_feed_pipe"])
            drop_bounds = self._mesh_bounds(drop)
            feed_gap = self._aabb_surface_distance(drop_bounds, self._mesh_bounds(bpy.data.objects[feed_name]))
            body_gap = self._aabb_surface_distance(drop_bounds, self._mesh_bounds(bpy.data.objects[f"Nozzle_Body_{number}"]))
            drop_contact_records.append({"drop": drop_name, "feed_pipe": feed_name, "feed_gap_m": round(feed_gap, 6), "body_gap_m": round(body_gap, 6)})
        max_drop_gap = max((max(record["feed_gap_m"], record["body_gap_m"]) for record in drop_contact_records), default=math.inf)

        system_pairs = [
            ("Tank_To_Pump_Wet_Line", "Solution_Tank_1200gal_Exterior"),
            ("Tank_To_Pump_Wet_Line", "Solution_Centrifugal_Pump"),
            ("Pump_To_Boom_Wet_Line", "Solution_Centrifugal_Pump"),
            ("Pump_To_Boom_Wet_Line", "Boom_Center_Wet_Pipe"),
            ("Pump_To_Boom_Wet_Line", "Boom_Center_Feed_Manifold"),
        ]
        system_contact_records = []
        for first_name, second_name in system_pairs:
            gap = self._aabb_surface_distance(self._mesh_bounds(bpy.data.objects[first_name]), self._mesh_bounds(bpy.data.objects[second_name]))
            system_contact_records.append({"nodes": [first_name, second_name], "aabb_surface_gap_m": round(gap, 6)})
        max_system_gap = max((record["aabb_surface_gap_m"] for record in system_contact_records), default=math.inf)
        plumbing_ok = max_flex_gap <= 0.003 and max_drop_gap <= 0.003 and max_system_gap <= 0.003
        gate(
            "application_plumbing_topology",
            len(body_names) == self.NOZZLE_COUNT
            and len(port_names) == self.NOZZLE_COUNT * 5
            and len(drop_names) == self.NOZZLE_COUNT
            and max_spacing_error <= 0.001
            and len(valve_names) == self.VALVE_COUNT
            and len(sensor_bodies) == self.SENSOR_COUNT
            and len(flex_contact_records) == 6
            and plumbing_ok,
            {
                "nozzle_body_count": len(body_names),
                "nozzle_branch_drop_count": len(drop_names),
                "five_position_port_count": len(port_names),
                "section_control_valve_count": len(valve_names),
                "boom_level_sensor_count": len(sensor_bodies),
                "measured_pitch_m": sorted(set(spacings)),
                "published_pitch_m": self.NOZZLE_SPACING_M,
                "maximum_pitch_error_m": round(max_spacing_error, 6),
                "authored_tip_to_outer_nozzle_center_margins": [round(value, 6) for value in end_margins],
                "fold_flex_contacts": flex_contact_records,
                "maximum_fold_flex_aabb_surface_gap_m": max_flex_gap,
                "maximum_nozzle_branch_aabb_surface_gap_m": max_drop_gap,
                "tank_pump_boom_contacts": system_contact_records,
                "maximum_tank_pump_boom_aabb_surface_gap_m": max_system_gap,
                "boundary": "Neutral-pose visible static topology only; flexible-hose sweep, pressure, flow, droplets and operating behavior remain unresolved.",
            },
        )

        public_min_y = contract["bounds"]["min_m"][1]
        gate("ground_collision", public_min_y >= -0.002 and autoplay_clearance["minimum_public_y_m"] >= -0.002 and tire_ok, {"neutral_pose_public_minimum_y_m": public_min_y, "sampled_auto_path": autoplay_clearance, "allowed_tolerance_m": -0.002})

        engine_min, _ = self._mesh_bounds(bpy.data.objects["Engine_House"])
        tank_engine_gap = engine_min[0] - tank_max[0]
        major_clear = tank_engine_gap >= 0.10 and tank_to_boom_x >= 1.0 and autoplay_clearance["major_carrier_collision_count"] == 0
        gate("self_collision", major_clear, {"neutral_tank_to_engine_x_gap_m": round(tank_engine_gap, 6), "neutral_tank_to_boom_center_rail_aabb_surface_gap_m": round(tank_to_boom_x, 6), "sampled_auto_path": autoplay_clearance})

        material_names = sorted(material.name for material in bpy.data.materials if material.users > 0)
        disallowed = [name for name in material_names if "deere" in name.lower() or "logo" in name.lower() or "brand" in name.lower()]
        external_images = sorted(image.name for image in bpy.data.images if image.source not in {"VIEWER", "GENERATED"})
        gate("neutral_unbranded_material_review", not disallowed and not external_images, {"used_materials": material_names, "disallowed_material_names": disallowed, "external_image_textures": external_images, "rights_boundary": "Neutral procedural materials only; no logo, copied livery, texture, or manufacturer geometry."})
        return statuses


if __name__ == "__main__":
    design = shared.load_design(DESIGN)
    R4045Builder(design, DESIGN, OUTPUT_DIR).run()

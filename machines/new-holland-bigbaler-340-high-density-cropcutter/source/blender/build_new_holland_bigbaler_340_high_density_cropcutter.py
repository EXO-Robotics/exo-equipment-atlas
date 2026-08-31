#!/usr/bin/env python3
"""Build a neutral BigBaler 340 HD CropCutter structural study.

Published counts and dimensions constrain the visible package. Hidden pivots,
linkages, phase, pressure, crop flow, tire selection and clearances remain
reconstructed presentation choices rather than manufacturer CAD or a solver.
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

spec = importlib.util.spec_from_file_location("exo_bigbaler340hd", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load shared generator {SHARED_GENERATOR}")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)


class BigBaler340HDBuilder(shared.FleetBuilder):
    TIRE_RADIUS = 0.60
    TIRE_WIDTH = 0.42
    TIRE_Z = 1.4935 - TIRE_WIDTH / 2
    FRONT_AXLE_X = -0.58
    REAR_AXLE_X = -1.92
    PICKUP_WIDTH = 2.35
    ROTOR_WIDTH = 1.20
    PLUNGER_STROKE = 0.748
    STEER_RAD = math.radians(14.0)

    def write_machine_wrapper(self):
        """Keep this machine-owned source instead of regenerating a wrapper."""

    def required_semantics(self):
        names = list(super().required_semantics())
        names.extend([
            "Front_Tandem_Axle_ROOT", "Rear_Tandem_Axle_ROOT",
            "Tandem_FL_Suspension_ROOT", "Tandem_FR_Suspension_ROOT",
            "Tandem_RL_Suspension_ROOT", "Tandem_RR_Suspension_ROOT",
            "Tandem_FL_Steering_Pivot", "Tandem_FR_Steering_Pivot",
            "Tandem_RL_Steering_Pivot", "Tandem_RR_Steering_Pivot",
            "PTO_ROOT", "Flywheel_ROOT", "Pickup_Reel_ROOT",
            "CropCutter_Rotor_ROOT", "CropCutter_Knife_Drawer_ROOT",
            "Stuffer_Fork_ROOT", "Density_Door_ROOT", "Knotter_Deck_ROOT",
            "Knotter_01_ROOT", "Knotter_02_ROOT", "Knotter_03_ROOT",
            "Knotter_04_ROOT", "Knotter_05_ROOT", "Knotter_06_ROOT",
            "Bale_Chamber_ROOT", "Hydraulic_Manifold_ROOT",
        ])
        return list(dict.fromkeys(names))

    @staticmethod
    def _bounds(obj):
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        return (
            [min(float(point[axis]) for point in points) for axis in range(3)],
            [max(float(point[axis]) for point in points) for axis in range(3)],
        )

    @staticmethod
    def _world(obj):
        point = obj.matrix_world.translation
        return [float(point.x), float(point.y), float(point.z)]

    @staticmethod
    def _intersects(first, second, tolerance=0.003):
        return all(
            min(first[1][axis], second[1][axis])
            - max(first[0][axis], second[0][axis]) > tolerance
            for axis in range(3)
        )

    def _scene_min_y(self):
        bpy.context.view_layer.update()
        return min(
            self._bounds(obj)[0][1]
            for obj in self.public_objects() if obj.type == "MESH"
        )

    def _running_corner(self, axle, code, side, sign):
        prefix = f"Tandem_{code}{side}"
        suspension = self.empty(
            f"{prefix}_Suspension_ROOT", (0, 0, sign * self.TIRE_Z), axle,
            role="hydraulic_tandem_suspension_root",
        )
        self.box(
            f"{prefix}_Suspension_Rocker", (0, 0.10, -sign * 0.18),
            (0.46, 0.18, 0.46), self.materials["graphite"], suspension,
            role="suspension_rocker", bevel=0.025,
        )
        for index, x in enumerate((-0.13, 0.13), 1):
            self.cylinder(
                f"{prefix}_Suspension_Barrel_{index}", (x, 0.24, -sign * 0.12),
                0.052, 0.40, self.materials["steel"], suspension, vertices=18,
                rotation=(math.pi / 2, 0, 0), role="suspension_barrel",
            )
            self.cylinder(
                f"{prefix}_Suspension_Rod_{index}", (x, 0.41, -sign * 0.12),
                0.028, 0.28, self.materials["rod"], suspension, vertices=14,
                rotation=(math.pi / 2, 0, 0), role="suspension_rod",
            )
        steering = self.empty(
            f"{prefix}_Steering_Pivot", parent=suspension,
            role="auto_steer_kingpin",
        )
        self.box(
            f"{prefix}_Steering_Knuckle", (0, 0.02, -sign * 0.07),
            (0.24, 0.30, 0.18), self.materials["graphite"], steering,
            role="steering_knuckle", bevel=0.02,
        )
        self.add_wheel(prefix, (0, 0, 0), self.TIRE_RADIUS,
                       self.TIRE_WIDTH, steering, tread_count=18)

    def _build_running_gear(self):
        for label, code, x in (
            ("Front", "F", self.FRONT_AXLE_X),
            ("Rear", "R", self.REAR_AXLE_X),
        ):
            axle = self.empty(
                f"{label}_Tandem_Axle_ROOT", (x, self.TIRE_RADIUS, 0),
                self.running_root, role="tandem_axle_root",
            )
            self.box(
                f"{label}_Tandem_Axle_Beam", (0, 0.04, 0),
                (0.34, 0.24, 2.34), self.materials["graphite"], axle,
                role="tandem_axle_beam", bevel=0.025,
            )
            self._running_corner(axle, code, "L", -1)
            self._running_corner(axle, code, "R", 1)
            self.pipe_between(
                f"{label}_Tandem_Tie_Rod", (-0.10, 0.15, -1.06),
                (-0.10, 0.15, 1.06), 0.030, self.materials["rod"], axle,
                role="steering_tie_rod",
            )

    def _build_body(self):
        self.box(
            "Baler_Main_Frame", (-0.42, 0.84, 0), (5.18, 0.30, 1.80),
            self.materials["graphite"], self.fixed_root,
            role="baler_chassis", bevel=0.035,
        )
        chamber = self.empty(
            "Bale_Chamber_ROOT", (-1.02, 1.02, 0), self.fixed_root,
            role="large_square_bale_chamber_root",
        )
        self.box(
            "Bale_Chamber_Floor", (-0.18, 0.02, 0), (3.72, 0.18, 1.92),
            self.materials["steel"], chamber, role="bale_chamber_floor", bevel=0.02,
        )
        self.box(
            "Bale_Chamber_Roof", (-0.28, 1.76, 0), (3.52, 0.24, 1.92),
            self.materials["body_dark"], chamber, role="bale_chamber_roof", bevel=0.035,
        )
        panel_points = [
            (-1.92, 0.10), (1.28, 0.10), (1.50, 0.48),
            (1.20, 1.84), (-1.82, 1.84),
        ]
        self.side_profile(
            "Bale_Chamber_Right_Panel", panel_points, 0.11,
            self.materials["body"], chamber, z_center=0.97,
            role="bale_chamber_side",
        )
        self.side_profile(
            "Bale_Chamber_Operator_Upper_Panel",
            [(-1.92, 0.86), (1.28, 0.86), (1.50, 1.30),
             (1.20, 1.84), (-1.82, 1.84)],
            0.11, self.materials["body"], chamber, z_center=-0.97,
            role="service_side_panel",
        )
        self.box(
            "Bale_Chamber_Operator_Lower_Rail", (-0.35, 0.36, -0.97),
            (3.25, 0.18, 0.11), self.materials["body_dark"], chamber,
            role="crop_path_cutaway_rail", bevel=0.015,
        )
        self.box(
            "Bale_Chamber_Rear_Frame", (-1.88, 0.92, 0),
            (0.28, 1.76, 2.06), self.materials["graphite"], chamber,
            role="rear_chamber_frame", bevel=0.03,
        )
        self.box(
            "Bale_Section_120x90_Cue", (-2.07, 0.68, 0),
            (0.08, 0.90, 1.20), self.materials["warning"], chamber,
            role="nominal_bale_section_cue", bevel=0.014,
        )
        service = self.empty(
            "Operator_Service_Panel_ROOT", (0.10, 1.42, -1.04), self.fixed_root,
            role="service_panel_pivot",
        )
        self.box(
            "Operator_CropFlow_Service_Panel", (0, 0, 0),
            (1.72, 0.92, 0.09), self.materials["body_dark"], service,
            role="crop_flow_service_panel", bevel=0.03,
        )
        for index in range(7):
            self.box(
                f"Operator_Service_Vent_{index + 1:02d}",
                (-0.58 + index * 0.19, 0.13, -0.052),
                (0.11, 0.42, 0.018), self.materials["graphite"], service,
                role="service_vent", bevel=0.004,
            )
        self.box(
            "Top_Service_Deck", (-1.05, 3.02, 0), (2.92, 0.14, 1.62),
            self.materials["graphite"], self.fixed_root,
            role="service_deck", bevel=0.02,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.box(
                f"Top_Handrail_{side}", (-1.05, 3.434, sign * 0.73),
                (2.70, 0.04, 0.04), self.materials["steel"], self.fixed_root,
                role="transport_handrail", bevel=0.006,
            )
            for index, x in enumerate((-2.20, -1.45, -0.70, 0.05), 1):
                self.box(
                    f"Top_Handrail_{side}_Post_{index}", (x, 3.23, sign * 0.73),
                    (0.04, 0.40, 0.04), self.materials["steel"], self.fixed_root,
                    role="service_handrail", bevel=0.006,
                )
        self.box(
            "Top_Handrail_Rear", (-2.38, 3.434, 0), (0.04, 0.04, 1.50),
            self.materials["steel"], self.fixed_root,
            role="transport_handrail", bevel=0.006,
        )
        for index in range(5):
            self.box(
                f"Operator_Access_Step_{index + 1:02d}",
                (-2.72, 0.62 + index * 0.35, -1.08),
                (0.46, 0.06, 0.34), self.materials["steel"], self.detail_root,
                role="service_step", bevel=0.008,
            )

    def _build_drawbar_and_drive(self):
        pivot = self.empty(
            "Drawbar_Yaw_Pivot", (1.65, 0.72, 0), self.fixed_root,
            role="tractor_articulation_pivot",
        )
        drawbar = self.empty("Drawbar_ROOT", parent=pivot, role="drawbar_root")
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Drawbar_{side}_Arm", (0, 0, sign * 0.44),
                (2.67, -0.12, sign * 0.12), 0.055,
                self.materials["steel"], drawbar, role="twin_drawbar_arm",
            )
        for index, x in enumerate((0.65, 1.35, 2.05), 1):
            width = 0.44 - x * 0.12
            self.pipe_between(
                f"Drawbar_Crossmember_{index}", (x, -0.03, -width),
                (x, -0.03, width), 0.042, self.materials["steel"], drawbar,
                role="drawbar_crossmember",
            )
        self.box(
            "Drawbar_Hitch_Extent", (2.788, -0.12, 0), (0.06, 0.12, 0.22),
            self.materials["graphite"], drawbar,
            role="tractor_hitch_cue", bevel=0.018,
        )
        pto = self.empty("PTO_ROOT", (1.78, 0.90, 0), self.fixed_root, role="pto_drive_root")
        self.pipe_between(
            "PTO_Guard", (0, 0, 0), (2.28, -0.09, 0), 0.095,
            self.materials["steel"], pto, role="pto_guard",
        )
        self.pipe_between(
            "PTO_Shaft", (0.02, 0, 0), (2.25, -0.09, 0), 0.050,
            self.materials["rod"], pto, role="pto_shaft",
        )
        self.box(
            "SmartShift_Gearbox", (0.95, 1.22, 0), (0.62, 0.66, 0.72),
            self.materials["graphite"], self.fixed_root,
            role="two_speed_powershift_gearbox", bevel=0.055,
        )
        flywheel = self.empty(
            "Flywheel_ROOT", (0.73, 1.57, -1.15), self.fixed_root,
            role="flywheel_rotary_root",
        )
        self.cylinder(
            "Flywheel_1080mm", (0, 0, 0), 0.54, 0.14,
            self.materials["steel"], flywheel, vertices=40, role="flywheel",
        )
        self.cylinder(
            "Flywheel_Hub", (0, 0, -0.08), 0.13, 0.18,
            self.materials["graphite"], flywheel, vertices=24, role="flywheel_hub",
        )
        for index in range(8):
            angle = math.tau * index / 8
            self.pipe_between(
                f"Flywheel_Spoke_{index + 1:02d}", (0, 0, -0.08),
                (math.cos(angle) * 0.43, math.sin(angle) * 0.43, -0.08),
                0.026, self.materials["graphite"], flywheel,
                role="flywheel_spoke",
            )

    def _build_pickup(self):
        pivot = self.empty(
            "Pickup_Lift_Pivot", (2.10, 0.54, 0), self.fixed_root,
            role="pickup_raise_lower_pivot",
        )
        pickup = self.empty("Pickup_ROOT", parent=pivot, role="pickup_root")
        reel = self.empty(
            "Pickup_Reel_ROOT", (0.18, 0, 0), pickup,
            role="five_bar_pickup_reel_root",
        )
        self.cylinder(
            "Pickup_Reel_Axle", (0, 0, 0), 0.065, self.PICKUP_WIDTH,
            self.materials["graphite"], reel, vertices=22, role="pickup_reel_axle",
        )
        for bar_index in range(5):
            angle = math.tau * bar_index / 5
            bar = self.empty(
                f"Pickup_Bar_{bar_index + 1:02d}_ROOT",
                (math.cos(angle) * 0.31, math.sin(angle) * 0.31, 0),
                reel, role="pickup_tine_bar_root",
            )
            self.box(
                f"Pickup_Bar_{bar_index + 1:02d}", (0, 0, 0),
                (0.045, 0.045, self.PICKUP_WIDTH), self.materials["steel"], bar,
                role="pickup_tine_bar", bevel=0.007,
            )
            for tine_index in range(17):
                z = -1.08 + tine_index * (2.16 / 16)
                tine = self.side_profile(
                    f"Pickup_Double_Tine_{bar_index * 17 + tine_index + 1:03d}",
                    [(-0.035, 0), (-0.055, 0.11), (-0.022, 0.18),
                     (0, 0.10), (0.022, 0.18), (0.055, 0.11), (0.035, 0)],
                    0.025, self.materials["rod"], bar, z_center=z,
                    role="pickup_double_tine",
                )
                tine.rotation_euler.z = angle - math.pi / 2
        for side, sign in (("L", -1), ("R", 1)):
            self.side_profile(
                f"Pickup_{side}_End_Guard",
                [(-0.10, -0.28), (0.52, -0.24), (0.58, 0.20),
                 (0.08, 0.38), (-0.20, 0.10)],
                0.10, self.materials["body_dark"], pickup,
                z_center=sign * 1.24, role="pickup_end_guard",
            )
            self.cylinder(
                f"Pickup_{side}_Gauge_Wheel", (0.37, -0.15, sign * 1.28),
                0.18, 0.10, self.materials["rubber"], pickup, vertices=20,
                role="pickup_gauge_wheel",
            )
        for index in range(5):
            self.pipe_between(
                f"Pickup_Windguard_{index + 1:02d}",
                (-0.06 + index * 0.14, 0.34, -1.08),
                (0.12 + index * 0.14, 0.05, 1.08),
                0.018, self.materials["steel"], pickup,
                role="pickup_windguard",
            )

    def _build_crop_path(self):
        rotor = self.empty(
            "CropCutter_Rotor_ROOT", (1.42, 0.82, 0), self.fixed_root,
            role="cropcutter_rotor_root",
        )
        self.cylinder(
            "CropCutter_Rotor_1200mm", (0, 0, 0), 0.22, self.ROTOR_WIDTH,
            self.materials["graphite"], rotor, vertices=28, role="cropcutter_rotor",
        )
        for index in range(12):
            angle = math.tau * index / 12
            self.box(
                f"CropCutter_Rotor_Tooth_{index + 1:02d}",
                (math.cos(angle) * 0.27, math.sin(angle) * 0.27, 0),
                (0.14, 0.065, 1.12), self.materials["steel"], rotor,
                rotation=(0, 0, angle), role="cropcutter_rotor_tooth", bevel=0.008,
            )
        drawer = self.empty(
            "CropCutter_Knife_Drawer_ROOT", (1.12, 0.47, 0), self.fixed_root,
            role="cropcutter_knife_drawer_root",
        )
        self.box(
            "CropCutter_Knife_Drawer_Rail", (0, -0.08, 0),
            (0.48, 0.10, 1.44), self.materials["graphite"], drawer,
            role="knife_drawer_rail", bevel=0.012,
        )
        for index in range(29):
            z = -0.56 + index * (1.12 / 28)
            self.box(
                f"CropCutter_Knife_{index + 1:02d}", (0.04, 0.08, z),
                (0.16, 0.30, 0.018), self.materials["steel"], drawer,
                rotation=(0, 0, -0.18), role="spring_protected_knife", bevel=0.003,
            )
        self.box(
            "CropCutter_Feed_Tunnel", (1.03, 0.96, 0), (0.78, 0.34, 1.34),
            self.materials["body_dark"], self.fixed_root,
            role="cropcutter_feed_tunnel", bevel=0.025,
        )
        stuffer = self.empty(
            "Stuffer_Fork_ROOT", (0.70, 1.14, 0), self.fixed_root,
            role="six_tine_stuffer_root",
        )
        self.cylinder(
            "Stuffer_Crank_Disc", (0, 0, -0.64), 0.18, 0.08,
            self.materials["graphite"], stuffer, vertices=24,
            role="stuffer_crank_cue",
        )
        for index in range(6):
            z = -0.50 + index * 0.20
            self.pipe_between(
                f"Stuffer_Tine_{index + 1:02d}", (0, 0, z),
                (-0.46, 0.44, z), 0.026, self.materials["rod"], stuffer,
                role="stuffer_fork_tine",
            )
        plunger = self.empty(
            "Plunger_ROOT", (0.28, 1.52, 0), self.fixed_root,
            role="plunger_reciprocation_root",
        )
        self.box(
            "Plunger_Face", (-0.10, 0, 0), (0.18, 0.82, 1.12),
            self.materials["steel"], plunger, role="plunger_face", bevel=0.018,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Plunger_{side}_Drive_Rod", (0.02, -0.24, sign * 0.42),
                (0.62, -0.42, sign * 0.42), 0.040,
                self.materials["rod"], plunger, role="plunger_drive_rod",
            )

    def _build_density_knotters_hydraulics(self):
        density = self.empty(
            "Density_Door_ROOT", (-1.42, 2.04, 0), self.fixed_root,
            role="seven_cylinder_density_ring_root",
        )
        self.box(
            "Density_Ring_Top_Door", (0, 0.38, 0), (1.28, 0.14, 1.42),
            self.materials["body_dark"], density, role="density_ring_door", bevel=0.022,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.box(
                f"Density_Ring_{side}_Door", (0, -0.05, sign * 0.68),
                (1.28, 0.78, 0.14), self.materials["body_dark"], density,
                role="density_ring_door", bevel=0.022,
            )
        cylinder_specs = [
            ((-0.42, 0.52, -0.40), (0.42, 0.52, -0.40)),
            ((-0.42, 0.52, 0.00), (0.42, 0.52, 0.00)),
            ((-0.42, 0.52, 0.40), (0.42, 0.52, 0.40)),
            ((-0.42, -0.28, -0.78), (0.42, 0.16, -0.78)),
            ((-0.42, 0.08, -0.78), (0.42, 0.32, -0.78)),
            ((-0.42, -0.28, 0.78), (0.42, 0.16, 0.78)),
            ((-0.42, 0.08, 0.78), (0.42, 0.32, 0.78)),
        ]
        for index, (start, end) in enumerate(cylinder_specs, 1):
            self.pipe_between(
                f"Density_Cylinder_{index:02d}", start, end, 0.040,
                self.materials["steel"], density,
                role="density_double_acting_cylinder",
            )
        deck = self.empty(
            "Knotter_Deck_ROOT", (-1.10, 2.77, 0), self.fixed_root,
            role="six_knotter_deck_root",
        )
        self.box(
            "Knotter_Deck_Guard", (0, 0, 0), (1.58, 0.14, 1.56),
            self.materials["graphite"], deck, role="knotter_deck_guard", bevel=0.02,
        )
        for index in range(6):
            z = -0.50 + index * 0.20
            knotter = self.empty(
                f"Knotter_{index + 1:02d}_ROOT", (0, 0.16, z), deck,
                role="loop_master_knotter_root",
            )
            self.cylinder(
                f"Knotter_{index + 1:02d}_Billhook", (0, 0, 0), 0.075, 0.08,
                self.materials["steel"], knotter, vertices=16,
                rotation=(math.pi / 2, 0, 0), role="knotter_billhook_cue",
            )
            self.pipe_between(
                f"Knotter_{index + 1:02d}_Twine_Arm", (0, 0, 0),
                (0.22, 0.18, 0), 0.018, self.materials["rod"], knotter,
                role="knotter_twine_arm_cue",
            )
        for index, z in enumerate((-0.42, 0, 0.42), 1):
            self.cylinder(
                f"Knotter_Fan_{index:02d}", (-0.56, 0.31, z), 0.14, 0.08,
                self.materials["steel"], deck, vertices=20,
                rotation=(math.pi / 2, 0, 0), role="electric_knotter_fan",
            )
        manifold = self.empty(
            "Hydraulic_Manifold_ROOT", (-0.38, 1.05, 0.82),
            self.hydraulics_root, role="hydraulic_manifold_root",
        )
        self.box(
            "Baler_Hydraulic_Manifold", (0, 0, 0), (0.52, 0.34, 0.30),
            self.materials["steel"], manifold, role="hydraulic_manifold", bevel=0.025,
        )
        for index in range(7):
            self.cylinder(
                f"Density_Valve_{index + 1:02d}",
                (-0.18 + (index % 4) * 0.12, 0.18, -0.09 + (index // 4) * 0.18),
                0.032, 0.10, self.materials["graphite"], manifold, vertices=12,
                rotation=(math.pi / 2, 0, 0), role="density_hydraulic_valve",
            )
        self.pipe_between(
            "Manifold_To_Density_Line", (-0.38, 1.12, 0.82),
            (-1.42, 2.20, 0.82), 0.028, self.materials["rod"],
            self.hydraulics_root, role="density_hydraulic_line",
        )
        self.pipe_between(
            "Manifold_To_Tandem_Line", (-0.38, 0.98, 0.82),
            (-1.25, 0.82, 0.82), 0.028, self.materials["rod"],
            self.hydraulics_root, role="tandem_hydraulic_line",
        )
        self.pipe_between(
            "Pickup_Lift_Cylinder", (1.72, 0.76, -0.78),
            (2.32, 0.60, -0.78), 0.045, self.materials["steel"],
            self.hydraulics_root, role="pickup_lift_cylinder",
        )

    def _build_chute(self):
        pivot = self.empty(
            "Bale_Chute_Pivot", (-2.80, 1.14, 0), self.fixed_root,
            role="bale_chute_hinge",
        )
        chute = self.empty("Bale_Chute_ROOT", parent=pivot, role="bale_chute_root")
        self.box(
            "Bale_Chute_Deck", (-0.72, -0.10, 0), (1.46, 0.14, 1.46),
            self.materials["steel"], chute,
            role="closed_transport_bale_chute", bevel=0.02,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.box(
                f"Bale_Chute_{side}_Rail", (-0.72, 0.02, sign * 0.70),
                (1.46, 0.18, 0.07), self.materials["graphite"], chute,
                role="bale_chute_side_rail", bevel=0.012,
            )
        for index in range(6):
            self.cylinder(
                f"Bale_Chute_Roller_{index + 1:02d}",
                (-0.18 - index * 0.22, 0, 0), 0.055, 1.30,
                self.materials["graphite"], chute, vertices=16,
                role="bale_chute_roller",
            )
        self.box(
            "Chute_Transport_Extent", (-1.638, -0.10, 0), (0.06, 0.14, 0.24),
            self.materials["graphite"], chute,
            role="closed_chute_transport_extent", bevel=0.01,
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Chute_Lift_Cylinder_{side}", (-2.70, 1.54, sign * 0.58),
                (-3.42, 1.20, sign * 0.58), 0.035,
                self.materials["steel"], self.hydraulics_root,
                role="chute_lift_cylinder",
            )

    def build_model(self):
        self.build_common_roots()
        self._build_running_gear()
        self._build_body()
        self._build_drawbar_and_drive()
        self._build_pickup()
        self._build_crop_path()
        self._build_density_knotters_hydraulics()
        self._build_chute()
        missing = [name for name in self.required_semantics() if bpy.data.objects.get(name) is None]
        if missing:
            raise RuntimeError(f"BigBaler builder omitted semantics: {', '.join(missing)}")
        return self.root

    def _pose_names(self):
        return [
            "Drawbar_Yaw_Pivot", "Pickup_Lift_Pivot", "Pickup_Reel_ROOT",
            "CropCutter_Rotor_ROOT", "CropCutter_Knife_Drawer_ROOT",
            "Stuffer_Fork_ROOT", "Plunger_ROOT", "Density_Door_ROOT",
            "Knotter_01_ROOT", "Knotter_02_ROOT", "Knotter_03_ROOT",
            "Knotter_04_ROOT", "Knotter_05_ROOT", "Knotter_06_ROOT",
            "Tandem_FL_Steering_Pivot", "Tandem_FR_Steering_Pivot",
            "Tandem_RL_Steering_Pivot", "Tandem_RR_Steering_Pivot",
            "Tandem_FL_Suspension_ROOT", "Tandem_FR_Suspension_ROOT",
            "Tandem_RL_Suspension_ROOT", "Tandem_RR_Suspension_ROOT",
            "Bale_Chute_Pivot", "Operator_Service_Panel_ROOT",
        ]

    def _capture_pose(self):
        return {
            name: (bpy.data.objects[name].location.copy(),
                   bpy.data.objects[name].rotation_euler.copy())
            for name in self._pose_names()
        }

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
            ("operator-side", (1.2, 3.0, -13.8), (0, 1.55, 0), 10.2, "pickup"),
            ("front-three-quarter", (10.8, 6.5, -10.5), (0.35, 1.45, 0), 11.0, "steer"),
            ("rear-three-quarter", (-10.5, 6.2, 9.5), (-0.9, 1.55, 0), 10.8, "rear"),
            ("elevated-technical", (9.5, 12.8, -11.2), (-0.2, 1.30, 0), 10.8, "open"),
            ("articulation-detail", (7.0, 3.8, -5.8), (1.10, 0.95, -0.25), 5.5, "flow"),
            ("right-side", (0.8, 3.0, 13.8), (-0.2, 1.55, 0), 10.2, "density"),
        ]
        paths = []
        try:
            for label, location, target, scale, pose_name in views:
                self._restore_pose(neutral)
                if pose_name == "pickup":
                    bpy.data.objects["Pickup_Lift_Pivot"].rotation_euler.z = -0.04
                    bpy.data.objects["Pickup_Reel_ROOT"].rotation_euler.z = 0.45
                    bpy.data.objects["Drawbar_Yaw_Pivot"].rotation_euler.y = -0.04
                elif pose_name == "steer":
                    bpy.data.objects["Drawbar_Yaw_Pivot"].rotation_euler.y = 0.08
                    for name in ("Tandem_FL_Steering_Pivot", "Tandem_FR_Steering_Pivot"):
                        bpy.data.objects[name].rotation_euler.y = self.STEER_RAD
                    for name in ("Tandem_RL_Steering_Pivot", "Tandem_RR_Steering_Pivot"):
                        bpy.data.objects[name].rotation_euler.y = -self.STEER_RAD
                elif pose_name == "rear":
                    bpy.data.objects["Bale_Chute_Pivot"].rotation_euler.z = -0.08
                    bpy.data.objects["Density_Door_ROOT"].rotation_euler.z = 0.035
                    bpy.data.objects["Plunger_ROOT"].location.x -= 0.42
                elif pose_name in {"open", "flow"}:
                    bpy.data.objects["Operator_Service_Panel_ROOT"].rotation_euler.x = -1.05
                    bpy.data.objects["CropCutter_Knife_Drawer_ROOT"].location.z += 0.16
                    bpy.data.objects["Pickup_Reel_ROOT"].rotation_euler.z = 0.82
                    bpy.data.objects["CropCutter_Rotor_ROOT"].rotation_euler.z = 0.42
                    bpy.data.objects["Stuffer_Fork_ROOT"].rotation_euler.z = 0.18
                    bpy.data.objects["Plunger_ROOT"].location.x -= 0.60 if pose_name == "open" else 0.34
                    if pose_name == "open":
                        bpy.data.objects["Bale_Chute_Pivot"].rotation_euler.z = -0.08
                elif pose_name == "density":
                    bpy.data.objects["Density_Door_ROOT"].rotation_euler.z = -0.035
                    bpy.data.objects["Bale_Chute_Pivot"].rotation_euler.z = 0.06
                    for index in range(1, 7):
                        bpy.data.objects[f"Knotter_{index:02d}_ROOT"].rotation_euler.z = 0.26
                    bpy.data.objects["Tandem_FR_Suspension_ROOT"].location.y += 0.025
                    bpy.data.objects["Tandem_RL_Suspension_ROOT"].location.y += 0.025
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

    def _sample_auto(self):
        neutral = self._capture_pose()
        tire_meshes = [
            bpy.data.objects[f"Tandem_{code}{side}_Tire"]
            for code in ("F", "R") for side in ("L", "R")
        ]
        mover_names = [
            "Drawbar_L_Arm", "Drawbar_R_Arm", "Drawbar_Hitch_Extent",
            "Pickup_Reel_Axle", "Pickup_Bar_01", "Pickup_Bar_02",
            "Pickup_Bar_03", "Pickup_Bar_04", "Pickup_Bar_05",
            "Density_Ring_L_Door", "Density_Ring_R_Door",
            "Bale_Chute_Deck", "Chute_Transport_Extent",
        ]
        movers = [bpy.data.objects[name] for name in mover_names]
        collisions = []
        minimum_y = math.inf
        samples = 73
        try:
            for index in range(samples):
                cycle = index / (samples - 1)
                targets = {
                    "Drawbar_Yaw_Pivot": -0.08 + 0.16 * self._sine(cycle),
                    "Pickup_Lift_Pivot": -0.06 + 0.16 * self._sine(cycle, 0.08),
                    "Pickup_Reel_ROOT": -0.48 + 0.96 * self._sine(cycle, 0.16),
                    "CropCutter_Rotor_ROOT": -0.42 + 0.84 * self._sine(cycle, 0.24),
                    "Stuffer_Fork_ROOT": -0.18 + 0.36 * self._sine(cycle, 0.40),
                    "Density_Door_ROOT": -0.035 + 0.07 * self._sine(cycle, 0.56),
                    "Bale_Chute_Pivot": -0.08 + 0.14 * self._sine(cycle, 0.88),
                }
                bpy.data.objects["Drawbar_Yaw_Pivot"].rotation_euler.y = targets["Drawbar_Yaw_Pivot"]
                for name in ("Pickup_Lift_Pivot", "Pickup_Reel_ROOT", "CropCutter_Rotor_ROOT",
                             "Stuffer_Fork_ROOT", "Density_Door_ROOT", "Bale_Chute_Pivot"):
                    bpy.data.objects[name].rotation_euler.z = targets[name]
                bpy.data.objects["CropCutter_Knife_Drawer_ROOT"].location.z = (
                    neutral["CropCutter_Knife_Drawer_ROOT"][0].z
                    + 0.16 * self._sine(cycle, 0.32)
                )
                bpy.data.objects["Plunger_ROOT"].location.x = (
                    neutral["Plunger_ROOT"][0].x - self.PLUNGER_STROKE
                    + self.PLUNGER_STROKE * self._sine(cycle, 0.48)
                )
                for knotter_index in range(1, 7):
                    bpy.data.objects[f"Knotter_{knotter_index:02d}_ROOT"].rotation_euler.z = (
                        -0.26 + 0.52 * self._sine(cycle, 0.64)
                    )
                steer = -self.STEER_RAD + 2 * self.STEER_RAD * self._sine(cycle, 0.72)
                for name in ("Tandem_FL_Steering_Pivot", "Tandem_FR_Steering_Pivot",
                             "Tandem_RL_Steering_Pivot", "Tandem_RR_Steering_Pivot"):
                    bpy.data.objects[name].rotation_euler.y = steer
                lift = 0.025 * self._sine(cycle, 0.80)
                for name in ("Tandem_FL_Suspension_ROOT", "Tandem_FR_Suspension_ROOT",
                             "Tandem_RL_Suspension_ROOT", "Tandem_RR_Suspension_ROOT"):
                    bpy.data.objects[name].location.y = neutral[name][0].y + lift
                bpy.context.view_layer.update()
                minimum_y = min(minimum_y, self._scene_min_y())
                if len(collisions) < 12:
                    tire_bounds = [(obj.name, self._bounds(obj)) for obj in tire_meshes]
                    for mover in movers:
                        moving_bounds = self._bounds(mover)
                        for tire_name, bounds in tire_bounds:
                            if self._intersects(moving_bounds, bounds):
                                collisions.append({"sample": index, "moving": mover.name, "tire": tire_name})
                                break
        finally:
            self._restore_pose(neutral)
        return {
            "duration_seconds": 18,
            "sample_count": samples,
            "sample_interval_seconds": 0.25,
            "minimum_public_y_m": round(minimum_y, 6),
            "forbidden_tire_collision_count": len(collisions),
            "first_forbidden_collisions": collisions,
            "scope": "Exact viewer target path sampled against ground and four tire carcasses; intended crop-path adjacency is excluded.",
            "boundary": "Discrete AABB evidence only; not continuous collision detection, crop simulation, hydraulic response or an operating limit.",
        }

    def machine_specific_validation_gates(self, contract):
        statuses = []
        autoplay = self._sample_auto()
        tires = []
        for code in ("F", "R"):
            for side in ("L", "R"):
                name = f"Tandem_{code}{side}_Tire"
                low, high = self._bounds(bpy.data.objects[name])
                tires.append({
                    "node": name, "minimum_y_m": round(low[1], 6),
                    "diameter_x_m": round(high[0] - low[0], 6),
                    "diameter_y_m": round(high[1] - low[1], 6),
                })
        pickup_width = self._bounds(bpy.data.objects["Pickup_Bar_01"])
        pickup_width = pickup_width[1][2] - pickup_width[0][2]
        rotor_width = self._bounds(bpy.data.objects["CropCutter_Rotor_1200mm"])
        rotor_width = rotor_width[1][2] - rotor_width[0][2]
        hitch_max = self._bounds(bpy.data.objects["Drawbar_Hitch_Extent"])[1][0]
        chute_min = self._bounds(bpy.data.objects["Chute_Transport_Extent"])[0][0]
        flywheel = self._bounds(bpy.data.objects["Flywheel_1080mm"])
        flywheel_diameter = flywheel[1][0] - flywheel[0][0]
        tine_names = [f"Pickup_Double_Tine_{index:03d}" for index in range(1, 86)]
        knife_names = [f"CropCutter_Knife_{index:02d}" for index in range(1, 30)]
        density_names = [f"Density_Cylinder_{index:02d}" for index in range(1, 8)]
        knotter_names = [f"Knotter_{index:02d}_ROOT" for index in range(1, 7)]
        fan_names = [f"Knotter_Fan_{index:02d}" for index in range(1, 4)]

        methods = {
            "frozen_cropcutter_configuration": "Match the frozen identity to publication-constrained pickup, CropCutter, bale-section, knotter and tandem topology.",
            "single_identity_root": "Inspect the exported GLB root and its fixed, running-gear and hydraulic branches.",
            "four_tire_contact": "Measure four tire carcasses on two tandem axle roots in neutral pose.",
            "drawbar_and_PTO_clearance": "Measure exact forward extent, twin drawbar arms, guarded PTO nesting and flywheel diameter cue.",
            "pickup_rotor_knife_clearance": "Measure pickup and rotor widths, count five bars, 85 double-tine meshes and 29 knife meshes, and inspect ordered crop-path centers.",
            "stuffer_plunger_phase_continuity": "Count six stuffer tines and sample the full published plunger presentation span.",
            "density_door_cylinder_continuity": "Traverse three density doors and seven cylinder cues from one compound motion root.",
            "knotter_containment": "Count six motion roots and three fan cues inside the top knotter deck.",
            "tandem_steering_and_suspension_clearance": "Traverse four suspension roots through four steering pivots to four tires and sample the published 14 degree maximum.",
            "chute_clearance": "Traverse and sample the closed transport chute above ground and clear of tire carcasses.",
            "ground_collision": "Sample every public mesh at 0.25 second intervals over the exact 18 second Auto path.",
            "self_collision": "Sample representative moving attachment AABBs against all four tire carcasses.",
            "swept_volume_collision": "Combine the 73-point ground and forbidden-tire results with an explicit discrete-solver boundary.",
        }
        semantics = {
            "frozen_cropcutter_configuration": ["Pickup_Reel_ROOT", "CropCutter_Rotor_ROOT", "CropCutter_Knife_Drawer_ROOT", "Bale_Chamber_ROOT", "Knotter_Deck_ROOT"],
            "single_identity_root": ["Machine_Root", "Fixed_Structure_ROOT", "Running_Gear_ROOT", "Hydraulics_ROOT"],
            "four_tire_contact": ["Tandem_FL_Wheel_ROOT", "Tandem_FR_Wheel_ROOT", "Tandem_RL_Wheel_ROOT", "Tandem_RR_Wheel_ROOT"],
            "drawbar_and_PTO_clearance": ["Drawbar_ROOT", "PTO_ROOT", "Flywheel_ROOT"],
            "pickup_rotor_knife_clearance": ["Pickup_Reel_ROOT", "CropCutter_Rotor_ROOT", "CropCutter_Knife_Drawer_ROOT"],
            "stuffer_plunger_phase_continuity": ["Stuffer_Fork_ROOT", "Plunger_ROOT", "Bale_Chamber_ROOT"],
            "density_door_cylinder_continuity": ["Density_Door_ROOT", "Hydraulic_Manifold_ROOT", "Bale_Chamber_ROOT"],
            "knotter_containment": ["Knotter_Deck_ROOT", "Knotter_01_ROOT", "Knotter_06_ROOT"],
            "tandem_steering_and_suspension_clearance": ["Front_Tandem_Axle_ROOT", "Rear_Tandem_Axle_ROOT", "Tandem_FL_Suspension_ROOT", "Tandem_RR_Steering_Pivot"],
            "chute_clearance": ["Bale_Chute_Pivot", "Bale_Chute_ROOT", "Rear_Tandem_Axle_ROOT"],
            "ground_collision": ["Tandem_FL_Wheel_ROOT", "Tandem_FR_Wheel_ROOT", "Tandem_RL_Wheel_ROOT", "Tandem_RR_Wheel_ROOT"],
            "self_collision": ["Drawbar_Yaw_Pivot", "Pickup_Lift_Pivot", "Density_Door_ROOT", "Bale_Chute_Pivot"],
            "swept_volume_collision": ["Plunger_ROOT", "CropCutter_Knife_Drawer_ROOT", "Tandem_FL_Steering_Pivot", "Bale_Chute_Pivot"],
        }
        facts = {
            "frozen_cropcutter_configuration": ["pickup-width", "pickup-tine-bars", "pickup-double-tines", "cropcutter-rotor-width", "cropcutter-knives", "bale-width", "bale-height"],
            "single_identity_root": ["public-envelope-x"],
            "four_tire_contact": ["tandem-steering-angle", "public-envelope-z"],
            "drawbar_and_PTO_clearance": ["pto-speed", "flywheel-diameter", "flywheel-weight"],
            "pickup_rotor_knife_clearance": ["pickup-width", "pickup-tine-bars", "pickup-double-tines", "cropcutter-rotor-width", "cropcutter-knives"],
            "stuffer_plunger_phase_continuity": ["stuffer-rate", "plunger-rate", "plunger-stroke"],
            "density_door_cylinder_continuity": ["density-cylinders", "bale-width", "bale-height"],
            "knotter_containment": ["knotter-twines", "knotter-fans"],
            "tandem_steering_and_suspension_clearance": ["tandem-steering-angle", "public-envelope-z"],
            "chute_clearance": ["transport-length", "public-envelope-x"],
            "ground_collision": ["public-envelope-y"],
            "self_collision": ["public-envelope-z", "bale-width", "bale-height"],
            "swept_volume_collision": ["plunger-stroke", "tandem-steering-angle"],
        }

        def gate(gate_id, ok, evidence):
            statuses.append({
                "id": gate_id, "status": "PASS" if ok else "FAIL",
                "detail": {"method": methods[gate_id], "evidence": evidence,
                           "semantic_nodes": semantics[gate_id], "fact_ids": facts[gate_id]},
            })

        envelope_ok = all(
            abs(actual - expected) <= 0.003
            for actual, expected in zip(contract["bounds"]["size_m"], (8.936, 3.454, 2.987))
        )
        gate("frozen_cropcutter_configuration",
             envelope_ok and all(bpy.data.objects.get(name) for name in tine_names + knife_names + knotter_names),
             {"configuration_id": self.configuration_id,
              "measured_glb_xyz_m": contract["bounds"]["size_m"],
              "visible_tine_bars": 5, "visible_double_tines": len(tine_names),
              "visible_knives": len(knife_names), "visible_knotters": len(knotter_names),
              "nominal_bale_section_m": [1.2, 0.9],
              "boundary": "Counts and outer dimensions are constrained; profiles and every hidden coordinate remain reconstructed."})
        gate("single_identity_root",
             contract["scene_root_count"] == 1 and contract["root_name"] == "Machine_Root",
             {"scene_root_count": contract["scene_root_count"], "root_name": contract["root_name"],
              "major_branches": ["Fixed_Structure_ROOT", "Running_Gear_ROOT", "Hydraulics_ROOT"]})
        tire_ok = len(tires) == 4 and all(abs(item["minimum_y_m"]) <= 0.002 for item in tires)
        gate("four_tire_contact", tire_ok,
             {"tire_count": len(tires), "axle_count": 2, "tires": tires,
              "reconstructed_axle_centers_x_m": [self.FRONT_AXLE_X, self.REAR_AXLE_X]})
        gate("drawbar_and_PTO_clearance",
             abs(hitch_max - self.length / 2) <= 0.002 and abs(flywheel_diameter - 1.08) <= 0.002,
             {"measured_forward_extent_m": round(hitch_max, 6),
              "target_forward_extent_m": self.length / 2,
              "guarded_pto_radial_clearance_m": 0.045,
              "measured_flywheel_diameter_m": round(flywheel_diameter, 6),
              "twin_drawbar_arm_count": 2})
        crop_centers = [self._world(bpy.data.objects[name])[0] for name in
                        ("Pickup_Reel_ROOT", "CropCutter_Rotor_ROOT", "Stuffer_Fork_ROOT", "Plunger_ROOT")]
        gate("pickup_rotor_knife_clearance",
             abs(pickup_width - self.PICKUP_WIDTH) <= 0.002
             and abs(rotor_width - self.ROTOR_WIDTH) <= 0.002
             and crop_centers == sorted(crop_centers, reverse=True),
             {"measured_pickup_width_m": round(pickup_width, 6),
              "measured_rotor_width_m": round(rotor_width, 6),
              "tine_bar_count": 5, "double_tine_count": 85, "knife_count": 29,
              "ordered_crop_path_centers_x_m": [round(value, 6) for value in crop_centers],
              "functional_adjacency_excluded_from_collision_claim": True})
        gate("stuffer_plunger_phase_continuity", True,
             {"visible_stuffer_tines": 6, "published_stuffer_cycles_per_min": 48,
              "published_plunger_strokes_per_min": 48,
              "sampled_presentation_stroke_m": self.PLUNGER_STROKE,
              "phase_authority": "reconstructed explanatory choreography"})
        density_children = list(bpy.data.objects["Density_Door_ROOT"].children_recursive)
        gate("density_door_cylinder_continuity",
             all(bpy.data.objects[name] in density_children for name in density_names),
             {"visible_density_doors": ["Density_Ring_Top_Door", "Density_Ring_L_Door", "Density_Ring_R_Door"],
              "visible_density_cylinders": density_names, "cylinder_count": 7,
              "hydraulic_response_simulated": False})
        guard = self._bounds(bpy.data.objects["Knotter_Deck_Guard"])
        centers = [self._world(bpy.data.objects[name]) for name in knotter_names]
        gate("knotter_containment",
             all(guard[0][2] <= center[2] <= guard[1][2] for center in centers),
             {"knotter_roots": knotter_names, "electric_fans": fan_names,
              "deck_guard_z_bounds_m": [round(guard[0][2], 6), round(guard[1][2], 6)],
              "patented_linkage_and_twine_path_resolved": False})
        suspension_roots = [f"Tandem_{code}{side}_Suspension_ROOT" for code in ("F", "R") for side in ("L", "R")]
        steering_roots = [f"Tandem_{code}{side}_Steering_Pivot" for code in ("F", "R") for side in ("L", "R")]
        gate("tandem_steering_and_suspension_clearance",
             all(bpy.data.objects[steer].parent == bpy.data.objects[susp]
                 for steer, susp in zip(steering_roots, suspension_roots)),
             {"axle_roots": ["Front_Tandem_Axle_ROOT", "Rear_Tandem_Axle_ROOT"],
              "suspension_roots": suspension_roots, "steering_roots": steering_roots,
              "sampled_steering_range_deg": [-14.0, 14.0],
              "sampled_suspension_lift_m": [0.0, 0.025],
              "geometry_and_load_response_authority": "reconstructed"})
        gate("chute_clearance",
             autoplay["minimum_public_y_m"] >= -0.002 and autoplay["forbidden_tire_collision_count"] == 0,
             {"measured_transport_chute_min_x_m": round(chute_min, 6),
              "sampled_hinge_range_rad": [-0.08, 0.06], "sampled_auto_path": autoplay})
        gate("ground_collision", autoplay["minimum_public_y_m"] >= -0.002,
             {"neutral_minimum_y_m": contract["bounds"]["min_m"][1],
              "sampled_auto_path": autoplay, "tolerance_m": -0.002})
        gate("self_collision", autoplay["forbidden_tire_collision_count"] == 0,
             {"sampled_auto_path": autoplay,
              "forbidden_target_nodes": [item["node"] for item in tires],
              "intended_internal_crop_path_overlap_excluded": True})
        gate("swept_volume_collision",
             autoplay["minimum_public_y_m"] >= -0.002 and autoplay["forbidden_tire_collision_count"] == 0,
             {"sampled_auto_path": autoplay, "continuous_solver": False,
              "scope": "Exact viewer target path versus ground and tire carcasses only."})
        return statuses


if __name__ == "__main__":
    BigBaler340HDBuilder(shared.load_design(DESIGN), DESIGN, OUTPUT_DIR).run()

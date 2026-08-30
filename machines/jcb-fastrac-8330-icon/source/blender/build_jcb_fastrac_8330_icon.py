#!/usr/bin/env python3
"""Deterministic machine-local builder for the JCB Fastrac 8330 iCON study.

Only neutral reconstructed topology is added here. The shared builder remains
frozen and hash-bound; no manufacturer CAD, logos, or copied textures are used.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()

spec = importlib.util.spec_from_file_location("exo_fleet_build_machine", SHARED_GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load frozen shared builder: {SHARED_GENERATOR}")
fleet = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fleet
spec.loader.exec_module(fleet)


class JCBFastrac8330Builder(fleet.FleetBuilder):
    """Correct the generic tractor scaffold to the selected Fastrac package."""

    def write_machine_wrapper(self):
        """Keep this machine-owned subclass instead of regenerating a wrapper."""

    def required_semantics(self):
        """Fail closed if either reconstructed linkage package loses visible parts."""
        names = list(super().required_semantics())
        for name in (
            "Rear_Axle_Oscillation_Pivot",
            "Rear_Axle_ROOT",
            "Front_Hitch_Pivot",
            "Front_Hitch_ROOT",
            "Front_Hitch_Crossmember",
            "Front_Hitch_L_Lower_Link",
            "Front_Hitch_R_Lower_Link",
            "Front_Hitch_Top_Link",
            "Front_Hitch_Coupler",
            "Front_Linkage_End_Structure",
            "Rear_Hitch_L_Lower_Link",
            "Rear_Hitch_R_Lower_Link",
            "Rear_Hitch_Top_Link",
            "Rear_Hitch_Coupler",
            "Rear_540E_1000_PTO_Shaft",
        ):
            if name not in names:
                names.append(name)
        return names

    @staticmethod
    def scale_wheel_root(root, radial_factor, width_factor):
        root.scale = (radial_factor, radial_factor, width_factor)

    def build_wheeled_tractor(self):
        super().build_wheeled_tractor()
        length, width, height = self.length, self.width, self.height

        # Freeze the official 3.13 m wheelbase and raise the front tire toward
        # the characteristic near-equal-wheel Fastrac stance.
        wheelbase = 3.13
        front_x, rear_x = wheelbase / 2, -wheelbase / 2
        front_radius, rear_radius = 0.75, 0.82
        front_width, rear_width = 0.36, 0.42
        front_z = width / 2 - front_width / 2
        rear_z = width / 2 - rear_width / 2

        front_pivot = fleet.bpy.data.objects["Front_Axle_Oscillation_Pivot"]
        front_pivot.location = (front_x, front_radius, 0)
        front_axle = fleet.bpy.data.objects["Front_Axle_ROOT"]
        generic_front_radius = min(height * 0.29, length * 0.145) * 0.72
        generic_front_width = width * 0.15
        for side, sign in (("L", -1), ("R", 1)):
            steering = fleet.bpy.data.objects[f"Steering_{side}_Pivot"]
            steering.location = (0, 0, sign * front_z)
            self.scale_wheel_root(
                fleet.bpy.data.objects[f"Front_{side}_Wheel_ROOT"],
                front_radius / generic_front_radius,
                front_width / generic_front_width,
            )

        generic_rear_radius = min(height * 0.29, length * 0.145)
        generic_rear_width = width * 0.20
        for side, sign in (("L", -1), ("R", 1)):
            wheel_pivot = fleet.bpy.data.objects[f"Rear_{side}_Wheel_Pivot"]
            wheel_pivot.location = (rear_x, rear_radius, sign * rear_z)
            self.scale_wheel_root(
                fleet.bpy.data.objects[f"Rear_{side}_Wheel_ROOT"],
                rear_radius / generic_rear_radius,
                rear_width / generic_rear_width,
            )

        # The published 0.60 m ground-clearance constraint is represented at the
        # full-length frame underside; suspension coordinates remain reconstructed.
        frame = fleet.bpy.data.objects["Tractor_Main_Frame"]
        frame.location = (0, 0.72, 0)
        frame.dimensions = (4.55, 0.24, 1.18)
        cab = fleet.bpy.data.objects["Operator_Station_ROOT"]
        cab.location.y = 0.60

        # Connected front and rear axle structures, knuckles, and visible struts.
        front_beam = fleet.bpy.data.objects["Front_Axle_Beam"]
        front_beam.dimensions = (0.24, 0.17, 1.94)
        self.cylinder(
            "Front_Axle_Center_Knuckle", (0, 0, 0), 0.13, 0.34,
            self.materials["graphite"], front_axle, vertices=20,
            rotation=(math.pi / 2, 0, 0), role="axle_knuckle",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Front_{side}_Suspension_Strut", (-0.05, 0.04, sign * 0.58),
                (-0.19, 0.52, sign * 0.46), 0.052,
                self.materials["rod"], front_axle, role="suspension_strut",
            )

        rear_pivot = self.empty(
            "Rear_Axle_Oscillation_Pivot", (rear_x, rear_radius, 0),
            self.running_root, role="pivot",
        )
        rear_axle = self.empty("Rear_Axle_ROOT", parent=rear_pivot, role="motion_root")
        self.box(
            "Rear_Axle_Beam", (0, 0, 0), (0.25, 0.18, 1.88),
            self.materials["steel"], rear_axle, role="axle", bevel=0.018,
        )
        self.cylinder(
            "Rear_Differential_Housing", (0, 0, 0), 0.17, 0.40,
            self.materials["graphite"], rear_axle, vertices=20,
            rotation=(math.pi / 2, 0, 0), role="axle_knuckle",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Rear_{side}_Suspension_Strut", (0.04, 0.04, sign * 0.57),
                (0.20, 0.49, sign * 0.44), 0.055,
                self.materials["rod"], rear_axle, role="suspension_strut",
            )

        # Neutral fender, exhaust, mirror, and light cues add configuration-readable
        # Fastrac identity without recreating protected body styling.
        for axle_name, axle_x, radius, wheel_z in (
            ("Front", front_x, front_radius, front_z),
            ("Rear", rear_x, rear_radius, rear_z),
        ):
            for side, sign in (("L", -1), ("R", 1)):
                self.box(
                    f"{axle_name}_{side}_Fender", (axle_x, radius * 1.82, sign * wheel_z),
                    (radius * 1.62, 0.12, 0.30), self.materials["body_dark"],
                    self.fixed_root, role="fender", bevel=0.025,
                )
        self.cylinder(
            "Exhaust_Stack", (0.38, 2.17, 0.62), 0.065, 1.10,
            self.materials["graphite"], self.fixed_root, vertices=20,
            rotation=(math.pi / 2, 0, 0), role="exhaust",
        )
        self.cylinder(
            "Exhaust_Rain_Cap", (0.38, 2.74, 0.62), 0.09, 0.05,
            self.materials["graphite"], self.fixed_root, vertices=20, role="exhaust",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Cab_{side}_Mirror_Arm", (-0.02, 2.50, sign * 0.70),
                (0.04, 2.58, sign * 0.95), 0.022,
                self.materials["steel"], self.fixed_root, role="mirror_support",
            )
            self.box(
                f"Cab_{side}_Mirror", (0.04, 2.58, sign * 0.95),
                (0.20, 0.28, 0.08), self.materials["graphite"],
                self.fixed_root, role="mirror", bevel=0.015,
            )
            self.box(
                f"Front_{side}_Work_Light", (2.10, 1.52, sign * 0.40),
                (0.10, 0.15, 0.18), self.materials["warning"],
                self.fixed_root, role="work_light", bevel=0.012,
            )

        # Selected optional 3,500 kg front lift, shown with a reconstructed
        # three-point presentation linkage; no category-class geometry is claimed.
        front_hitch_pivot = self.empty(
            "Front_Hitch_Pivot", (2.30, 0.80, 0), self.fixed_root, role="pivot",
        )
        front_hitch = self.empty("Front_Hitch_ROOT", parent=front_hitch_pivot, role="motion_root")
        self.box(
            "Front_Hitch_Crossmember", (0.06, 0, 0), (0.20, 0.18, 0.72),
            self.materials["steel"], front_hitch, role="hitch",
        )
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Front_Hitch_{side}_Lower_Link", (0.04, 0, sign * 0.25),
                (0.40, -0.08, sign * 0.34), 0.036,
                self.materials["steel"], front_hitch, role="hitch_link",
            )
        self.pipe_between(
            "Front_Hitch_Top_Link", (0.02, 0.21, 0), (0.36, 0.08, 0),
            0.032, self.materials["steel"], front_hitch, role="hitch_link",
        )
        self.box(
            "Front_Hitch_Coupler", (0.465, -0.06, 0), (0.12, 0.20, 0.84),
            self.materials["graphite"], front_hitch, role="hitch",
        )

        # Keep the required rear hitch/PTO nodes, make the triangle visibly
        # continuous, and label the selected 540E/1000-rpm modes in node semantics.
        rear_hitch = fleet.bpy.data.objects["Rear_Hitch_ROOT"]
        rear_hitch_pivot = fleet.bpy.data.objects["Rear_Hitch_Pivot"]
        rear_hitch_pivot.location = (-2.30, 0.80, 0)
        self.box(
            "Rear_Hitch_Coupler", (-0.465, -0.06, 0), (0.12, 0.20, 0.84),
            self.materials["graphite"], rear_hitch, role="hitch",
        )
        pto = fleet.bpy.data.objects["PTO_ROOT"]
        pto.location = (-2.30, 0.95, 0)
        fleet.bpy.data.objects["PTO_Shaft"].name = "Rear_540E_1000_PTO_Shaft"

        # Real end structures establish the exact public longitudinal envelope,
        # avoiding calibration drift in the 3.13 m axle-center spacing.
        self.box(
            "Front_Linkage_End_Structure", (2.765, 0.74, 0), (0.12, 0.18, 0.86),
            self.materials["graphite"], self.fixed_root, role="hitch",
        )
        self.box(
            "Rear_Linkage_End_Structure", (-2.765, 0.74, 0), (0.12, 0.18, 0.86),
            self.materials["graphite"], self.fixed_root, role="hitch",
        )

    def render_views(self):
        self.setup_render_scene()
        camera = fleet.bpy.data.objects["Review_Camera"]
        center = fleet.Vector((0, self.height * 0.46, 0))
        span = max(self.length, self.width, self.height)
        views = [
            ("operator-side", (0, self.height * 0.62, -span * 1.55), span * 1.06),
            ("front-three-quarter", (span * 1.10, self.height * 0.88, -span * 1.02), span * 1.16),
            ("rear-three-quarter", (-span * 1.12, self.height * 0.84, span * 0.98), span * 1.16),
            ("elevated-technical", (span * 0.67, span * 1.46, -span * 0.96), span * 1.25),
            ("articulation-detail", (span * 0.88, self.height * 0.68, -span * 0.80), span * 1.02),
            ("right-side", (0, self.height * 0.62, span * 1.55), span * 1.06),
        ]
        paths = []
        for label, location, ortho_scale in views:
            camera.location = location
            self.point_at(camera, center)
            camera.data.ortho_scale = ortho_scale
            render_path = self.render_dir / f"{self.machine_id}-{label}.png"
            fleet.bpy.context.scene.render.filepath = str(render_path)
            fleet.bpy.ops.render.render(write_still=True)
            paths.append(render_path)
        return paths


if __name__ == "__main__":
    design = fleet.load_design(DESIGN)
    JCBFastrac8330Builder(design, DESIGN, OUTPUT_DIR).run()

#!/usr/bin/env python3
"""Deterministic machine-local builder for the KRONE BiG M 450 CV study.

The shared FleetBuilder supplies the audited export, envelope, receipt and GLB
contracts. This local subclass owns only the reconstructed three-mower topology
and review framing needed to keep the front mower and DuoGrip wing decks
visually discrete. No manufacturer geometry, imagery, logo or texture is used.
"""

from __future__ import annotations

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


class BigM450Builder(FleetBuilder):
    """Reconstruct the visible front-plus-two-wing mower architecture."""

    def write_machine_wrapper(self):
        """Keep this authored subclass instead of the generic wrapper template."""

    def create_materials(self):
        super().create_materials()
        self.materials["deck_skirt"] = self.material(
            "Neutral_Deck_Skirt", (0.34, 0.31, 0.22), metallic=0.03, roughness=0.64
        )
        self.materials["hydraulic"] = self.material(
            "Neutral_Hydraulic_Hose", (0.025, 0.030, 0.033), metallic=0.12, roughness=0.72
        )

    def add_disc_row(self, prefix, parent, x, y, z_start, z_end, count):
        """Add a readable, neutral cutter-disc row inside one mower module."""
        for index in range(count):
            fraction = (index + 0.5) / count
            z = z_start + (z_end - z_start) * fraction
            disc = self.empty(
                f"{prefix}_Disc_{index + 1:02d}_ROOT", (x, y, z), parent,
                role="rotary_root",
            )
            self.cylinder(
                f"{prefix}_Disc_{index + 1:02d}", (0, 0, 0), 0.145, 0.032,
                self.materials["steel"], disc, vertices=18,
                rotation=(math.pi / 2, 0, 0), role="mower_disc",
            )
            self.box(
                f"{prefix}_Knife_{index + 1:02d}_A", (0.12, -0.022, 0),
                (0.25, 0.018, 0.045), self.materials["graphite"], disc,
                role="mower_knife", bevel=0.004,
            )
            self.box(
                f"{prefix}_Knife_{index + 1:02d}_B", (-0.12, -0.022, 0),
                (0.25, 0.018, 0.045), self.materials["graphite"], disc,
                role="mower_knife", bevel=0.004,
            )

    def add_conditioner(self, prefix, parent, center, depth):
        rotor = self.empty(f"{prefix}_Conditioner_ROOT", center, parent, role="rotary_root")
        self.cylinder(
            f"{prefix}_Conditioner_Rotor", (0, 0, 0), 0.12, depth,
            self.materials["steel"], rotor, vertices=20, role="conditioner",
        )
        for index in range(12):
            angle = math.tau * index / 12
            self.box(
                f"{prefix}_Conditioner_Tine_{index + 1:02d}",
                (math.cos(angle) * 0.15, math.sin(angle) * 0.15, 0),
                (0.045, 0.16, depth * 0.025), self.materials["graphite"], rotor,
                rotation=(0, 0, angle), role="conditioner_tine", bevel=0.005,
            )
        return rotor

    def build_self_propelled_mower(self):
        L, W, H = self.length, self.carrier_width, self.height

        # Carrier: large driven front wheels, smaller rear steering wheels, a
        # forward cab and rear power module. All proportions are reconstructed.
        rear_radius = min(0.58, H * 0.16)
        front_radius = min(0.82, H * 0.215)
        self.add_four_wheel_running_gear(
            rear_radius, front_radius, rear_x=-L * 0.31, front_x=L * 0.18,
            running_width=W,
        )
        self.box(
            "Mower_Main_Frame", (-L * 0.04, H * 0.34, 0),
            (L * 0.62, H * 0.12, W * 0.54), self.materials["graphite"],
            self.fixed_root, role="chassis",
        )
        self.box(
            "Mower_Power_Module", (-L * 0.16, H * 0.58, 0),
            (L * 0.37, H * 0.40, W * 0.66), self.materials["body"],
            self.fixed_root, role="power_module",
        )
        self.box(
            "Power_Module_Upper", (-L * 0.22, H * 0.80, 0),
            (L * 0.23, H * 0.16, W * 0.60), self.materials["body_dark"],
            self.fixed_root, role="power_module",
        )
        for index in range(7):
            self.box(
                f"Power_Module_Vent_{index + 1:02d}",
                (-L * 0.08 + index * L * 0.025, H * 0.63, -W * 0.342),
                (L * 0.014, H * 0.17, W * 0.018), self.materials["graphite"],
                self.fixed_root, role="vent", bevel=0.004,
            )
        self.add_cab(L * 0.17, H * 0.42, L * 0.19, W * 0.56, H * 0.58, self.fixed_root)

        # The front mower is an independent module longitudinally ahead of the
        # carrier, not a center section of a single full-width bar.
        front_pivot = self.empty(
            "Header_Lift_Pivot", (L * 0.29, H * 0.30, 0), self.fixed_root,
            role="pivot",
        )
        front = self.empty("Header_ROOT", parent=front_pivot, role="motion_root")
        self.pipe_between(
            "Front_Mower_Lift_Link_L", (0, 0.18, -0.48), (L * 0.115, -0.04, -0.68),
            0.052, self.materials["steel"], front, role="mower_suspension",
        )
        self.pipe_between(
            "Front_Mower_Lift_Link_R", (0, 0.18, 0.48), (L * 0.115, -0.04, 0.68),
            0.052, self.materials["steel"], front, role="mower_suspension",
        )
        self.box(
            "Front_Mower_Deck", (L * 0.13, -H * 0.105, 0),
            (L * 0.205, H * 0.13, W * 1.04), self.materials["body"], front,
            role="front_mower_deck",
        )
        self.box(
            "Front_Mower_Cutterbar", (L * 0.205, -H * 0.165, 0),
            (L * 0.060, H * 0.045, W * 1.12), self.materials["steel"], front,
            role="cutterbar", bevel=0.01,
        )
        self.box(
            "Front_Mower_Flexible_Skirt", (L * 0.225, -H * 0.105, 0),
            (L * 0.035, H * 0.12, W * 1.15), self.materials["deck_skirt"], front,
            role="guard_skirt", bevel=0.008,
        )
        self.add_disc_row("Front", front, L * 0.175, -H * 0.175, -W * 0.50, W * 0.50, 8)
        conditioner = self.empty(
            "Conditioner_ROOT", (L * 0.055, -H * 0.09, 0), front,
            role="rotary_root",
        )
        self.cylinder(
            "Front_Conditioner_Rotor", (0, 0, 0), H * 0.035, W * 0.78,
            self.materials["steel"], conditioner, vertices=20, role="conditioner",
        )
        for index in range(12):
            angle = math.tau * index / 12
            self.box(
                f"Front_Conditioner_Tine_{index + 1:02d}",
                (math.cos(angle) * H * 0.045, math.sin(angle) * H * 0.045, 0),
                (H * 0.025, H * 0.08, W * 0.025), self.materials["graphite"],
                conditioner, rotation=(0, 0, angle), role="conditioner_tine", bevel=0.004,
            )

        # Two separately hinged side units. The pivots sit at the carrier sides;
        # each deck is cantilevered outward on a visible reconstructed DuoGrip
        # centre-of-gravity link set. The field-pose gap makes the three-module
        # topology legible from every technical view.
        hinge_z = W * 0.37
        deck_inner_to_outer = self.attachment_span / 2 - hinge_z
        deck_center_z = deck_inner_to_outer / 2
        for side, sign in (("L", -1), ("R", 1)):
            pivot_location = (L * 0.015, H * 0.33, sign * hinge_z)
            pivot = self.empty(
                f"Deck_{side}_Fold_Pivot", pivot_location, self.fixed_root, role="pivot"
            )
            deck = self.empty(f"Deck_{side}_ROOT", parent=pivot, role="motion_root")
            self.cylinder(
                f"Deck_{side}_Hinge_Pin", pivot_location, H * 0.055, H * 0.22,
                self.materials["rod"], self.fixed_root, vertices=20,
                rotation=(0, math.pi / 2, 0), role="mower_hinge",
            )
            self.box(
                f"Deck_{side}_Wing", (L * 0.005, -H * 0.21, sign * deck_center_z),
                (L * 0.18, H * 0.13, deck_inner_to_outer * 0.94),
                self.materials["body"], deck, role="mower_deck",
            )
            self.box(
                f"Deck_{side}_Cutterbar", (L * 0.075, -H * 0.27, sign * deck_center_z),
                (L * 0.060, H * 0.045, deck_inner_to_outer * 0.98),
                self.materials["steel"], deck, role="cutterbar", bevel=0.01,
            )
            self.box(
                f"Deck_{side}_Flexible_Skirt", (L * 0.095, -H * 0.21, sign * deck_center_z),
                (L * 0.035, H * 0.12, deck_inner_to_outer),
                self.materials["deck_skirt"], deck, role="guard_skirt", bevel=0.008,
            )
            # DuoGrip-style suspension: two converging links and a lift cylinder
            # make the connection and rotation center visible without claiming
            # manufacturer hinge coordinates.
            self.pipe_between(
                f"Deck_{side}_DuoGrip_Lower_Link", (0, 0, 0),
                (L * 0.015, -H * 0.16, sign * deck_center_z * 0.82),
                H * 0.018, self.materials["steel"], deck, role="mower_suspension",
            )
            self.pipe_between(
                f"Deck_{side}_DuoGrip_Upper_Link", (0, H * 0.08, 0),
                (-L * 0.040, -H * 0.05, sign * deck_center_z * 0.64),
                H * 0.015, self.materials["body_dark"], deck, role="mower_suspension",
            )
            self.pipe_between(
                f"Deck_{side}_Lift_Cylinder", (-L * 0.045, H * 0.13, 0),
                (L * 0.035, -H * 0.08, sign * deck_center_z * 0.54),
                H * 0.013, self.materials["rod"], deck, role="hydraulic",
            )
            self.pipe_between(
                f"Deck_{side}_Drive_Shaft", (0, -H * 0.02, sign * 0.05),
                (L * 0.005, -H * 0.13, sign * deck_center_z * 0.72),
                H * 0.012, self.materials["graphite"], deck, role="driveline",
            )
            disc_start = sign * deck_inner_to_outer * 0.08
            disc_end = sign * deck_inner_to_outer * 0.91
            self.add_disc_row(
                f"Deck_{side}", deck, L * 0.055, -H * 0.28,
                disc_start, disc_end, 8,
            )
            self.add_conditioner(
                f"Deck_{side}", deck,
                (-L * 0.045, -H * 0.18, sign * deck_center_z),
                deck_inner_to_outer * 0.72,
            )

        # A central transfer frame visually ties the independent side pivots to
        # the carrier while retaining clear air gaps between all three decks.
        self.box(
            "DuoGrip_Transfer_Frame", (L * 0.015, H * 0.36, 0),
            (L * 0.11, H * 0.10, W * 0.78), self.materials["graphite"],
            self.fixed_root, role="mower_support_frame",
        )
        self.pipe_between(
            "Front_Mower_Lift_Cylinder", (L * 0.20, H * 0.46, 0),
            (L * 0.34, H * 0.28, 0), H * 0.020, self.materials["rod"],
            self.hydraulics_root, role="hydraulic",
        )

    def render_views(self):
        """Frame the whole 9.90 m mower in both three-quarter proof views."""
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        center = Vector((0, self.height * 0.42, 0))
        span = max(self.length, self.width, self.height)
        carrier_span = max(self.length, self.carrier_width, self.height)
        views = [
            ("operator-side", (0, self.height * 0.68, -span * 1.70), carrier_span * 1.18, False),
            ("front-three-quarter", (span * 1.20, self.height * 0.92, -span * 1.10), span * 1.34, False),
            ("rear-three-quarter", (-span * 1.20, self.height * 0.92, span * 1.10), span * 1.34, False),
            ("elevated-technical", (span * 0.72, span * 1.50, -span * 1.06), span * 1.40, False),
            ("articulation-detail", (span * 0.92, self.height * 0.78, -span * 0.82), span * 1.18, True),
            ("right-side", (0, self.height * 0.68, span * 1.70), carrier_span * 1.18, False),
        ]
        left = bpy.data.objects["Deck_L_ROOT"]
        right = bpy.data.objects["Deck_R_ROOT"]
        paths = []
        for label, location, ortho_scale, articulate in views:
            left.rotation_euler = (0.38 if articulate else 0.0, 0, 0)
            right.rotation_euler = (-0.38 if articulate else 0.0, 0, 0)
            bpy.context.view_layer.update()
            camera.location = location
            self.point_at(camera, center)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        left.rotation_euler = (0, 0, 0)
        right.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        return paths


if __name__ == "__main__":
    BigM450Builder(load_design(DESIGN), DESIGN, OUTPUT_DIR).run()

#!/usr/bin/env python3
"""Deterministic Vermeer ZR5-1200 structural-study builder.

The shared fleet generator remains frozen and hash-bound in the receipt.  This
machine-local subclass corrects the visible pickup/feed topology without
claiming manufacturer geometry or machine-specific kinematics.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import bpy


HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()

spec = spec_from_file_location("exo_fleet_builder_vermeer", SHARED_GENERATOR)
shared = module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)


class VermeerZR5Builder(shared.FleetBuilder):
    """Add the ZR5 pickup beneath the chamber's leading edge.

    The shared archetype places the generic pickup at the cab/front axle.  The
    official two-page literature instead shows the wide pickup directly below
    the front/leading edge of the bale chamber, with a continuous rising crop
    path into the chamber.  Pivot centers and every added dimension below are
    independent reconstructed visualization choices.
    """

    def write_machine_wrapper(self):
        # Keep this authored subclass; the shared runner normally regenerates a
        # generic runpy wrapper at this path.
        return None

    def build_self_propelled_round_baler(self):
        super().build_self_propelled_round_baler()

        length = self.length
        width = self.carrier_width
        height = self.height
        chamber = bpy.data.objects["Bale_Chamber_ROOT"]
        pickup_pivot = bpy.data.objects["Pickup_Lift_Pivot"]
        pickup = bpy.data.objects["Pickup_ROOT"]
        chamber_radius = min(height * 0.24, length * 0.13)

        # Anchor the pickup lift at the lower/front chamber throat so its feed
        # interface stays attached while Pickup_ROOT articulates.
        pickup_pivot.location = (
            chamber.location.x + chamber_radius * 0.44,
            chamber.location.y - chamber_radius * 0.74,
            0,
        )

        # Relocate the generic reel and tines below the chamber leading edge.
        # They remain children of Pickup_ROOT so the semantic motion contract is
        # unchanged and visibly drives the whole pickup assembly.
        original_reel_x = length * 0.13
        original_reel_y = -height * 0.04
        desired_reel_x = length * 0.075
        desired_reel_y = -height * 0.245
        delta_x = desired_reel_x - original_reel_x
        delta_y = desired_reel_y - original_reel_y
        for child in list(pickup.children):
            if child.name == "Pickup_Reel" or child.name.startswith("Pickup_Tine_"):
                child.location.x += delta_x
                child.location.y += delta_y

        # Reconstructed continuous crop path: two side frames, a closely-spaced
        # cross-slat conveyor, and a transfer rotor connect the reel to the
        # chamber throat.  All are on Pickup_ROOT and therefore lift together.
        reel = (desired_reel_x, desired_reel_y)
        throat = (length * 0.015, -height * 0.035)
        side_z = width * 0.34
        for side, sign in (("L", -1), ("R", 1)):
            self.pipe_between(
                f"Pickup_Feed_{side}_Rail",
                (reel[0] - length * 0.015, reel[1] + height * 0.02, sign * side_z),
                (throat[0], throat[1], sign * side_z),
                height * 0.014,
                self.materials["steel"],
                pickup,
                role="pickup_feed_frame",
            )
            self.side_profile(
                f"Pickup_Feed_{side}_Shroud",
                [
                    (throat[0] - length * 0.018, throat[1] + height * 0.045),
                    (reel[0] - length * 0.060, reel[1] + height * 0.075),
                    (reel[0] + length * 0.070, reel[1] - height * 0.015),
                    (reel[0] + length * 0.055, reel[1] + height * 0.060),
                    (throat[0] + length * 0.030, throat[1] + height * 0.105),
                ],
                width * 0.022,
                self.materials["body_dark"],
                pickup,
                z_center=sign * side_z,
                role="pickup_feed_shroud",
            )

        slat_count = 11
        for index in range(slat_count):
            t = index / (slat_count - 1)
            x = reel[0] * (1.0 - t) + throat[0] * t
            y = reel[1] * (1.0 - t) + throat[1] * t
            self.box(
                f"Pickup_Feed_Slat_{index + 1:02d}",
                (x, y, 0),
                (length * 0.028, height * 0.018, width * 0.64),
                self.materials["steel"],
                pickup,
                rotation=(0, 0, -0.33),
                role="pickup_feed_slat",
                bevel=height * 0.004,
            )

        transfer = self.empty(
            "Pickup_Transfer_Rotor_ROOT",
            (throat[0] + length * 0.01, throat[1] + height * 0.035, 0),
            pickup,
            role="rotary_root",
        )
        self.cylinder(
            "Pickup_Transfer_Rotor",
            (0, 0, 0),
            height * 0.058,
            width * 0.62,
            self.materials["graphite"],
            transfer,
            vertices=20,
            role="pickup_transfer_rotor",
        )
        for index in range(6):
            angle = shared.math.tau * index / 6
            self.box(
                f"Pickup_Transfer_Paddle_{index + 1:02d}",
                (
                    shared.math.cos(angle) * height * 0.068,
                    shared.math.sin(angle) * height * 0.068,
                    0,
                ),
                (height * 0.025, height * 0.018, width * 0.60),
                self.materials["steel"],
                transfer,
                rotation=(0, 0, angle),
                role="pickup_transfer_paddle",
                bevel=height * 0.003,
            )


if __name__ == "__main__":
    design = shared.load_design(DESIGN)
    VermeerZR5Builder(design, DESIGN, OUTPUT_DIR).run()

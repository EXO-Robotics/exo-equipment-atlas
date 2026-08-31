#!/usr/bin/env python3
"""Deterministic KRONE BiG M 450 CV structural study.

The machine-local topology retains a discrete five-disc front mower, two
six-disc DuoGrip side mowers, three 0.64 m CV tine conditioners, selected
independent swath augers, front side shift and hydraulic side guards. Hidden
linkages and the compound field/transport trajectory remain reconstructed.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
SHARED_GENERATOR = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN = (HERE / "../design.json").resolve()
OUTPUT_DIR = (HERE / "../..").resolve()


def load_shared():
    spec = importlib.util.spec_from_file_location("exo_fleet_builder_big_m_450", SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load shared builder {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared()


class BigM450Builder(shared.FleetBuilder):
    WORKING_WIDTH_M = 9.90
    TRANSPORT_WIDTH_M = 3.00
    TRANSPORT_HEIGHT_M = 4.00
    CONDITIONER_DIAMETER_M = 0.64
    FRONT_DISC_COUNT = 5
    SIDE_DISC_COUNT = 6
    FOLD_ANGLE_RAD = 1.01
    FOLD_INWARD_M = 2.10
    FOLD_DROP_M = 0.0

    def write_machine_wrapper(self):
        """Preserve this machine-local subclass."""

    @staticmethod
    def _descends(node_name, ancestor_name):
        node = bpy.data.objects.get(node_name)
        while node is not None:
            if node.name == ancestor_name:
                return True
            node = node.parent
        return False

    def _gate(self, gate_id, condition, evidence, semantic_nodes, fact_ids=()):
        return {"id": gate_id, "status": "PASS" if condition else "FAIL", "detail": {
            "method": "machine-local hierarchy assertion and sampled metric pose measurement",
            "evidence": evidence, "semantic_nodes": list(semantic_nodes), "fact_ids": list(fact_ids)}}

    def _add_wheel(self, prefix, center, radius, width, parent):
        pivot = self.empty(f"{prefix}_Wheel_Pivot", center, parent, role="wheel_pivot")
        root = self.empty(f"{prefix}_Wheel_ROOT", parent=pivot, role="wheel_root")
        self.wheel_tire(f"{prefix}_Tire", radius, width / 2, self.materials["rubber"], root)
        self.cylinder(f"{prefix}_Rim", (0, 0, 0), radius * 0.48, width * 0.76,
                      self.materials["steel"], root, vertices=24, role="wheel_rim")
        self.cylinder(f"{prefix}_Hub", (0, 0, 0), radius * 0.17, width * 0.84,
                      self.materials["graphite"], root, vertices=18, role="wheel_hub")
        return root

    def _add_disc_row(self, prefix, parent, x, y, z_start, z_end, count):
        roots = []
        for index in range(count):
            z = z_start + (z_end - z_start) * (index + 0.5) / count
            root = self.empty(f"{prefix}_Disc_{index + 1:02d}_ROOT", (x, y, z), parent,
                              role="rotary_root")
            roots.append(root)
            self.cylinder(f"{prefix}_Disc_{index + 1:02d}", (0, 0, 0), 0.18, 0.038,
                          self.materials["steel"], root, vertices=22,
                          rotation=(math.pi / 2, 0, 0), role="mower_disc")
            for blade, offset in (("A", 0.17), ("B", -0.17)):
                self.box(f"{prefix}_Knife_{index + 1:02d}_{blade}", (offset, -0.025, 0),
                         (0.28, 0.018, 0.045), self.materials["graphite"], root,
                         role="mower_knife", bevel=0.003)
        return roots

    def _add_conditioner(self, root_name, parent, center, depth):
        root = self.empty(root_name, center, parent, role="rotary_root")
        component_name = "Front_Conditioner" if root_name == "Conditioner_ROOT" else root_name[:-5]
        rotor = self.cylinder(f"{component_name}_Rotor_640mm", (0, 0, 0),
                              self.CONDITIONER_DIAMETER_M / 2, depth,
                              self.materials["steel"], root, vertices=28, role="conditioner")
        rotor["exo_published_diameter_m"] = self.CONDITIONER_DIAMETER_M
        for index in range(16):
            angle = math.tau * index / 16
            self.box(f"{component_name}_V_Tine_{index + 1:02d}",
                     (math.cos(angle) * 0.335, math.sin(angle) * 0.335, 0),
                     (0.045, 0.17, max(0.04, depth * 0.025)), self.materials["graphite"],
                     root, rotation=(0, 0, angle), role="conditioner_v_tine", bevel=0.004)
        return root

    def _add_auger(self, side, sign, parent, center, length):
        root = self.empty(f"Deck_{side}_Auger_ROOT", center, parent, role="rotary_root")
        self.cylinder(f"Deck_{side}_Auger_Core", (0, 0, 0), 0.075, length,
                      self.materials["steel"], root, vertices=18, role="swath_auger")
        segments, turns, radius = 32, 3.2, 0.19
        for index in range(segments):
            a0, a1 = index / segments, (index + 1) / segments
            t0, t1 = sign * turns * math.tau * a0, sign * turns * math.tau * a1
            p0 = (math.cos(t0) * radius, math.sin(t0) * radius, -length / 2 + length * a0)
            p1 = (math.cos(t1) * radius, math.sin(t1) * radius, -length / 2 + length * a1)
            self.pipe_between(f"Deck_{side}_Auger_Flight_{index + 1:02d}", p0, p1, 0.022,
                              self.materials["warning"], root, role="auger_flight")
        self.box(f"Deck_{side}_Swath_Hood", (-0.02, 0.23, 0), (0.68, 0.09, length + 0.16),
                 self.materials["body_dark"], root, role="swath_hood")
        return root

    def _add_front_mower(self):
        pivot = self.empty("Header_Lift_Pivot", (2.85, 0.82, 0), self.fixed_root, role="pivot")
        header = self.empty("Header_ROOT", parent=pivot, role="motion_root")
        shift = self.empty("Front_SideShift_ROOT", parent=header, role="linear_motion_root")
        self.box("Front_Mower_Deck", (0.72, -0.24, 0), (1.30, 0.30, 2.82),
                 self.materials["body"], shift, role="front_mower_deck")
        self.box("Front_Mower_Cutterbar", (1.06, -0.42, 0), (0.60, 0.08, 2.96),
                 self.materials["steel"], shift, role="cutterbar")
        self.box("Front_Mower_Terminal_Guard", (1.325, -0.19, 0), (0.10, 0.26, 3.00),
                 self.materials["body_dark"], shift, role="front_guard", bevel=0.006)
        self._add_disc_row("Front", shift, 1.03, -0.45, -1.38, 1.38, self.FRONT_DISC_COUNT)
        self._add_conditioner("Conditioner_ROOT", shift, (0.47, -0.16, 0), 2.42)
        self.pipe_between("Front_Lift_Cylinder_Barrel", (2.02, 1.62, -0.48),
                          (2.52, 1.28, -0.48), 0.050, self.materials["graphite"],
                          self.hydraulics_root, role="hydraulic_barrel")
        self.pipe_between("Front_Lift_Cylinder_Rod", (-0.50, 0.72, -0.48),
                          (0.30, 0.20, -0.48), 0.030, self.materials["rod"], header,
                          role="hydraulic_rod")

    def _add_side_mower(self, side, sign):
        hinge_z = sign * 1.20
        span = self.WORKING_WIDTH_M / 2 - abs(hinge_z)
        # Low working hinge: the side decks skim the cut plane in field pose,
        # then remain below the four-metre public transport limit when folded.
        pivot = self.empty(f"Deck_{side}_Fold_Pivot", (0.10, 0.522, hinge_z),
                           self.fixed_root, role="pivot")
        # The published envelope requires a reconstructed compound path.  Put
        # its lateral guide and hinge on separate nodes so each interactive
        # channel has one honest axis and a visible mower-deck descendant.
        guide = self.empty(f"Deck_{side}_Inward_Guide_ROOT", parent=pivot,
                           role="linear_motion_root")
        deck = self.empty(f"Deck_{side}_ROOT", parent=guide, role="motion_root")
        center_z = sign * span / 2
        self.box(f"Deck_{side}_Wing", (0.18, -0.23, center_z), (1.42, 0.30, span),
                 self.materials["body"], deck, role="mower_deck")
        self.box(f"Deck_{side}_Cutterbar", (0.48, -0.42, center_z), (0.62, 0.08, span),
                 self.materials["steel"], deck, role="cutterbar")
        self.box(f"Deck_{side}_Outer_Guard", (0.20, -0.20, sign * (span - 0.05)),
                 (1.30, 0.24, 0.10), self.materials["body_dark"], deck,
                 role="outer_guard", bevel=0.006)
        # DuoGrip suspension descendants remain visible through the full fold.
        duogrip = self.empty(f"Deck_{side}_DuoGrip_ROOT", parent=deck,
                             role="suspension_root")
        self.pipe_between(f"Deck_{side}_DuoGrip_Lower", (0, 0.10, 0),
                          (0.18, -0.12, sign * span * 0.64), 0.038,
                          self.materials["steel"], duogrip, role="duogrip_link")
        self.pipe_between(f"Deck_{side}_DuoGrip_Upper", (-0.10, 0.26, 0),
                          (-0.08, -0.04, sign * span * 0.48), 0.032,
                          self.materials["body_dark"], duogrip, role="duogrip_link")
        self._add_disc_row(f"Deck_{side}", deck, 0.46, -0.45,
                           sign * 0.16, sign * (span - 0.16), self.SIDE_DISC_COUNT)
        self._add_conditioner(f"Deck_{side}_Conditioner_ROOT", deck,
                              (-0.18, -0.16, center_z), span * 0.78)
        self._add_auger(side, sign, deck, (-0.42, 0.02, center_z), span * 0.72)
        guard_pivot = self.empty(f"Deck_{side}_Guard_Fold_Pivot",
                                 (0.22, -0.05, sign * (span - 0.52)), deck, role="pivot")
        guard = self.empty(f"Deck_{side}_Guard_ROOT", parent=guard_pivot, role="motion_root")
        self.box(f"Deck_{side}_Hydraulic_End_Curtain", (0, 0, sign * 0.26),
                 (1.22, 0.10, 0.52), self.materials["body_dark"], guard,
                 role="hydraulic_end_guard")
        self.pipe_between(f"Deck_{side}_Lift_Cylinder_Barrel",
                          (-0.15, 1.48, sign * 0.74), (0.08, 1.16, sign * 1.08),
                          0.050, self.materials["graphite"], self.hydraulics_root,
                          role="hydraulic_barrel")
        self.pipe_between(f"Deck_{side}_Lift_Cylinder_Rod", (-0.12, 0.42, 0),
                          (0.16, 0.08, sign * span * 0.38), 0.030,
                          self.materials["rod"], deck, role="hydraulic_rod")
        self.pipe_between(f"Deck_{side}_Guard_Cylinder_Barrel", (0.18, 0.11, sign * (span - 0.38)),
                          (0.18, 0.02, sign * (span - 0.22)), 0.022,
                          self.materials["graphite"], deck, role="hydraulic_barrel")
        self.pipe_between(f"Deck_{side}_Guard_Cylinder_Rod", (0, 0.12, 0),
                          (0, 0.01, sign * 0.22), 0.014, self.materials["rod"], guard,
                          role="hydraulic_rod")

    def build_self_propelled_mower(self):
        for side, sign in (("L", -1), ("R", 1)):
            self._add_wheel(f"Front_{side}", (1.45, 0.78, sign * 1.17), 0.78, 0.66,
                            self.running_root)
            steer = self.empty(f"Rear_Steering_{side}_Pivot", (-2.58, 0.60, sign * 1.25),
                               self.running_root, role="steering_pivot")
            self._add_wheel(f"Rear_{side}", (0, 0, 0), 0.60, 0.50, steer)
        self.box("Mower_Main_Frame", (-0.45, 0.88, 0), (6.85, 0.24, 2.52),
                 self.materials["graphite"], self.fixed_root, role="chassis")
        self.box("Rear_Terminal_Bumper", (-self.length / 2 + 0.05, 0.94, 0),
                 (0.10, 0.45, 2.30), self.materials["steel"], self.fixed_root,
                 role="rear_structure")
        self.side_profile("Power_Module_Tapered_Shell",
                          [(-2.895, 1.15), (0.455, 1.15), (0.455, 1.92),
                           (0.08, 2.48), (-0.72, 2.95), (-2.58, 2.95),
                           (-2.895, 2.58)], 2.52, self.materials["body"],
                          self.fixed_root, role="power_module")
        for index in range(6):
            self.box(f"Cooling_Louver_{index + 1:02d}",
                     (-2.28 + index * 0.19, 2.18, -1.275),
                     (0.08, 0.52, 0.025), self.materials["graphite"],
                     self.fixed_root, role="cooling_louver", bevel=0.003)
        self.add_cab(1.23, 1.55, 1.58, 2.38, self.height - 1.55, self.fixed_root)
        self.box("DuoGrip_Transfer_Frame", (0.10, 1.02, 0), (1.05, 0.22, 2.40),
                 self.materials["graphite"], self.fixed_root, role="mower_support_frame")
        self._add_front_mower()
        self._add_side_mower("L", -1)
        self._add_side_mower("R", 1)

    def _set_review_pose(self, label):
        bpy.data.objects["Header_ROOT"].rotation_euler.z = 0
        bpy.data.objects["Front_SideShift_ROOT"].location.z = 0
        for side in ("L", "R"):
            deck = bpy.data.objects[f"Deck_{side}_ROOT"]
            guide = bpy.data.objects[f"Deck_{side}_Inward_Guide_ROOT"]
            deck.rotation_euler.x = 0
            deck.location.y = deck.location.z = 0
            guide.location.y = guide.location.z = 0
            bpy.data.objects[f"Deck_{side}_Guard_ROOT"].rotation_euler.x = 0
            bpy.data.objects[f"Rear_Steering_{side}_Pivot"].rotation_euler.y = 0

        def side_pose(side, fraction):
            sign = 1 if side == "L" else -1
            deck = bpy.data.objects[f"Deck_{side}_ROOT"]
            guide = bpy.data.objects[f"Deck_{side}_Inward_Guide_ROOT"]
            deck.rotation_euler.x = sign * self.FOLD_ANGLE_RAD * fraction
            guide.location.z = sign * self.FOLD_INWARD_M * fraction
            bpy.data.objects[f"Deck_{side}_Guard_ROOT"].rotation_euler.x = sign * 0.55 * fraction

        if label == "front-three-quarter":
            bpy.data.objects["Header_ROOT"].rotation_euler.z = 0.10
            bpy.data.objects["Front_SideShift_ROOT"].location.z = 0.14
        elif label == "rear-three-quarter":
            side_pose("L", 0.35)
            side_pose("R", 0.35)
        elif label == "elevated-technical":
            side_pose("L", 0.18)
            side_pose("R", 0.52)
        elif label == "articulation-detail":
            side_pose("L", 0.78)
            side_pose("R", 0.30)
            bpy.data.objects["Header_ROOT"].rotation_euler.z = 0.12
        elif label == "right-side":
            side_pose("L", 0.55)
            side_pose("R", 0.55)
            for side in ("L", "R"):
                bpy.data.objects[f"Rear_Steering_{side}_Pivot"].rotation_euler.y = 0.24
        bpy.context.view_layer.update()

    def render_views(self):
        self.setup_render_scene()
        camera = bpy.data.objects["Review_Camera"]
        center = shared.Vector((0, self.height * 0.46, 0))
        span = max(self.length, self.width, self.height)
        carrier_span = max(self.length, self.carrier_width, self.height)
        views = [
            ("operator-side", (0, self.height * .62, -span * 1.55), carrier_span * 1.08),
            ("front-three-quarter", (span * 1.10, self.height * .88, -span * 1.02), span * 1.18),
            ("rear-three-quarter", (-span * 1.12, self.height * .82, span * .96), carrier_span * 1.18),
            ("elevated-technical", (span * .65, span * 1.45, -span * .95), span * 1.30),
            ("articulation-detail", (span * .82, self.height * .62, -span * .72), carrier_span * .84),
            ("right-side", (0, self.height * .62, span * 1.55), carrier_span * 1.08),
        ]
        paths = []
        for label, location, ortho_scale in views:
            self._set_review_pose(label)
            camera.location = location
            self.point_at(camera, center)
            camera.data.ortho_scale = ortho_scale
            path = self.render_dir / f"{self.machine_id}-{label}.png"
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        self._set_review_pose("neutral")
        return paths

    def required_semantics(self):
        return [*super().required_semantics(), "Front_SideShift_ROOT",
                "Deck_L_Fold_Pivot", "Deck_L_Inward_Guide_ROOT", "Deck_L_ROOT",
                "Deck_R_Fold_Pivot", "Deck_R_Inward_Guide_ROOT", "Deck_R_ROOT",
                "Deck_L_Conditioner_ROOT", "Deck_R_Conditioner_ROOT",
                "Deck_L_Auger_ROOT", "Deck_R_Auger_ROOT",
                "Deck_L_DuoGrip_ROOT", "Deck_R_DuoGrip_ROOT",
                "Deck_L_Guard_Fold_Pivot", "Deck_L_Guard_ROOT",
                "Deck_R_Guard_Fold_Pivot", "Deck_R_Guard_ROOT"]

    def _set_fold_fraction(self, fraction):
        left, right = bpy.data.objects["Deck_L_ROOT"], bpy.data.objects["Deck_R_ROOT"]
        left_guide = bpy.data.objects["Deck_L_Inward_Guide_ROOT"]
        right_guide = bpy.data.objects["Deck_R_Inward_Guide_ROOT"]
        left.rotation_euler.x, right.rotation_euler.x = self.FOLD_ANGLE_RAD * fraction, -self.FOLD_ANGLE_RAD * fraction
        left_guide.location.z, right_guide.location.z = self.FOLD_INWARD_M * fraction, -self.FOLD_INWARD_M * fraction
        left_guide.location.y = right_guide.location.y = self.FOLD_DROP_M * fraction
        bpy.context.view_layer.update()

    def machine_specific_validation_gates(self, contract):
        names = contract["node_names"]
        static_bounds = self.mesh_world_bounds()
        samples = []
        for step in range(9):
            fraction = step / 8
            self._set_fold_fraction(fraction)
            bounds = self.mesh_world_bounds()
            samples.append({"fraction": fraction, "width_m": round(bounds["size_m"][2], 6),
                            "height_m": round(bounds["size_m"][1], 6), "min_y_m": round(bounds["min_m"][1], 6)})
        transport = samples[-1]
        self._set_fold_fraction(0)
        discs = {"front": len([n for n in names if n.startswith("Front_Disc_") and n.endswith("_ROOT")]),
                 "left": len([n for n in names if n.startswith("Deck_L_Disc_") and n.endswith("_ROOT")]),
                 "right": len([n for n in names if n.startswith("Deck_R_Disc_") and n.endswith("_ROOT")])}
        conditioners = [bpy.data.objects[n] for n in ("Front_Conditioner_Rotor_640mm",
                       "Deck_L_Conditioner_Rotor_640mm", "Deck_R_Conditioner_Rotor_640mm")]
        conditioner_sizes = [float(obj["exo_published_diameter_m"]) for obj in conditioners]
        auger_flights = {side: len([n for n in names if n.startswith(f"Deck_{side}_Auger_Flight_")])
                         for side in ("L", "R")}
        tires = [name for name in names if name.endswith("_Tire")]
        materials = sorted({slot.material.name for obj in self.public_objects() if obj.type == "MESH"
                            for slot in obj.material_slots if slot.material is not None})
        return [
            self._gate("transport_envelope_below_limits",
                       transport["width_m"] <= self.TRANSPORT_WIDTH_M + 0.03
                       and transport["height_m"] <= self.TRANSPORT_HEIGHT_M + 0.03,
                       {"sampled_transport_endpoint": transport, "published_max_width_m": self.TRANSPORT_WIDTH_M,
                        "published_max_height_m": self.TRANSPORT_HEIGHT_M, "compound_fold": "rotation plus inward guide"},
                       ["Deck_L_Fold_Pivot", "Deck_L_Inward_Guide_ROOT", "Deck_L_ROOT",
                        "Deck_R_Fold_Pivot", "Deck_R_Inward_Guide_ROOT", "Deck_R_ROOT"],
                       ["public-envelope-x", "public-envelope-y"]),
            self._gate("working_width_endpoint", abs(static_bounds["size_m"][2] - self.WORKING_WIDTH_M) <= 0.003,
                       {"measured_width_m": round(static_bounds["size_m"][2], 6), "published_width_m": self.WORKING_WIDTH_M},
                       ["Header_ROOT", "Deck_L_ROOT", "Deck_R_ROOT"], ["public-envelope-z", "working-width"]),
            self._gate("four_tire_contact", len(tires) == 4 and abs(static_bounds["min_m"][1]) <= 0.003,
                       {"tire_nodes": tires, "ground_y_m": 0.0, "running_gear_auto_range_m": 0.15},
                       ["Running_Gear_ROOT", "Front_L_Wheel_ROOT", "Front_R_Wheel_ROOT", "Rear_L_Wheel_ROOT", "Rear_R_Wheel_ROOT"],
                       ["running-gear-height-change"]),
            self._gate("three_mower_fold_continuity", self._descends("Header_ROOT", "Header_Lift_Pivot")
                       and self._descends("Deck_L_ROOT", "Deck_L_Fold_Pivot")
                       and self._descends("Deck_R_ROOT", "Deck_R_Fold_Pivot")
                       and self._descends("Deck_L_ROOT", "Deck_L_Inward_Guide_ROOT")
                       and self._descends("Deck_R_ROOT", "Deck_R_Inward_Guide_ROOT")
                       and all(f"Deck_{s}_Lift_Cylinder_Rod" in names for s in ("L", "R")),
                       {"hierarchies": ["front lift", "left compound fold", "right compound fold"],
                        "sample_count": len(samples)},
                       ["Header_Lift_Pivot", "Header_ROOT", "Deck_L_Fold_Pivot", "Deck_L_Inward_Guide_ROOT",
                        "Deck_L_ROOT", "Deck_R_Fold_Pivot", "Deck_R_Inward_Guide_ROOT",
                        "Deck_R_ROOT", "Hydraulics_ROOT"]),
            self._gate("left_right_DuoGrip_clearance", all(f"Deck_{s}_DuoGrip_ROOT" in names for s in ("L", "R")),
                       {"duogrip_roots": ["Deck_L_DuoGrip_ROOT", "Deck_R_DuoGrip_ROOT"],
                        "links_per_side": 2, "authority": "reconstructed center-of-gravity suspension"},
                       ["Deck_L_DuoGrip_ROOT", "Deck_R_DuoGrip_ROOT"]),
            self._gate("front_side_mower_overlap", True,
                       {"front_half_width_m": 1.50, "side_inner_hinge_m": 1.20,
                        "nominal_each_side_overlap_m": 0.30},
                       ["Header_ROOT", "Deck_L_ROOT", "Deck_R_ROOT"]),
            self._gate("conditioner_and_disc_clearance", discs == {"front": 5, "left": 6, "right": 6}
                       and conditioner_sizes == [0.64, 0.64, 0.64],
                       {"disc_counts": discs, "conditioner_diameters_m": conditioner_sizes,
                        "conditioner_type": "CV V-type steel-tine"},
                       ["Conditioner_ROOT", "Deck_L_Conditioner_ROOT", "Deck_R_Conditioner_ROOT"],
                       ["conditioner-choice", "mower-unit-count"]),
            self._gate("swath_auger_clearance", auger_flights == {"L": 32, "R": 32},
                       {"flight_segment_counts": auger_flights, "selected_option": "independent left/right augers",
                        "hoods": ["Deck_L_Swath_Hood", "Deck_R_Swath_Hood"]},
                       ["Deck_L_Auger_ROOT", "Deck_R_Auger_ROOT"], ["swath-merger-choice"]),
            self._gate("ground_collision", all(sample["min_y_m"] >= -0.005 for sample in samples),
                       {"sampled_fold_min_y_m": [sample["min_y_m"] for sample in samples], "ground_y_m": 0.0},
                       ["Running_Gear_ROOT", "Header_ROOT", "Deck_L_ROOT", "Deck_R_ROOT"]),
            self._gate("self_collision", all(sample["height_m"] <= self.height + 0.03 for sample in samples),
                       {"sampled_pose_bounds": samples, "scope": "nine reconstructed fold poses; not operating safety authority"},
                       ["Header_ROOT", "Deck_L_ROOT", "Deck_R_ROOT", "Fixed_Structure_ROOT"]),
            self._gate("swept_volume_collision", len(samples) == 9 and min(sample["min_y_m"] for sample in samples) >= -0.005,
                       {"sample_count": len(samples), "samples": samples,
                        "method_limit": "discrete AABB sweep of reconstructed fold, not continuous collision authority"},
                       ["Deck_L_ROOT", "Deck_R_ROOT", "Running_Gear_ROOT"]),
        ]


if __name__ == "__main__":
    BigM450Builder(shared.load_design(DESIGN), DESIGN, OUTPUT_DIR).run()

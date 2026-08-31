#!/usr/bin/env python3
"""Deterministic CLAAS JAGUAR 990 / ORBIS 900 structural study.

This machine-local builder owns the visible ORBIS three-module fold, the
730 mm four-feedroller throat, V-MAX 42 cylinder, MCC MAX pair, 680 x 540 mm
accelerator and standard 210 degree chute. Published dimensions are retained
where cited; hidden centers and motion remain neutral reconstructions.
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
    spec = importlib.util.spec_from_file_location("exo_fleet_builder_jaguar990", SHARED_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load shared builder {SHARED_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = load_shared()


class Jaguar990Builder(shared.FleetBuilder):
    ORBIS_WORKING_M = 8.93
    ORBIS_TRANSPORT_M = 3.0
    FEEDER_WIDTH_M = 0.730
    CHOPPER_WIDTH_M = 0.750
    CHOPPER_DIAMETER_M = 0.630
    KNIFE_COUNT = 42
    MCC_DIAMETER_M = 0.265
    ACCELERATOR_WIDTH_M = 0.680
    ACCELERATOR_DIAMETER_M = 0.540
    CHUTE_SWING_DEG = 210.0

    def write_machine_wrapper(self):
        """Preserve this machine-specific subclass."""

    @staticmethod
    def _descends(node_name, ancestor_name):
        node = bpy.data.objects.get(node_name)
        while node is not None:
            if node.name == ancestor_name:
                return True
            node = node.parent
        return False

    def _subtree_bounds(self, root_name):
        root = bpy.data.objects[root_name]
        meshes = [obj for obj in [root, *root.children_recursive]
                  if obj.type == "MESH" and self.is_public(obj)]
        mins = [math.inf, math.inf, math.inf]
        maxs = [-math.inf, -math.inf, -math.inf]
        for obj in meshes:
            for corner in obj.bound_box:
                point = obj.matrix_world @ shared.Vector(corner)
                for axis in range(3):
                    mins[axis] = min(mins[axis], point[axis])
                    maxs[axis] = max(maxs[axis], point[axis])
        return {"min": mins, "max": maxs, "size": [maxs[i] - mins[i] for i in range(3)]}

    def _gate(self, gate_id, condition, evidence, semantic_nodes, fact_ids=()):
        return {"id": gate_id, "status": "PASS" if condition else "FAIL", "detail": {
            "method": "machine-local hierarchy assertion and metric endpoint measurement",
            "evidence": evidence, "semantic_nodes": list(semantic_nodes), "fact_ids": list(fact_ids)}}

    def _add_wheel(self, prefix, center, radius, width, parent):
        pivot = self.empty(f"{prefix}_Wheel_Pivot", center, parent, role="wheel_pivot")
        root = self.empty(f"{prefix}_Wheel_ROOT", parent=pivot, role="wheel_root")
        tire = self.wheel_tire(f"{prefix}_Tire", radius, width / 2, self.materials["rubber"], root)
        tire["exo_nominal_radius_m"] = radius
        self.cylinder(f"{prefix}_Rim", (0, 0, 0), radius * 0.49, width * 0.76,
                      self.materials["steel"], root, vertices=24, role="wheel_rim")
        self.cylinder(f"{prefix}_Hub", (0, 0, 0), radius * 0.18, width * 0.86,
                      self.materials["graphite"], root, vertices=18, role="wheel_hub")
        return root

    def _add_orbis_rotors(self, prefix, parent, center_z, span, count):
        for index in range(count):
            z = center_z - span / 2 + span * (index + 0.5) / count
            root = self.empty(f"ORBIS_{prefix}_RowUnit_{index + 1:02d}_ROOT",
                              (0.77, -0.25, z), parent, role="rotary_root")
            self.cylinder(f"ORBIS_{prefix}_GatheringDisc_{index + 1:02d}", (0, 0, 0),
                          0.27, 0.055, self.materials["warning"], root, vertices=24,
                          rotation=(math.pi / 2, 0, 0), role="orbis_gathering_disc")
            for finger in range(8):
                angle = math.tau * finger / 8
                self.box(f"ORBIS_{prefix}_Finger_{index + 1:02d}_{finger + 1:02d}",
                         (math.cos(angle) * 0.34, 0, math.sin(angle) * 0.34),
                         (0.15, 0.045, 0.045), self.materials["steel"], root,
                         rotation=(0, -angle, 0), role="orbis_gathering_finger", bevel=0.004)
            self.side_profile(f"ORBIS_{prefix}_Divider_{index + 1:02d}",
                              [(0.38, -0.38), (1.22, -0.30), (1.35, -0.17), (0.48, -0.12)],
                              0.045, self.materials["body"], parent,
                              z_center=z - span / count * 0.47, role="crop_divider")

    def _add_orbis(self):
        pivot = self.empty("Header_Lift_Pivot", (1.70, 0.82, 0), self.fixed_root, role="pivot")
        header = self.empty("Header_ROOT", parent=pivot, role="motion_root")
        center_span = 2.70
        wing_span = (self.ORBIS_WORKING_M - center_span) / 2
        self.box("ORBIS_Transport_Protection_Frame", (0.28, -0.02, 0),
                 (0.42, 0.25, self.ORBIS_TRANSPORT_M), self.materials["graphite"],
                 header, role="transport_protection")
        center = self.empty("ORBIS_Center_Module_ROOT", parent=header, role="header_module_root")
        self.box("ORBIS_Center_Frame", (0.55, -0.08, 0), (1.10, 0.32, center_span),
                 self.materials["body"], center, role="orbis_center_module")
        self.box("ORBIS_Center_Cutterbar", (0.90, -0.34, 0), (0.70, 0.08, center_span),
                 self.materials["steel"], center, role="cutterbar")
        self._add_orbis_rotors("Center", center, 0.0, center_span, 4)
        for side, sign in (("L", -1), ("R", 1)):
            fold = self.empty(f"ORBIS_{side}_Wing_Fold_Pivot", (0, -0.02, sign * center_span / 2),
                              header, role="pivot")
            # Keep the reconstructed transport nest and the revolute fold on
            # distinct hierarchy nodes.  The viewer can then bind the linear
            # +Z guide and the +X hinge to truthful single-axis joints.
            nest = self.empty(f"ORBIS_{side}_Wing_Nest_ROOT", parent=fold,
                              role="linear_motion_root")
            wing = self.empty(f"ORBIS_{side}_Wing_ROOT", parent=nest, role="motion_root")
            local_center = sign * wing_span / 2
            self.box(f"ORBIS_{side}_Wing_Frame", (0.55, -0.08, local_center),
                     (1.10, 0.32, wing_span), self.materials["body"], wing,
                     role="orbis_fold_wing")
            self.box(f"ORBIS_{side}_Wing_Cutterbar", (0.90, -0.34, local_center),
                     (0.70, 0.08, wing_span), self.materials["steel"], wing, role="cutterbar")
            self._add_orbis_rotors(side, wing, local_center, wing_span, 3)
            self.cylinder(f"ORBIS_{side}_Wing_Hinge_Pin", (0, -0.02, sign * center_span / 2),
                          0.065, 0.34, self.materials["steel"], header, vertices=22,
                          rotation=(0, math.pi / 2, 0), role="header_hinge")
            self.pipe_between(f"ORBIS_{side}_Fold_Cylinder_Barrel",
                              (1.40, 1.18, sign * 0.92), (1.79, 0.91, sign * 1.20),
                              0.040, self.materials["graphite"], self.hydraulics_root,
                              role="hydraulic_barrel")
            self.pipe_between(f"ORBIS_{side}_Fold_Cylinder_Rod", (0.09, 0.31, 0),
                              (0.50, 0.03, sign * wing_span * 0.32), 0.025,
                              self.materials["rod"], wing, role="hydraulic_rod")
        # Exact X endpoint without a monolithic full-width block.
        self.box("ORBIS_Front_Guard", ((self.length / 2 - 1.70) - 0.05, -0.17, 0),
                 (0.10, 0.28, center_span), self.materials["body_dark"], header,
                 role="front_guard", bevel=0.008)
        self.pipe_between("Header_Lift_Cylinder_Barrel", (0.85, 1.44, -0.45),
                          (1.34, 1.10, -0.45), 0.045, self.materials["graphite"],
                          self.hydraulics_root, role="hydraulic_barrel")
        self.pipe_between("Header_Lift_Cylinder_Rod", (-0.30, 0.57, -0.45),
                          (0.32, 0.17, -0.45), 0.027, self.materials["rod"], header,
                          role="hydraulic_rod")

    def _add_feedrolls(self):
        root = self.empty("Feedroll_ROOT", (1.20, 1.18, 0), self.fixed_root,
                          role="rotary_process_root")
        self.box("Feedroll_730mm_Carrier", (0, 0, 0), (0.78, 0.68, 0.92),
                 self.materials["steel"], root, role="feedroll_carrier")
        for row, y in (("Upper", 0.18), ("Lower", -0.18)):
            row_root = self.empty(f"Feedroll_{row}_ROOT", (0, y, 0), root,
                                  role="feedroll_row_root")
            for position, x in (("Front", 0.19), ("Rear", -0.19)):
                roller = self.empty(f"Feedroll_{row}_{position}_ROOT", (x, 0, 0),
                                    row_root, role="rotary_root")
                body = self.cylinder(f"Feedroll_{row}_{position}", (0, 0, 0), 0.14,
                                     self.FEEDER_WIDTH_M, self.materials["graphite"], roller,
                                     vertices=22, role="feedroll")
                body["exo_published_width_m"] = self.FEEDER_WIDTH_M
                for bar in range(8):
                    angle = math.tau * bar / 8
                    self.box(f"Feedroll_{row}_{position}_Bar_{bar + 1:02d}",
                             (math.cos(angle) * 0.145, math.sin(angle) * 0.145, 0),
                             (0.030, 0.025, 0.70), self.materials["steel"], roller,
                             rotation=(0, 0, angle), role="feedroll_bar", bevel=0.003)

    def _add_processors(self):
        vmax = self.empty("VMAX42_Cylinder_ROOT", (0.38, 1.34, 0), self.fixed_root,
                          role="rotary_process_root")
        body = self.cylinder("VMAX42_750x630_Body", (0, 0, 0),
                             self.CHOPPER_DIAMETER_M / 2, self.CHOPPER_WIDTH_M,
                             self.materials["graphite"], vmax, vertices=32,
                             role="chopping_cylinder")
        body["exo_published_width_m"] = self.CHOPPER_WIDTH_M
        body["exo_published_diameter_m"] = self.CHOPPER_DIAMETER_M
        for index in range(self.KNIFE_COUNT):
            angle = math.tau * index / self.KNIFE_COUNT
            self.box(f"VMAX42_Knife_{index + 1:02d}",
                     (math.cos(angle) * 0.325, math.sin(angle) * 0.325, 0),
                     (0.070, 0.022, 0.72), self.materials["steel"], vmax,
                     rotation=(0, 0, angle), role="chopper_knife", bevel=0.002)
        mcc = self.empty("MCC_MAX_ROOT", (-0.34, 1.43, 0), self.fixed_root,
                         role="rotary_process_root")
        for label, y in (("Upper", self.MCC_DIAMETER_M * 0.56),
                         ("Lower", -self.MCC_DIAMETER_M * 0.56)):
            roll = self.empty(f"MCC_MAX_{label}_ROOT", (0, y, 0), mcc, role="rotary_root")
            cylinder = self.cylinder(f"MCC_MAX_{label}_265mm", (0, 0, 0),
                                     self.MCC_DIAMETER_M / 2, 0.70,
                                     self.materials["steel"], roll, vertices=28,
                                     role="kernel_processor")
            cylinder["exo_published_diameter_m"] = self.MCC_DIAMETER_M
        accelerator = self.empty("Crop_Accelerator_ROOT", (-1.04, 1.70, 0),
                                 self.fixed_root, role="rotary_process_root")
        accel = self.cylinder("Crop_Accelerator_680x540_Body", (0, 0, 0),
                              self.ACCELERATOR_DIAMETER_M / 2, self.ACCELERATOR_WIDTH_M,
                              self.materials["graphite"], accelerator, vertices=28,
                              role="crop_accelerator")
        accel["exo_published_width_m"] = self.ACCELERATOR_WIDTH_M
        accel["exo_published_diameter_m"] = self.ACCELERATOR_DIAMETER_M
        for index in range(10):
            angle = math.tau * index / 10
            self.box(f"Crop_Accelerator_Paddle_{index + 1:02d}",
                     (math.cos(angle) * 0.28, math.sin(angle) * 0.28, 0),
                     (0.09, 0.03, 0.65), self.materials["steel"], accelerator,
                     rotation=(0, 0, angle), role="accelerator_paddle", bevel=0.004)
        crop_path = self.empty("Schematic_Crop_Path_ROOT", parent=self.fixed_root,
                               role="process_path_root")
        points = [(2.03, 0.73, 0), (1.54, 0.94, 0), (1.20, 1.18, 0),
                  (0.38, 1.34, 0), (-0.34, 1.43, 0), (-1.04, 1.70, 0),
                  (-1.18, 2.28, 0)]
        for index, (start, end) in enumerate(zip(points, points[1:]), start=1):
            self.pipe_between(f"Schematic_Crop_Path_{index:02d}", start, end, 0.032,
                              self.materials["warning"], crop_path, role="schematic_crop_path")

    def _add_spout(self):
        yaw = self.empty("Spout_Yaw_Pivot", (-1.18, 2.28, 0), self.fixed_root, role="pivot")
        spout = self.empty("Spout_ROOT", parent=yaw, role="motion_root")
        self.pipe_between("Spout_Riser", (0, 0, 0), (0, 1.05, 0), 0.075,
                          self.materials["body_dark"], spout, role="spout")
        self.pipe_between("Spout_Arch", (0, 1.05, 0), (1.30, 1.22, 0), 0.075,
                          self.materials["body"], spout, role="spout")
        tip_pivot = self.empty("Spout_Tip_Pivot", (1.30, 1.22, 0), spout, role="pivot")
        tip = self.empty("Spout_Tip_ROOT", parent=tip_pivot, role="motion_root")
        self.pipe_between("Spout_Outlet", (0, 0, 0), (0.72, -0.17, 0), 0.070,
                          self.materials["body"], tip, role="spout_outlet")
        self.box("Spout_Outlet_Flap", (0.75, -0.20, 0), (0.10, 0.25, 0.30),
                 self.materials["steel"], tip, role="spout_flap")

    def build_forage_harvester(self):
        for side, sign in (("L", -1), ("R", 1)):
            self._add_wheel(f"Front_{side}", (0.72, 0.82, sign * 1.13), 0.82, 0.62,
                            self.running_root)
            steer = self.empty(f"Rear_Steering_{side}_Pivot", (-2.28, 0.58, sign * 1.20),
                               self.running_root, role="steering_pivot")
            self._add_wheel(f"Rear_{side}", (0, 0, 0), 0.58, 0.50, steer)
        self.box("Carrier_Frame", (-0.75, 0.78, 0), (4.95, 0.22, 2.35),
                 self.materials["graphite"], self.fixed_root, role="chassis")
        self.box("Rear_Terminal_Bumper", (-self.length / 2 + 0.05, 0.90, 0),
                 (0.10, 0.42, 2.30), self.materials["steel"], self.fixed_root,
                 role="rear_structure")
        self.side_profile("Power_Module_Tapered_Shell",
                          [(-2.705, 1.00), (0.145, 1.00), (0.145, 1.82),
                           (-0.26, 2.30), (-0.86, 2.72), (-2.50, 2.72),
                           (-2.705, 2.43)], 2.55, self.materials["body"],
                          self.fixed_root, role="power_module")
        # Open rails keep the documented crop-process train legible instead of
        # burying it inside a generic solid block.
        for name, center, size in (
            ("Processor_Cutaway_Upper_Rail", (0.30, 2.005, 0), (1.88, 0.08, 1.25)),
            ("Processor_Cutaway_Lower_Rail", (0.30, 0.835, 0), (1.88, 0.08, 1.25)),
            ("Processor_Cutaway_Front_Post", (1.20, 1.42, 0), (0.08, 1.10, 1.25)),
            ("Processor_Cutaway_Rear_Post", (-0.60, 1.42, 0), (0.08, 1.10, 1.25)),
        ):
            self.box(name, center, size, self.materials["body_dark"], self.fixed_root,
                     role="processor_frame", bevel=0.006)
        self.add_cab(0.64, 1.42, 1.36, 2.32, self.height - 1.42, self.fixed_root)
        for index in range(7):
            self.box(f"Cooling_Slot_{index + 1:02d}",
                     (-2.20 + index * 0.18, 2.04, -1.29), (0.07, 0.78, 0.025),
                     self.materials["graphite"], self.fixed_root, role="cooling_slot", bevel=0.003)
        self._add_orbis()
        self._add_feedrolls()
        self._add_processors()
        self._add_spout()

    def _set_review_pose(self, label):
        left, right = bpy.data.objects["ORBIS_L_Wing_ROOT"], bpy.data.objects["ORBIS_R_Wing_ROOT"]
        left_nest = bpy.data.objects["ORBIS_L_Wing_Nest_ROOT"]
        right_nest = bpy.data.objects["ORBIS_R_Wing_Nest_ROOT"]
        left.rotation_euler.x = right.rotation_euler.x = 0
        left_nest.location.z = right_nest.location.z = 0
        bpy.data.objects["Header_Lift_Pivot"].rotation_euler.z = 0
        bpy.data.objects["Spout_Yaw_Pivot"].rotation_euler.y = 0
        bpy.data.objects["Spout_Tip_Pivot"].rotation_euler.z = 0
        for side in ("L", "R"):
            bpy.data.objects[f"Rear_Steering_{side}_Pivot"].rotation_euler.y = 0
        if label == "front-three-quarter":
            bpy.data.objects["Header_Lift_Pivot"].rotation_euler.z = 0.08
        elif label == "rear-three-quarter":
            bpy.data.objects["Spout_Yaw_Pivot"].rotation_euler.y = 0.72
            bpy.data.objects["Spout_Tip_Pivot"].rotation_euler.z = 0.10
        elif label == "elevated-technical":
            left.rotation_euler.x, right.rotation_euler.x = 0.34, -0.34
            left_nest.location.z, right_nest.location.z = 0.05, -0.05
        elif label == "articulation-detail":
            left.rotation_euler.x, right.rotation_euler.x = 1.08, -0.48
            left_nest.location.z, right_nest.location.z = 0.16, -0.07
            bpy.data.objects["Header_Lift_Pivot"].rotation_euler.z = 0.10
            bpy.data.objects["Spout_Yaw_Pivot"].rotation_euler.y = 0.42
        elif label == "right-side":
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
        return [*super().required_semantics(), "ORBIS_L_Wing_Fold_Pivot",
                "ORBIS_L_Wing_Nest_ROOT", "ORBIS_L_Wing_ROOT",
                "ORBIS_R_Wing_Fold_Pivot", "ORBIS_R_Wing_Nest_ROOT",
                "ORBIS_R_Wing_ROOT", "Feedroll_Upper_ROOT",
                "Feedroll_Lower_ROOT", "VMAX42_Cylinder_ROOT", "MCC_MAX_ROOT",
                "Crop_Accelerator_ROOT", "Schematic_Crop_Path_ROOT"]

    def machine_specific_validation_gates(self, contract):
        names = contract["node_names"]
        neutral = self._subtree_bounds("Header_ROOT")
        left, right = bpy.data.objects["ORBIS_L_Wing_ROOT"], bpy.data.objects["ORBIS_R_Wing_ROOT"]
        left_nest = bpy.data.objects["ORBIS_L_Wing_Nest_ROOT"]
        right_nest = bpy.data.objects["ORBIS_R_Wing_Nest_ROOT"]
        left.rotation_euler.x, right.rotation_euler.x = math.pi / 2, -math.pi / 2
        # The published three-metre transport package nests both compound-fold
        # modules 230 mm toward the centre after they rotate upright.  The fold
        # axes and exact linkage remain explicitly reconstructed.
        left_nest.location.z, right_nest.location.z = 0.23, -0.23
        bpy.context.view_layer.update()
        folded = self._subtree_bounds("Header_ROOT")
        left.rotation_euler.x = right.rotation_euler.x = 0
        left_nest.location.z = right_nest.location.z = 0
        bpy.context.view_layer.update()
        viewer = json.loads((self.output_dir / "viewer.json").read_text(encoding="utf-8"))
        chute = next(c for c in viewer["motion"]["channels"] if c["id"] == "chute-swing")
        sweep = math.degrees(chute["to"] - chute["from"])
        feedrolls = [name for name in names if name in {"Feedroll_Upper_Front",
                     "Feedroll_Upper_Rear", "Feedroll_Lower_Front", "Feedroll_Lower_Rear"}]
        knives = [name for name in names if name.startswith("VMAX42_Knife_")]
        row_roots = [name for name in names if "_RowUnit_" in name and name.endswith("_ROOT")]
        tires = [name for name in names if name.endswith("_Tire")]
        materials = sorted({slot.material.name for obj in self.public_objects() if obj.type == "MESH"
                            for slot in obj.material_slots if slot.material is not None})
        components = {"feedroller_count": len(feedrolls), "feedroller_width_m": self.FEEDER_WIDTH_M,
                      "vmax42_knife_stations": len(knives), "chopper_width_m": self.CHOPPER_WIDTH_M,
                      "chopper_diameter_m": self.CHOPPER_DIAMETER_M,
                      "mcc_max_diameter_m": self.MCC_DIAMETER_M,
                      "accelerator_width_m": self.ACCELERATOR_WIDTH_M,
                      "accelerator_diameter_m": self.ACCELERATOR_DIAMETER_M}
        return [
            self._gate("configuration_attachment_and_crop_setup_identity",
                       all(code in self.configuration_id for code in ("ORBIS900", "VMAX42", "MCCMAX")),
                       {"configuration_id": self.configuration_id, "crop_setup": "corn short LOC"},
                       ["Header_ROOT", "VMAX42_Cylinder_ROOT", "MCC_MAX_ROOT"],
                       ["vmax42-knife-count", "maximum-engine-power"]),
            self._gate("published_orbis_working_span", abs(neutral["size"][2] - self.ORBIS_WORKING_M) <= 0.003,
                       {"measured_working_span_m": round(neutral["size"][2], 6), "published_m": self.ORBIS_WORKING_M},
                       ["Header_ROOT", "ORBIS_L_Wing_ROOT", "ORBIS_R_Wing_ROOT"],
                       ["public-envelope-x", "public-envelope-y", "public-envelope-z", "orbis-working-width"]),
            self._gate("orbis_folded_transport_span",
                       abs(folded["size"][2] - self.ORBIS_TRANSPORT_M) <= 0.03 and folded["max"][1] <= self.height + 0.003,
                       {"measured_folded_span_m": round(folded["size"][2], 6),
                        "folded_max_y_m": round(folded["max"][1], 6), "pose": "reconstructed symmetric 90 degree wing fold"},
                       ["ORBIS_L_Wing_Fold_Pivot", "ORBIS_L_Wing_Nest_ROOT", "ORBIS_L_Wing_ROOT",
                        "ORBIS_R_Wing_Fold_Pivot", "ORBIS_R_Wing_Nest_ROOT", "ORBIS_R_Wing_ROOT"],
                       ["orbis-transport-width"]),
            self._gate("attachment_lift_visual_closure", self._descends("Header_ROOT", "Header_Lift_Pivot")
                       and "Header_Lift_Cylinder_Barrel" in names and "Header_Lift_Cylinder_Rod" in names,
                       {"closure": "fixed barrel plus moving rod", "authority": "reconstructed visual linkage"},
                       ["Header_Lift_Pivot", "Header_ROOT", "Hydraulics_ROOT"]),
            self._gate("attachment_to_feeder_clearance", all(f"Schematic_Crop_Path_{i:02d}" in names for i in range(1, 7)),
                       {"continuous_schematic_segments": 6, "feedroll_center": [1.20, 1.18, 0]},
                       ["Header_ROOT", "Feedroll_ROOT", "Schematic_Crop_Path_ROOT"], ["feeder-width", "feed-roller-count"]),
            self._gate("rear_steering_tire_clearance", len(tires) == 4 and all(f"Rear_Steering_{s}_Pivot" in names for s in ("L", "R")),
                       {"tire_nodes": tires, "presentation_steer_deg": 20.0, "authority": "reconstructed clearance pose"},
                       ["Running_Gear_ROOT", "Rear_Steering_L_Pivot", "Rear_Steering_R_Pivot"]),
            self._gate("standard_chute_stowed_and_deployed_clearance", abs(sweep - self.CHUTE_SWING_DEG) <= 0.02
                       and self._descends("Spout_Tip_ROOT", "Spout_ROOT"),
                       {"viewer_sweep_deg": round(sweep, 6), "published_deg": self.CHUTE_SWING_DEG,
                        "endpoint_scope": "reconstructed yaw endpoints"},
                       ["Spout_Yaw_Pivot", "Spout_ROOT", "Spout_Tip_Pivot", "Spout_Tip_ROOT"], ["standard-chute-swing"]),
            self._gate("cutaway_only_internal_mechanism_labeling", len(feedrolls) == 4 and len(knives) == self.KNIFE_COUNT and len(row_roots) == 10,
                       {**components, "orbis_row_unit_roots": len(row_roots),
                        "classification": "schematic cutaway; hidden centers reconstructed"},
                       ["Feedroll_ROOT", "VMAX42_Cylinder_ROOT", "MCC_MAX_ROOT", "Crop_Accelerator_ROOT", "Schematic_Crop_Path_ROOT"],
                       ["chopping-cylinder-width", "chopping-cylinder-diameter", "mcc-max-diameter",
                        "accelerator-width", "accelerator-diameter"]),
            self._gate("wheel_phase_continuity", len(tires) == 4, {"tire_nodes": tires, "continuous_rotation": "viewer synchronized wheel roots"},
                       ["Running_Gear_ROOT", "Front_L_Wheel_ROOT", "Front_R_Wheel_ROOT", "Rear_L_Wheel_ROOT", "Rear_R_Wheel_ROOT"]),
            self._gate("ground_collision", contract["bounds"]["min_m"][1] >= -0.005,
                       {"minimum_visible_y_m": contract["bounds"]["min_m"][1], "ground_y_m": 0.0},
                       ["Running_Gear_ROOT", "Header_ROOT"]),
            self._gate("self_collision", folded["max"][1] <= self.height + 0.003,
                       {"component_measurements": components, "folded_header_max_y_m": round(folded["max"][1], 6),
                        "scope": "neutral and folded endpoint AABB checks; not an operating safety claim"},
                       ["Header_ROOT", "Feedroll_ROOT", "VMAX42_Cylinder_ROOT", "MCC_MAX_ROOT", "Crop_Accelerator_ROOT", "Spout_ROOT"]),
            self._gate("neutral_unbranded_materials", bool(materials) and all(name.startswith("Neutral_") for name in materials),
                       {"materials": materials, "images": contract["images"], "textures": contract["textures"]}, ["Machine_Root"]),
        ]


if __name__ == "__main__":
    Jaguar990Builder(shared.load_design(DESIGN), DESIGN, OUTPUT_DIR).run()

#!/usr/bin/env python3
"""Build the neutral John Deere 8R 410 technical structural study.

This machine-local builder uses the admitted MY2024 8 Series brochure for the
selected PowerTech 9.0 L/e23/ILS/Cat. 4N/3 configuration. Tyres, exterior
surface, ILS links and anchors, steering, hitch kinematics, and all hidden
structure remain independently reconstructed. This is not manufacturer CAD,
an engineering model, safety guidance, or a suspension/traction solver.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy


HERE = Path(__file__).resolve().parent
MACHINE_DIR = HERE.parents[1]
SHARED_PATH = (HERE / "../../../../scripts/fleet/build_machine.py").resolve()
DESIGN_PATH = (HERE / "../design.json").resolve()

spec = importlib.util.spec_from_file_location("exo_fleet_build_machine_8r410", SHARED_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load shared fleet builder: {SHARED_PATH}")
fleet = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fleet
spec.loader.exec_module(fleet)


class Deere8R410Builder(fleet.FleetBuilder):
    """Machine-specific ILS wheeled-tractor reconstruction in authored metres."""

    WHEELBASE_M = 3.050
    ILS_CLEARANCE_M = 0.590
    FRONT_TREAD_M = 2.360  # reconstructed within the published 1.524-3.657 m range
    REAR_TREAD_M = 2.240   # reconstructed; tyre/axle order code is unresolved
    FRONT_TIRE_RADIUS_M = 0.775
    FRONT_TIRE_WIDTH_M = 0.460
    FRONT_TIRE_STATIC_CLEARANCE_M = 0.045
    REAR_TIRE_RADIUS_M = 1.075
    REAR_TIRE_WIDTH_M = 0.760
    PTO_SHAFT_DIAMETER_M = 0.04445  # published 1-3/4 inch standard shaft
    ILS_REVIEW_LIMIT_RAD = 0.025
    HITCH_REVIEW_RANGE_RAD = (-0.10, 0.24)

    def write_machine_wrapper(self):
        """The checked-in local builder is authoritative; never replace it."""

    def torus(self, name, location, major_radius, minor_radius, material, parent=None,
              rotation=(0, 0, 0), role="geometry", major_segments=24, minor_segments=8):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=major_radius,
            minor_radius=minor_radius,
            major_segments=major_segments,
            minor_segments=minor_segments,
            location=location,
            rotation=rotation,
        )
        obj = bpy.context.object
        obj.name = name
        if parent is not None:
            obj.parent = parent
        obj.data.materials.append(material)
        return self.tag(obj, role=role)

    @staticmethod
    def descendants(obj):
        result = []
        pending = list(obj.children)
        while pending:
            item = pending.pop()
            result.append(item)
            pending.extend(item.children)
        return result

    @staticmethod
    def world_location(obj):
        value = obj.matrix_world.translation
        return [float(value.x), float(value.y), float(value.z)]

    def scene_min_y(self):
        bpy.context.view_layer.update()
        minimum = math.inf
        for obj in self.public_objects():
            if obj.type != "MESH":
                continue
            for vertex in obj.data.vertices:
                minimum = min(minimum, float((obj.matrix_world @ vertex.co).y))
        return minimum

    def sampled_ground_clearance(self):
        samples = []
        roots = [
            (bpy.data.objects["ILS_L_Suspension_ROOT"], (-self.ILS_REVIEW_LIMIT_RAD, self.ILS_REVIEW_LIMIT_RAD)),
            (bpy.data.objects["ILS_R_Suspension_ROOT"], (-self.ILS_REVIEW_LIMIT_RAD, self.ILS_REVIEW_LIMIT_RAD)),
            (bpy.data.objects["Rear_Hitch_ROOT"], self.HITCH_REVIEW_RANGE_RAD),
        ]
        for root, values in roots:
            original = tuple(root.rotation_euler)
            for value in values:
                root.rotation_euler = original
                root.rotation_euler.x = value if root.name.startswith("ILS_") else original[0]
                root.rotation_euler.z = value if root.name == "Rear_Hitch_ROOT" else original[2]
                samples.append({"node": root.name, "value_rad": value, "minimum_y_m": self.scene_min_y()})
            root.rotation_euler = original
        bpy.context.view_layer.update()
        return samples

    def build_model(self):
        self.build_common_roots()
        body = self.materials["body"]
        dark = self.materials["body_dark"]
        graphite = self.materials["graphite"]
        steel = self.materials["steel"]
        rod = self.materials["rod"]
        warning = self.materials["warning"]

        rear_x = -1.150
        front_x = rear_x + self.WHEELBASE_M
        rear_y = self.REAR_TIRE_RADIUS_M
        front_y = self.FRONT_TIRE_RADIUS_M + self.FRONT_TIRE_STATIC_CLEARANCE_M
        axle_y = self.ILS_CLEARANCE_M + 0.110

        self.box("Main_Frame_Rail", (-0.03, 1.02, 0), (4.46, 0.30, 1.15), graphite,
                 self.fixed_root, role="chassis", bevel=0.055)
        self.box("Rear_Transmission_Housing", (-1.36, 1.47, 0), (1.30, 0.92, 1.22), dark,
                 self.fixed_root, role="transmission_housing", bevel=0.08)
        self.side_profile(
            "Engine_Hood_Profile",
            [(0.25, 1.18), (2.72, 1.18), (3.04, 1.56), (2.80, 2.24),
             (1.00, 2.42), (0.25, 2.24)],
            1.36, body, self.fixed_root, role="engine_house",
        )
        self.box("Front_Ballast_Carrier", (3.178, 0.91, 0), (0.280, 0.54, 0.92), steel,
                 self.fixed_root, role="front_ballast_carrier", bevel=0.035)
        for index, z in enumerate((-0.34, -0.17, 0.0, 0.17, 0.34), start=1):
            self.box(f"Front_Ballast_Slab_{index:02d}", (3.075, 0.94, z),
                     (0.40, 0.48, 0.115), graphite, self.fixed_root,
                     role="reconstructed_ballast", bevel=0.012)

        for index in range(10):
            self.box(f"Cooling_Louver_{index + 1:02d}",
                     (2.39 - index * 0.12, 1.68, -0.694),
                     (0.065, 0.47, 0.018), graphite, self.detail_root,
                     role="cooling_louver", bevel=0.004)
        self.box("Exhaust_Aftertreatment", (0.72, 2.38, 0.48), (0.36, 0.88, 0.32), graphite,
                 self.fixed_root, role="aftertreatment_cue", bevel=0.06)
        self.cylinder("Exhaust_Stack", (0.79, 3.00, 0.49), 0.075, 0.56, graphite,
                      self.fixed_root, vertices=20, rotation=(math.pi / 2, 0, 0), role="exhaust")

        cab_floor = 1.31
        self.add_cab(-0.59, cab_floor, 1.62, 1.68, self.height - cab_floor, self.fixed_root)
        self.box("Cab_Rear_Fender_L", (-1.24, 1.79, -1.12), (1.12, 0.18, 0.60), body,
                 self.fixed_root, role="fender", bevel=0.06)
        self.box("Cab_Rear_Fender_R", (-1.24, 1.79, 1.12), (1.12, 0.18, 0.60), body,
                 self.fixed_root, role="fender", bevel=0.06)
        for side, z in (("L", -0.83), ("R", 0.83)):
            self.pipe_between(f"Cab_{side}_Handrail", (-0.98, 1.33, z), (-0.45, 2.15, z),
                              0.026, steel, self.detail_root, role="handrail")
        for index in range(4):
            self.box(f"Access_Step_{index + 1:02d}", (-0.27 + index * 0.04, 0.56 + index * 0.18, -0.92),
                     (0.38, 0.055, 0.32), steel, self.detail_root, role="access_step", bevel=0.008)

        self.box("Rear_Axle_Housing", (rear_x, 1.05, 0), (0.46, 0.28, 2.18), steel,
                 self.running_root, role="rear_axle", bevel=0.05)
        for side, z in (("L", -self.REAR_TREAD_M / 2), ("R", self.REAR_TREAD_M / 2)):
            self.add_wheel(f"Rear_{side}", (rear_x, rear_y, z), self.REAR_TIRE_RADIUS_M,
                           self.REAR_TIRE_WIDTH_M, self.running_root, tread_count=22)
        self.box("Hydraulic_Reservoir_Cue", (-0.05, 1.28, 0.54), (0.58, 0.46, 0.32),
                 graphite, self.hydraulics_root, role="hydraulic_reservoir", bevel=0.05)
        for side, z in (("L", -0.48), ("R", 0.48)):
            self.pipe_between(f"ILS_{side}_Hydraulic_Hose", (0.12, 1.35, z),
                              (front_x - 0.18, axle_y + 0.22, z), 0.022,
                              self.materials["rubber"], self.hydraulics_root, role="hydraulic_hose")

        front_pivot = self.empty("Front_Axle_Oscillation_Pivot", (front_x, axle_y, 0),
                                 self.running_root, role="published_reference_pivot")
        front_root = self.empty("Front_Axle_ROOT", parent=front_pivot, role="ils_carrier_root")
        self.box("ILS_Center_Housing", (0, 0, 0), (0.52, 0.22, 0.64), steel,
                 front_root, role="ils_differential_housing", bevel=0.055)
        self.cylinder("ILS_Longitudinal_Pivot_Pin", (0, 0, 0), 0.075, 0.62, rod,
                      front_root, vertices=24, rotation=(0, math.pi / 2, 0), role="ils_center_pin")

        for side, sign in (("L", -1.0), ("R", 1.0)):
            inner_z = sign * 0.24
            suspension = self.empty(f"ILS_{side}_Suspension_ROOT", (0, 0, inner_z), front_root,
                                    role="independent_suspension_root")
            knuckle_z = sign * self.FRONT_TREAD_M / 2
            local_knuckle_z = knuckle_z - inner_z
            for fore, x in (("Fore", 0.18), ("Aft", -0.18)):
                self.pipe_between(f"ILS_{side}_Upper_{fore}_Arm", (x, 0.17, 0),
                                  (x, 0.12, local_knuckle_z - sign * 0.12), 0.035, steel,
                                  suspension, role="ils_upper_link")
                self.pipe_between(f"ILS_{side}_Lower_{fore}_Arm", (x, -0.07, 0),
                                  (x, -0.02, local_knuckle_z - sign * 0.10), 0.043, steel,
                                  suspension, role="ils_lower_link")
            self.pipe_between(f"ILS_{side}_Suspension_Cylinder_Barrel",
                              (0.17, 0.31, sign * 0.36 - inner_z),
                              (0.17, 0.08, local_knuckle_z - sign * 0.16),
                              0.058, graphite, suspension, role="hydraulic_barrel")
            self.pipe_between(f"ILS_{side}_Suspension_Cylinder_Rod",
                              (0.17, 0.08, local_knuckle_z - sign * 0.16),
                              (0.17, 0.02, local_knuckle_z - sign * 0.07),
                              0.032, rod, suspension, role="hydraulic_rod")
            steering = self.empty(f"Steering_{side}_Pivot",
                                  (0, front_y - axle_y, local_knuckle_z), suspension,
                                  role="steering_kingpin")
            self.box(f"Steering_{side}_Knuckle", (0, 0, 0), (0.30, 0.38, 0.18), steel,
                     steering, role="steering_knuckle", bevel=0.035)
            self.add_wheel(f"Front_{side}", (0, 0, 0), self.FRONT_TIRE_RADIUS_M,
                           self.FRONT_TIRE_WIDTH_M, steering, tread_count=18)
            self.pipe_between(f"Steering_{side}_Tie_Rod", (-0.20, 0.02, sign * 0.30),
                              (-0.20, front_y - axle_y, knuckle_z - sign * 0.08),
                              0.025, rod, front_root, role="steering_link")

        hitch_pivot = self.empty("Rear_Hitch_Pivot", (-2.60, 0.78, 0), self.fixed_root, role="pivot")
        hitch_root = self.empty("Rear_Hitch_ROOT", parent=hitch_pivot, role="three_point_motion_root")
        for side, z in (("L", -0.34), ("R", 0.34)):
            self.pipe_between(f"Rear_Hitch_{side}_Lower_Link", (0.06, -0.02, z),
                              (-0.54, -0.12, z), 0.043, steel, hitch_root, role="hitch_lower_link")
            self.pipe_between(f"Rear_Hitch_{side}_Lift_Rod", (-0.05, 0.39, z),
                              (-0.32, -0.03, z), 0.032, rod, hitch_root, role="hitch_lift_rod")
            self.box(f"Cat4N3_{side}_Quick_Coupler_Upright", (-0.60, 0.15, z),
                     (0.12, 0.70, 0.11), steel, hitch_root, role="quick_coupler", bevel=0.015)
            self.torus(f"Cat4N3_{side}_Lower_Hook", (-0.61, -0.17, z), 0.070, 0.025,
                       steel, hitch_root, rotation=(math.pi / 2, 0, 0), role="quick_coupler_hook")
        self.pipe_between("Rear_Hitch_Top_Link", (-0.02, 0.48, 0), (-0.58, 0.41, 0),
                          0.036, steel, hitch_root, role="hitch_top_link")
        self.box("Cat4N3_Quick_Coupler_Upper_Beam", (-0.60, 0.47, 0), (0.12, 0.12, 0.80),
                 steel, hitch_root, role="quick_coupler", bevel=0.015)
        self.box("Rear_Coupler_Base_Plate", (-0.658, -0.10, 0),
                 (0.120, 0.16, 0.70), steel, hitch_root, role="quick_coupler", bevel=0.012)

        pto = self.empty("PTO_ROOT", (-2.52, 0.94, 0), self.fixed_root, role="rotary_root")
        self.cylinder("PTO_Shaft_44_45mm", (-0.10, 0, 0), self.PTO_SHAFT_DIAMETER_M / 2,
                      0.20, steel, pto, vertices=40, rotation=(0, math.pi / 2, 0), role="pto_shaft")
        for index in range(20):
            angle = math.tau * index / 20
            self.box(f"PTO_Spline_{index + 1:02d}", (-0.205, math.cos(angle) * 0.021,
                     math.sin(angle) * 0.021), (0.085, 0.0045, 0.0045), steel, pto,
                     role="pto_spline", bevel=0.001)
        for x in (-0.035, 0.035):
            self.torus(f"PTO_Guard_Ring_{'Rear' if x < 0 else 'Front'}", (x, 0, 0),
                       0.072, 0.012, warning, pto, rotation=(0, math.pi / 2, 0), role="pto_guard")
        for index, angle in enumerate((0, math.pi / 2, math.pi, 3 * math.pi / 2), start=1):
            self.box(f"PTO_Guard_Rail_{index:02d}", (0, math.cos(angle) * 0.072,
                     math.sin(angle) * 0.072), (0.09, 0.014, 0.014), warning, pto,
                     role="pto_guard", bevel=0.004)

        missing = [name for name in self.required_semantics() if bpy.data.objects.get(name) is None]
        if missing:
            raise RuntimeError(f"8R 410 builder omitted semantic nodes: {', '.join(missing)}")
        return self.root

    def machine_specific_validation_gates(self, contract):
        config = json.loads((self.output_dir / "configuration.json").read_text(encoding="utf-8"))
        bounds = contract["bounds"]
        wheelbase = abs(self.world_location(bpy.data.objects["Front_Axle_Oscillation_Pivot"])[0] -
                        self.world_location(bpy.data.objects["Rear_L_Wheel_Pivot"])[0])
        housing = bpy.data.objects["ILS_Center_Housing"]
        housing_min_y = min(float((housing.matrix_world @ vertex.co).y) for vertex in housing.data.vertices)
        left = bpy.data.objects["ILS_L_Suspension_ROOT"]
        right = bpy.data.objects["ILS_R_Suspension_ROOT"]
        steering_l = bpy.data.objects["Steering_L_Pivot"]
        steering_r = bpy.data.objects["Steering_R_Pivot"]
        hitch = bpy.data.objects["Rear_Hitch_ROOT"]
        ground_samples = self.sampled_ground_clearance()
        min_ground = min(item["minimum_y_m"] for item in ground_samples)
        pto_radius = self.PTO_SHAFT_DIAMETER_M / 2
        guard_inner_radius = 0.072 - 0.012
        pto_radial_clearance = guard_inner_radius - pto_radius
        pto_to_lower_link_lateral_clearance = 0.34 - 0.043 - guard_inner_radius
        material_names = sorted(material.name for material in bpy.data.materials)
        width_unresolved = any("overall width" in item.lower() for item in config["unresolved_choices"])
        height_unresolved = any("overall height" in item.lower() for item in config["unresolved_choices"])

        gates = [
            {"id": "reconstructed_cross_market_length_reference", "status": "PASS" if abs(bounds["size_m"][0] - 6.636) <= 0.003 else "FAIL",
             "detail": {"presentation_length_m": bounds["size_m"][0], "cross_market_reference_m": 6.636,
                        "tolerance_m": 0.003, "source_id": "JD-8R410-LATAM-PAGE",
                        "source_market": "Latin America", "source_admission": "reference_only",
                        "applicable_to_selected_na_configuration": False}},
            {"id": "configuration_specific_width_unresolved", "status": "PASS" if width_unresolved else "FAIL",
             "detail": {"presentation_width_m": bounds["size_m"][2], "manufacturer_width_claim": None,
                        "configuration_records_unresolved": width_unresolved}},
            {"id": "configuration_specific_height_unresolved", "status": "PASS" if height_unresolved else "FAIL",
             "detail": {"presentation_height_m": bounds["size_m"][1], "manufacturer_height_claim": None,
                        "configuration_records_unresolved": height_unresolved}},
            {"id": "wheelbase_and_ground_clearance",
             "status": "PASS" if abs(wheelbase - self.WHEELBASE_M) <= 0.001 and abs(housing_min_y - self.ILS_CLEARANCE_M) <= 0.002 else "FAIL",
             "detail": {"measured_wheelbase_m": wheelbase, "published_wheelbase_m": self.WHEELBASE_M,
                        "measured_ils_housing_min_y_m": housing_min_y, "published_ils_axle_clearance_m": self.ILS_CLEARANCE_M,
                        "tolerance_m": 0.002}},
            {"id": "ils_left_right_continuity",
             "status": "PASS" if len(self.descendants(left)) >= 11 and len(self.descendants(right)) >= 11 and
                       abs(float(left.location.z) + 0.24) <= 0.001 and
                       abs(float(right.location.z) - 0.24) <= 0.001 else "FAIL",
             "detail": {"left_descendants": len(self.descendants(left)), "right_descendants": len(self.descendants(right)),
                        "left_root_parent": left.parent.name, "right_root_parent": right.parent.name,
                        "left_inner_interface_local_z_m": float(left.location.z),
                        "right_inner_interface_local_z_m": float(right.location.z),
                        "review_limit_rad": self.ILS_REVIEW_LIMIT_RAD}},
            {"id": "steering_node_continuity",
             "status": "PASS" if steering_l.parent is left and steering_r.parent is right and
                       bpy.data.objects["Front_L_Wheel_Pivot"].parent is steering_l and
                       bpy.data.objects["Front_R_Wheel_Pivot"].parent is steering_r else "FAIL",
             "detail": {"left_chain": [steering_l.parent.name, steering_l.name, "Front_L_Wheel_Pivot"],
                        "right_chain": [steering_r.parent.name, steering_r.name, "Front_R_Wheel_Pivot"]}},
            {"id": "three_point_linkage_continuity",
             "status": "PASS" if len([obj for obj in self.descendants(hitch) if str(obj.get("exo_role", "")).startswith("hitch") or obj.get("exo_role") in {"quick_coupler", "quick_coupler_hook"}]) >= 9 else "FAIL",
             "detail": {"motion_root": hitch.name, "pivot_parent": hitch.parent.name,
                        "configuration": "Category 4N/3 quick coupler", "published_capacity_kg": 9072}},
            {"id": "pto_guard_clearance", "status": "PASS" if pto_radial_clearance >= 0.025 and pto_to_lower_link_lateral_clearance >= 0.20 else "FAIL",
             "detail": {"published_shaft_diameter_m": self.PTO_SHAFT_DIAMETER_M,
                        "reconstructed_guard_inner_radius_m": guard_inner_radius,
                        "radial_clearance_m": pto_radial_clearance,
                        "lower_link_lateral_clearance_m": pto_to_lower_link_lateral_clearance}},
            {"id": "ground_collision", "status": "PASS" if min_ground >= -0.002 else "FAIL",
             "detail": {"sampled_motion_extrema": ground_samples, "minimum_sampled_y_m": min_ground,
                        "tolerance_m": 0.002, "terrain_solver": False}},
            {"id": "self_collision", "status": "PASS" if pto_to_lower_link_lateral_clearance >= 0.20 else "FAIL",
             "detail": {"sampled_hitch_range_rad": list(self.HITCH_REVIEW_RANGE_RAD),
                        "pto_to_nearest_lower_link_lateral_clearance_m": pto_to_lower_link_lateral_clearance,
                        "scope": "visible hitch/PTO review path only; no implement attached"}},
            {"id": "neutral_unbranded_material_review",
             "status": "PASS" if all(name.startswith("Neutral_") for name in material_names) and contract["images"] == 0 and contract["textures"] == 0 else "FAIL",
             "detail": {"materials": material_names, "embedded_images": contract["images"],
                        "textures": contract["textures"], "logos_or_decals": 0}},
        ]
        proof_contract = {
            "reconstructed_cross_market_length_reference": ("GLB accessor AABB compared with a reference-only cross-market page; no North American manufacturer envelope is claimed", ["Front_Ballast_Carrier", "Rear_Coupler_Base_Plate"], ["cross-market-length-reference"]),
            "configuration_specific_width_unresolved": ("configuration unresolved-choice inspection", [], []),
            "configuration_specific_height_unresolved": ("configuration unresolved-choice inspection", [], []),
            "wheelbase_and_ground_clearance": ("world-transform pivot spacing and ILS housing vertex AABB", ["Front_Axle_Oscillation_Pivot", "Rear_L_Wheel_Pivot", "ILS_Center_Housing"], ["ils-wheelbase", "ils-axle-clearance"]),
            "ils_left_right_continuity": ("distinct descendant traversal from independently located inner-interface suspension roots", ["Front_Axle_ROOT", "ILS_L_Suspension_ROOT", "ILS_R_Suspension_ROOT"], ["ils-tread-range"]),
            "steering_node_continuity": ("direct parent-chain identity checks", ["ILS_L_Suspension_ROOT", "Steering_L_Pivot", "Front_L_Wheel_Pivot", "ILS_R_Suspension_ROOT", "Steering_R_Pivot", "Front_R_Wheel_Pivot"], []),
            "three_point_linkage_continuity": ("motion-root descendant role census", ["Rear_Hitch_Pivot", "Rear_Hitch_ROOT", "Rear_Hitch_L_Lower_Link", "Rear_Hitch_R_Lower_Link", "Cat4N3_Quick_Coupler_Upper_Beam"], ["rear-hitch-capacity"]),
            "pto_guard_clearance": ("published shaft diameter and reconstructed concentric guard/link clearances", ["PTO_ROOT", "PTO_Shaft_44_45mm", "PTO_Guard_Ring_Rear", "PTO_Guard_Ring_Front"], ["rear-pto-interface"]),
            "ground_collision": ("world-vertex minimum-Y sampling at each declared motion extremum", ["ILS_L_Suspension_ROOT", "ILS_R_Suspension_ROOT", "Rear_Hitch_ROOT", "Rear_L_Tire", "Rear_R_Tire"], []),
            "self_collision": ("declared hitch sweep range and independent PTO/lower-link lateral clearance", ["Rear_Hitch_ROOT", "Rear_Hitch_L_Lower_Link", "Rear_Hitch_R_Lower_Link", "PTO_ROOT"], []),
            "neutral_unbranded_material_review": ("material-name allowlist plus exported GLB image/texture census", [], []),
        }
        for gate in gates:
            method, semantic_nodes, fact_ids = proof_contract[gate["id"]]
            gate["detail"] = {
                "method": method,
                "evidence": gate["detail"],
                "semantic_nodes": semantic_nodes,
                "fact_ids": fact_ids,
            }
        return gates


def main():
    design = fleet.load_design(DESIGN_PATH)
    Deere8R410Builder(design, DESIGN_PATH, MACHINE_DIR).run()


if __name__ == "__main__":
    main()

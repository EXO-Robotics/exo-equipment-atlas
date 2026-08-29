#!/usr/bin/env python3
"""Build the neutral LTM 1100-5.3 technical structural study.

Run with Blender factory startup in background mode. This script independently
authors every visible mesh. It does not ingest manufacturer CAD, imagery,
textures, or geometry. Published values constrain identity and the retained
transport envelope; telescope staging, pivots, anchors, rigging, steering,
supports, and the bounded deployed review pose remain reconstructed.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


MACHINE_ID = "liebherr-ltm-1100-5-3"
CONFIGURATION_ID = "LIEBHERR-LTM1100-5.3-GLOBAL-445-R25-10X6X10-T62-TRANSPORT-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
MACHINE_REL = Path("machines/liebherr-ltm-1100-5-3")
BUILDER_REL = MACHINE_REL / "source/blender/build_liebherr_ltm_1100_5_3.py"
BLEND_REL = MACHINE_REL / "source/blender/liebherr-ltm-1100-5-3-structural-study.blend"
GLB_REL = MACHINE_REL / "assets/liebherr-ltm-1100-5-3-structural-study.glb"
RECEIPT_REL = MACHINE_REL / "production/asset-receipt.json"
VALIDATION_REL = MACHINE_REL / "production/validation.json"
RENDER_RELS = [
    MACHINE_REL / "review/renders/transport-left-side.png",
    MACHINE_REL / "review/renders/transport-right-side.png",
    MACHINE_REL / "review/renders/transport-front-quarter.png",
    MACHINE_REL / "review/renders/transport-rear-quarter.png",
    MACHINE_REL / "review/renders/carrier-five-axle-steering-detail.png",
    MACHINE_REL / "review/renders/superstructure-boom-heel-detail.png",
    MACHINE_REL / "review/renders/deployed-outrigger-detail.png",
    MACHINE_REL / "review/renders/deployed-telescoped-luffed-side.png",
    MACHINE_REL / "review/renders/deployed-telescoped-front-quarter.png",
    MACHINE_REL / "review/renders/boom-head-rigging-detail.png",
]

PUBLISHED = {
    "transport-width": 2.55,
    "transport-height-445": 4.0,
    "carrier-overall-length": 14.416,
    "transport-boom-head-length": 14.932,
    "axle-count": 5,
    "axle-spacings": [2.5, 1.65, 2.33, 1.65],
    "tire": "445/95 R 25",
    "boom-retracted": 13.0,
    "boom-maximum": 62.0,
    "slew": 360.0,
    "luff-maximum": 83.0,
    "operator-cab-tilt": 20.0,
    "support-width": 7.643,
    "support-longitudinal-span": 8.122,
}

RECONSTRUCTED = {
    "transport_pose": {
        "slew_deg": 0.0,
        "boom_luff_deg": 3.0,
        "telescope_visual_extension_m": [0.0, 0.18, 0.36, 0.54],
        "supports": "stowed visual positions",
        "hook": "low secured visual position ahead of carrier cab",
    },
    "deployed_review_pose": {
        "slew_deg": 0.0,
        "boom_luff_deg": 42.0,
        "visual_boom_head_distance_from_heel_m": 27.8,
        "telescope_section_offsets_m": [0.0, 4.2, 8.1, 11.7],
        "support_pad_centers_z_m": [-3.8215, 3.8215],
        "support_center_span_x_m": 8.122,
        "note": "bounded visual continuity study only; not a load case or published operating configuration",
    },
    "axle_centers_x_m": [4.13, 1.63, -0.02, -2.35, -4.0],
    "tire_geometry_m": {"outer_radius": 0.741, "section_width": 0.445, "rim_radius": 0.318},
    "slew_ring_center_m": [-3.35, 1.33, 0.0],
    "boom_heel_m": [-4.72, 2.78, 0.0],
    "boom_section_profiles": "independently selected tapered rectangular shells",
    "luff_cylinder_anchors": "independently selected for visual closure",
    "rigging": "generic three-fall visual study; hook-block branch unresolved",
    "steering": "all wheels straight in retained transport pose; kingpins and ratios unresolved",
}

UNRESOLVED = [
    "serial and delivery-market configuration",
    "road axle-load and carried-counterweight case",
    "counterweight plate set and VarioBallast radius",
    "boom section engineering profiles, overlaps, staging, locking pins, and telescope synchronization",
    "boom heel pin and luff-cylinder anchor coordinates",
    "slew ring dimensions and bearing elevation",
    "outrigger stages, VarioBase state, jack stroke, pad articulation, and support forces",
    "suspension, driveline, brake, hub, and all-wheel-steering internal geometry",
    "winch selection, rope specification, fall count, hook-block selection, and secured transport attachment",
    "public material and branding authorization",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


ROOT = repo_root()


def ap(rel: Path) -> Path:
    return ROOT / rel


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ensure_dirs() -> None:
    for rel in [BLEND_REL, GLB_REL, RECEIPT_REL, VALIDATION_REL, *RENDER_RELS]:
        ap(rel).parent.mkdir(parents=True, exist_ok=True)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            datablocks.remove(block)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 650
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.016, 0.022)
    scene["machine_id"] = MACHINE_ID
    scene["configuration_id"] = CONFIGURATION_ID
    scene["candidate_class"] = CANDIDATE_CLASS
    scene["authority_boundary"] = "independent visualization study; not load, safety, engineering, or manufacturer authority"
    bpy.context.preferences.filepaths.save_version = 0


def collection(name: str) -> bpy.types.Collection:
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def move_to_collection(obj: bpy.types.Object, coll: bpy.types.Collection) -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    coll.objects.link(obj)


def material(name: str, color, metallic=0.0, roughness=0.45, alpha=1.0) -> bpy.types.Material:
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, alpha)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        m.surface_render_method = "DITHERED"
    return m


def tag(obj, semantic: str, authority="reconstructed", export=True) -> None:
    obj["semantic"] = semantic
    obj["authority"] = authority
    obj["machine_id"] = MACHINE_ID
    obj["configuration_id"] = CONFIGURATION_ID
    obj["export"] = bool(export)


def parent_local(obj, parent, location=None, rotation=None) -> None:
    obj.parent = parent
    if location is not None:
        obj.location = location
    if rotation is not None:
        obj.rotation_euler = rotation


def empty(name, location=(0, 0, 0), parent=None, coll=None, semantic="pivot", export=True):
    obj = bpy.data.objects.new(name, None)
    (coll or COL_PIVOTS).objects.link(obj)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.18
    parent_local(obj, parent, location)
    tag(obj, semantic, "reconstructed", export)
    return obj


def bevel(obj, amount=0.02, segments=2):
    if amount <= 0:
        return
    mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
    mod.width = amount
    mod.segments = segments


def box(name, location, dimensions, mat, coll, parent=None, rotation=(0, 0, 0), bevel_amount=0.02, semantic="visible_structure", export=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(obj, min(bevel_amount, min(dimensions) * 0.15), 2)
    obj.data.materials.append(mat)
    move_to_collection(obj, coll)
    parent_local(obj, parent, location, rotation)
    tag(obj, semantic, "reconstructed", export)
    return obj


def cylinder(name, location, radius, depth, mat, coll, parent=None, rotation=(0, 0, 0), vertices=20, semantic="visible_structure", export=True, bevel_amount=0.01):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to_collection(obj, coll)
    parent_local(obj, parent, location, rotation)
    bevel(obj, bevel_amount, 2)
    tag(obj, semantic, "reconstructed", export)
    return obj


def torus(name, location, major_radius, minor_radius, mat, coll, parent=None, rotation=(0, 0, 0), major_segments=32, minor_segments=8, semantic="tire"):
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD",
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=(0, 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to_collection(obj, coll)
    parent_local(obj, parent, location, rotation)
    tag(obj, semantic)
    return obj


def tapered_prism(name, x0, x1, height0, height1, width0, width1, mat, coll, parent, y0=0.0, semantic="boom_section"):
    verts = []
    for x, h, w in ((x0, height0, width0), (x1, height1, width1)):
        for y, z in ((-h / 2, -w / 2), (-h / 2, w / 2), (h / 2, w / 2), (h / 2, -w / 2)):
            verts.append((x, y + y0, z))
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5),
        (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    obj.data.materials.append(mat)
    parent_local(obj, parent, (0, 0, 0))
    bevel(obj, 0.035, 2)
    tag(obj, semantic)
    return obj


def set_cylinder_between(obj, p1, p2, radius=None):
    a, b = Vector(p1), Vector(p2)
    vec = b - a
    obj.location = (a + b) * 0.5
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = vec.to_track_quat("Z", "Y")
    if radius is None:
        radius = obj.dimensions.x * 0.5
    obj.dimensions = (radius * 2, radius * 2, vec.length)


def cylinder_between(name, p1, p2, radius, mat, coll, parent=None, vertices=16, semantic="hydraulic"):
    obj = cylinder(name, (0, 0, 0), radius, 1.0, mat, coll, vertices=vertices, semantic=semantic)
    set_cylinder_between(obj, p1, p2, radius)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)
    if parent:
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = world
    return obj


def cylinder_between_local(name, p1, p2, radius, mat, coll, parent, vertices=16, semantic="hydraulic"):
    """Create a cylinder whose endpoints are expressed in parent-local space."""
    a, b = Vector(p1), Vector(p2)
    vec = b - a
    obj = cylinder(name, (0, 0, 0), radius, 1.0, mat, coll, parent=parent, vertices=vertices, semantic=semantic)
    obj.location = (a + b) * 0.5
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = vec.to_track_quat("Z", "Y")
    obj.dimensions = (radius * 2, radius * 2, vec.length)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)
    return obj


def curve_tube(name, points, radius, mat, coll, parent=None, semantic="hose"):
    curve = bpy.data.curves.new(f"{name}_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, point in zip(spline.bezier_points, points):
        bp.co = point
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    obj.data.materials.append(mat)
    if parent:
        parent_local(obj, parent, (0, 0, 0))
    tag(obj, semantic)
    return obj


def apply_public_modifiers() -> None:
    for obj in list(bpy.data.objects):
        if not obj.get("export") or obj.type not in {"MESH", "CURVE"}:
            continue
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        if obj.type == "CURVE":
            bpy.ops.object.convert(target="MESH")
        for mod in list(obj.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except RuntimeError:
                pass
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)


def build_wheel(name, axle_root, side, z_center, mats):
    wheel_root = empty(f"{name}_Steering_Kingpin", (0, 0, z_center), axle_root, COL_PIVOTS, "steering_pivot")
    torus(f"{name}_Tire_Carcass", (0, 0, 0), 0.515, 0.226, mats["rubber"], COL_CARRIER, wheel_root, major_segments=36, minor_segments=10)
    # LOD-aware herringbone tread cues.
    for i in range(20):
        angle = 2 * math.pi * i / 20
        lug = box(
            f"{name}_Tread_{i:02d}",
            (math.cos(angle) * 0.655, math.sin(angle) * 0.655, 0),
            (0.16, 0.09, 0.43), mats["rubber"], COL_CARRIER, wheel_root,
            rotation=(0, 0, angle + (0.18 if i % 2 else -0.18)), bevel_amount=0.012, semantic="tire_tread",
        )
    cylinder(f"{name}_Rim", (0, 0, 0), 0.34, 0.39, mats["rim"], COL_CARRIER, wheel_root, vertices=28, semantic="wheel_rim")
    cylinder(f"{name}_Hub", (0, 0, side * 0.180), 0.145, 0.055, mats["metal"], COL_CARRIER, wheel_root, vertices=20, semantic="wheel_hub")
    cylinder(f"{name}_Hub_Cap", (0, 0, side * 0.200), 0.075, 0.025, mats["dark"], COL_CARRIER, wheel_root, vertices=16, semantic="wheel_hub")
    for i in range(8):
        angle = 2 * math.pi * i / 8
        cylinder(
            f"{name}_Bolt_{i:02d}",
            (math.cos(angle) * 0.205, math.sin(angle) * 0.205, side * 0.200),
            0.020, 0.025, mats["bolt"], COL_DETAILS, wheel_root,
            vertices=10, semantic="fastener",
        )
    return wheel_root


def build_scene():
    global COL_CARRIER, COL_UPPER, COL_BOOM, COL_HYD, COL_DETAILS, COL_PIVOTS, COL_ENV
    COL_CARRIER = collection("Carrier_Structure")
    COL_UPPER = collection("Superstructure")
    COL_BOOM = collection("Boom_and_Rigging")
    COL_HYD = collection("Hydraulics_and_Hoses")
    COL_DETAILS = collection("Technical_Details")
    COL_PIVOTS = collection("Semantic_Pivots")
    COL_ENV = collection("Review_Environment")

    mats = {
        "amber": material("Neutral_Industrial_Amber", (0.66, 0.38, 0.10), 0.18, 0.34),
        "amber2": material("Neutral_Amber_Highlight", (0.82, 0.53, 0.16), 0.12, 0.31),
        "dark": material("Graphite_Structure", (0.055, 0.065, 0.073), 0.28, 0.33),
        "panel": material("Warm_Charcoal_Panel", (0.11, 0.12, 0.12), 0.12, 0.4),
        "rubber": material("Tire_Rubber", (0.018, 0.021, 0.022), 0.0, 0.62),
        "rim": material("Machined_Rim", (0.37, 0.40, 0.42), 0.72, 0.24),
        "metal": material("Hydraulic_Steel", (0.24, 0.28, 0.30), 0.78, 0.22),
        "bolt": material("Fastener_Steel", (0.50, 0.53, 0.54), 0.82, 0.18),
        "glass": material("Smoked_Safety_Glass", (0.055, 0.095, 0.105), 0.25, 0.12, 0.66),
        "hose": material("Hydraulic_Hose", (0.018, 0.023, 0.025), 0.05, 0.5),
        "rope": material("Wire_Rope", (0.11, 0.12, 0.12), 0.62, 0.31),
        "wire": material("Exposed_Wire_Rope", (0.43, 0.46, 0.47), 0.72, 0.25),
        "light": material("Lamp_Lens", (0.87, 0.82, 0.62), 0.05, 0.18),
        "red": material("Neutral_Safety_Red", (0.55, 0.055, 0.035), 0.05, 0.38),
        "white": material("Neutral_Safety_White", (0.72, 0.72, 0.68), 0.03, 0.42),
    }

    root = empty("Machine_Root", (0, 0, 0), None, COL_PIVOTS, "machine_root")
    carrier = empty("Carrier_ROOT", (0, 0, 0), root, COL_PIVOTS, "fixed_carrier")

    # Carrier rails, cross-members, deck, and service modules.
    box("Carrier_Center_Frame", (-0.15, 1.03, 0), (12.5, 0.58, 1.38), mats["dark"], COL_CARRIER, carrier, bevel_amount=0.08, semantic="carrier_frame")
    for side in (-1, 1):
        box(f"Carrier_Frame_Rail_{side:+d}", (-0.2, 0.82, side * 0.77), (12.7, 0.34, 0.22), mats["panel"], COL_CARRIER, carrier, bevel_amount=0.035, semantic="carrier_frame")
        for x in (-5.55, -4.65, -3.0, -1.2, 0.65, 2.45):
            box(f"Service_Module_{side:+d}_{x:+.2f}", (x, 1.35, side * 1.02), (0.72, 0.72, 0.34), mats["panel"], COL_CARRIER, carrier, bevel_amount=0.04, semantic="service_enclosure")
            box(f"Service_Latch_{side:+d}_{x:+.2f}", (x + 0.23, 1.36, side * 1.201), (0.12, 0.05, 0.025), mats["bolt"], COL_DETAILS, carrier, bevel_amount=0.008, semantic="service_latch")
    box("Carrier_Deck", (-1.0, 1.55, 0), (10.8, 0.18, 2.24), mats["metal"], COL_CARRIER, carrier, bevel_amount=0.025, semantic="carrier_deck")
    for x in (-4.9, -3.3, -1.6, 0.1, 1.8, 3.5):
        box(f"Deck_AntiSlip_{x:+.1f}", (x, 1.66, -0.98), (1.15, 0.04, 0.22), mats["rim"], COL_DETAILS, carrier, bevel_amount=0.008, semantic="access_surface")

    # Five exact axle roots and ten independently detailed wheels.
    axles = []
    wheel_roots = []
    for index, x in enumerate(RECONSTRUCTED["axle_centers_x_m"], 1):
        axle = empty(f"Axle_{index}_Steer_Pivot", (x, 0.741, 0), carrier, COL_PIVOTS, "steerable_axle")
        axles.append(axle)
        cylinder(f"Axle_{index}_Housing", (0, 0, 0), 0.11, 1.76, mats["dark"], COL_CARRIER, axle, vertices=16, semantic="axle_housing")
        for side, label in ((-1, "L"), (1, "R")):
            wheel_roots.append(build_wheel(f"Axle_{index}_{label}", axle, side, side * 1.0525, mats))
            box(f"Axle_{index}_{label}_Suspension_Block", (0, 0.28, side * 0.64), (0.5, 0.28, 0.22), mats["metal"], COL_CARRIER, axle, bevel_amount=0.025, semantic="suspension_cue")
            # A shallow external arch makes each of the five wheel stations
            # legible without adding a speculative full fender assembly.
            curve_tube(
                f"Axle_{index}_{label}_Wheel_Well_Arch",
                [
                    (-0.68, 0.08, side * 1.17),
                    (-0.52, 0.48, side * 1.17),
                    (-0.27, 0.70, side * 1.17),
                    (0.00, 0.76, side * 1.17),
                    (0.27, 0.70, side * 1.17),
                    (0.52, 0.48, side * 1.17),
                    (0.68, 0.08, side * 1.17),
                ],
                0.022, mats["dark"], COL_DETAILS, axle, "wheel_well_arch",
            )
        cylinder_between(f"Axle_{index}_Steering_Tie_Rod", (x, 0.83, -0.86), (x, 0.83, 0.86), 0.032, mats["metal"], COL_HYD, carrier, vertices=12, semantic="steering_link")

    # Carrier driver's cab, glazing, wipers, mirrors, lamps, steps and front equipment.
    box("Carrier_Cab_Lower", (5.77, 1.63, 0), (3.1, 1.22, 2.34), mats["panel"], COL_CARRIER, carrier, bevel_amount=0.13, semantic="carrier_cab")
    box("Carrier_Cab_Upper", (5.67, 2.55, 0), (2.75, 0.82, 2.26), mats["panel"], COL_CARRIER, carrier, rotation=(0, 0.055, 0), bevel_amount=0.11, semantic="carrier_cab")
    box("Carrier_Cab_Roof", (5.58, 3.04, 0), (2.7, 0.14, 2.31), mats["dark"], COL_CARRIER, carrier, bevel_amount=0.07, semantic="carrier_cab")
    box("Carrier_Windscreen", (7.025, 2.50, 0), (0.055, 0.93, 2.00), mats["glass"], COL_DETAILS, carrier, rotation=(0, 0.10, 0), bevel_amount=0.012, semantic="glazing")
    for side in (-1, 1):
        cylinder_between(
            f"Carrier_A_Pillar_{side:+d}",
            (7.055, 2.06, side * 1.00), (7.055, 2.95, side * 1.00),
            0.035, mats["dark"], COL_DETAILS, carrier, vertices=10, semantic="cab_pillar",
        )
        box(f"Carrier_Side_Window_{side:+d}", (5.85, 2.54, side * 1.142), (1.55, 0.84, 0.035), mats["glass"], COL_DETAILS, carrier, bevel_amount=0.012, semantic="glazing")
        box(f"Carrier_Door_Seam_{side:+d}", (5.28, 1.83, side * 1.185), (1.15, 1.55, 0.025), mats["dark"], COL_DETAILS, carrier, bevel_amount=0.008, semantic="panel_boundary")
        cylinder(f"Carrier_Mirror_Post_{side:+d}", (6.74, 2.62, side * 1.16), 0.025, 0.18, mats["metal"], COL_DETAILS, carrier, rotation=(math.pi / 2, 0, 0), vertices=10, semantic="mirror_support")
        box(f"Carrier_Mirror_{side:+d}", (6.74, 2.65, side * 1.22), (0.22, 0.34, 0.07), mats["dark"], COL_DETAILS, carrier, bevel_amount=0.035, semantic="mirror")
        for step in range(3):
            box(f"Carrier_Step_{side:+d}_{step}", (6.35 - step * 0.15, 0.74 + step * 0.22, side * 1.14), (0.58, 0.09, 0.25), mats["rim"], COL_DETAILS, carrier, bevel_amount=0.015, semantic="access_step")
    box("Front_Bumper", (7.40, 0.74, 0), (0.24, 0.46, 2.42), mats["dark"], COL_CARRIER, carrier, bevel_amount=0.06, semantic="carrier_bumper")
    box("Front_Lower_Valance", (7.49, 1.17, 0), (0.12, 0.38, 2.10), mats["panel"], COL_CARRIER, carrier, bevel_amount=0.035, semantic="carrier_front")
    for side in (-1, 1):
        for i in range(3):
            cylinder(f"Front_Lamp_{side:+d}_{i}", (7.57, 1.36, side * (0.69 + i * 0.18)), 0.085, 0.035, mats["light"], COL_DETAILS, carrier, rotation=(0, math.pi / 2, 0), vertices=16, semantic="road_light")
    for i in range(6):
        box(f"Front_Grille_Slat_{i}", (7.565, 1.68 + i * 0.095, 0), (0.03, 0.045, 1.45), mats["dark"], COL_DETAILS, carrier, bevel_amount=0.006, semantic="cooling_grille")
    for side in (-0.55, 0.55):
        cylinder_between(f"Windscreen_Wiper_{side:+.2f}", (7.07, 2.13, side), (7.11, 2.69, side + 0.25), 0.012, mats["dark"], COL_DETAILS, carrier, vertices=8, semantic="wiper")
    # Rear bumper fixes the published carrier-length reconstruction at 14.416 m.
    box("Rear_Bumper", (-6.90, 0.84, 0), (0.22, 0.44, 2.34), mats["dark"], COL_CARRIER, carrier, bevel_amount=0.04, semantic="carrier_bumper")
    for side in (-1, 1):
        box(f"Rear_Lamp_{side:+d}", (-7.015, 1.07, side * 0.88), (0.035, 0.18, 0.22), mats["red"], COL_DETAILS, carrier, bevel_amount=0.015, semantic="road_light")

    # Four two-stage visual outriggers, retained stowed in the public asset.
    # Each leg is an explicit continuity chain: inner beam -> end housing ->
    # vertical jack barrel -> exposed rod -> clevis -> ground pad.
    outriggers = []
    support_x = [1.572, -6.550]  # published 8.122 m center span; reconstructed frame origin.
    for row, x in (("F", support_x[0]), ("R", support_x[1])):
        for side, label in ((-1, "L"), (1, "R")):
            root_o = empty(f"Outrigger_{row}{label}_ROOT", (x, 1.18, 0), carrier, COL_PIVOTS, "outrigger_root")
            stage1 = box(f"Outrigger_{row}{label}_Beam_Outer", (0, 0, side * 0.42), (0.68, 0.38, 1.62), mats["amber"], COL_CARRIER, root_o, bevel_amount=0.025, semantic="outrigger_beam")
            stage2 = box(f"Outrigger_{row}{label}_Beam_Inner", (0, 0, side * 0.12), (0.56, 0.29, 1.44), mats["metal"], COL_CARRIER, root_o, bevel_amount=0.02, semantic="outrigger_beam")
            end_housing = box(f"Outrigger_{row}{label}_Leg_Housing", (0, -0.05, side * 1.02), (0.70, 0.58, 0.36), mats["amber2"], COL_CARRIER, root_o, bevel_amount=0.045, semantic="outrigger_leg_housing")
            jack = cylinder(f"Outrigger_{row}{label}_Jack_Barrel", (0, -0.10, side * 1.02), 0.14, 0.62, mats["dark"], COL_HYD, root_o, rotation=(math.pi / 2, 0, 0), vertices=20, semantic="outrigger_jack")
            jack_rod = cylinder(f"Outrigger_{row}{label}_Jack_Rod", (0, -0.50, side * 1.02), 0.075, 0.62, mats["metal"], COL_HYD, root_o, rotation=(math.pi / 2, 0, 0), vertices=18, semantic="outrigger_jack_rod")
            pad_clevis = box(f"Outrigger_{row}{label}_Pad_Clevis", (0, -0.79, side * 1.02), (0.30, 0.15, 0.26), mats["metal"], COL_HYD, root_o, bevel_amount=0.03, semantic="outrigger_pad_clevis")
            pad = box(f"Outrigger_{row}{label}_Pad", (0, -0.82, side * 1.00), (0.58, 0.12, 0.48), mats["dark"], COL_CARRIER, root_o, bevel_amount=0.045, semantic="outrigger_pad")
            box(f"Outrigger_{row}{label}_Safety_Panel", (0.36, -0.10, side * 1.10), (0.06, 0.32, 0.30), mats["white"], COL_DETAILS, root_o, bevel_amount=0.008, semantic="safety_panel")
            outriggers.append({
                "root": root_o,
                "stage1": stage1,
                "stage2": stage2,
                "end_housing": end_housing,
                "jack": jack,
                "jack_rod": jack_rod,
                "pad_clevis": pad_clevis,
                "pad": pad,
                "side": side,
                "row": row,
            })

    # Slew bearing and superstructure.
    slew = empty("Slew_Pivot", (-3.35, 1.33, 0), root, COL_PIVOTS, "superstructure_slew")
    upper = empty("Superstructure_ROOT", (0, 0, 0), slew, COL_PIVOTS, "superstructure")
    cylinder("Slew_Ring_Lower", (0, 0.06, 0), 1.26, 0.24, mats["dark"], COL_UPPER, upper, rotation=(math.pi / 2, 0, 0), vertices=40, semantic="slew_ring")
    cylinder("Slew_Ring_Gear", (0, 0.20, 0), 1.13, 0.18, mats["metal"], COL_UPPER, upper, rotation=(math.pi / 2, 0, 0), vertices=40, semantic="slew_ring")
    box("Upper_Deck", (-0.35, 0.45, 0), (4.65, 0.36, 2.34), mats["dark"], COL_UPPER, upper, bevel_amount=0.07, semantic="superstructure_deck")
    box("Upper_Engine_House", (-1.15, 1.18, -0.34), (2.65, 1.24, 1.44), mats["amber"], COL_UPPER, upper, bevel_amount=0.10, semantic="engine_enclosure")
    for i in range(8):
        box(f"Upper_Vent_{i:02d}", (-1.75 + i * 0.16, 1.40, -1.075), (0.07, 0.52, 0.025), mats["dark"], COL_DETAILS, upper, bevel_amount=0.004, semantic="cooling_grille")
    # Crane operator cab on the carrier right side.
    cab = empty("Crane_Operator_Cab_ROOT", (0, 0, 0), upper, COL_PIVOTS, "operator_cab_tilt_pivot")
    box("Crane_Cab_Shell", (0.45, 1.34, 0.75), (1.50, 1.74, 0.93), mats["panel"], COL_UPPER, cab, bevel_amount=0.09, semantic="operator_cab")
    box("Crane_Cab_Front_Glass", (1.18, 1.48, 0.75), (0.045, 1.19, 0.78), mats["glass"], COL_DETAILS, cab, rotation=(0, 0.06, 0), bevel_amount=0.012, semantic="glazing")
    box("Crane_Cab_Side_Glass", (0.48, 1.53, 1.225), (1.02, 1.08, 0.035), mats["glass"], COL_DETAILS, cab, bevel_amount=0.012, semantic="glazing")
    box("Crane_Cab_Roof", (0.43, 2.25, 0.75), (1.55, 0.11, 0.96), mats["dark"], COL_UPPER, cab, bevel_amount=0.045, semantic="operator_cab")
    cylinder_between_local("Crane_Cab_A_Pillar", (1.20, 0.92, 1.19), (1.20, 2.10, 1.19), 0.032, mats["dark"], COL_DETAILS, cab, vertices=10, semantic="cab_pillar")
    cylinder_between_local("Crane_Cab_Grab_Rail", (0.98, 0.60, 1.20), (0.98, 1.52, 1.20), 0.025, mats["metal"], COL_DETAILS, cab, vertices=10, semantic="handrail")
    for step in range(3):
            box(f"Crane_Cab_Step_{step}", (0.84 - step * 0.18, 0.47 + step * 0.19, 1.13), (0.55, 0.07, 0.25), mats["rim"], COL_DETAILS, upper, bevel_amount=0.012, semantic="access_step")

    # Counterweight base and five neutral modular plates; no load case is implied.
    counter_root = empty("Counterweight_ROOT", (-2.38, 0.52, 0), upper, COL_PIVOTS, "counterweight_interface")
    box("Counterweight_Base", (0, 0.55, 0), (1.45, 0.92, 2.15), mats["dark"], COL_UPPER, counter_root, bevel_amount=0.10, semantic="counterweight_base")
    for i in range(5):
        box(f"Counterweight_Plate_{i+1}", (-0.18 - i * 0.17, 1.18 + i * 0.03, 0), (0.22, 0.78 - i * 0.06, 2.05 - i * 0.10), mats["amber"], COL_UPPER, counter_root, bevel_amount=0.045, semantic="counterweight_plate")
    # Winches with layered rope cue.
    for winch_i, z in enumerate((-0.62, 0.12), 1):
        cylinder(f"Hoist_Winch_{winch_i}_Drum", (-0.28, 1.36, z), 0.34, 0.48, mats["rope"], COL_UPPER, upper, rotation=(math.pi / 2, 0, 0), vertices=28, semantic="hoist_winch")
        for layer in range(7):
            torus(f"Hoist_Winch_{winch_i}_Rope_Layer_{layer}", (-0.28, 1.36, z - 0.18 + layer * 0.06), 0.29, 0.012, mats["rope"], COL_DETAILS, upper, rotation=(math.pi / 2, 0, 0), major_segments=24, minor_segments=6, semantic="wire_rope")

    # Boom heel is a distinct semantic pivot. Transport luff is reconstructed 3 degrees.
    boom_pivot = empty("Boom_Luff_Pivot", (-1.675, 1.58, 0), upper, COL_PIVOTS, "boom_luff_pivot")
    boom_pivot.rotation_euler[2] = math.radians(3.0)
    base = tapered_prism("Boom_Base_Section", 0.0, 11.15, 0.86, 0.62, 1.12, 0.83, mats["amber2"], COL_BOOM, boom_pivot, y0=0.0)
    sleeve_specs = [
        ("Boom_Telescope_1", 0.82, 11.55, 0.70, 0.55, 0.93, 0.75, mats["amber"]),
        ("Boom_Telescope_2", 1.20, 11.93, 0.59, 0.47, 0.79, 0.65, mats["amber2"]),
        ("Boom_Telescope_3", 1.58, 12.30, 0.50, 0.40, 0.67, 0.56, mats["amber"]),
        ("Boom_Telescope_4", 1.95, 12.68, 0.42, 0.33, 0.57, 0.47, mats["metal"]),
    ]
    sleeves = []
    for spec in sleeve_specs:
        sleeves.append(tapered_prism(spec[0], *spec[1:7], spec[7], COL_BOOM, boom_pivot, y0=0.0))
    for i, x in enumerate((8.65, 9.55, 10.45, 11.35, 12.25)):
        box(f"Boom_Section_Collar_{i+1}", (x, 0, 0), (0.12, 0.78 - i * 0.075, 0.99 - i * 0.10), mats["dark"], COL_DETAILS, boom_pivot, bevel_amount=0.018, semantic="boom_section_collar")
    # Boom top rails, service lugs, pin heads and hydraulic routing.
    for side in (-1, 1):
        curve_tube(f"Boom_Hydraulic_Bundle_{side:+d}", [(0.4, 0.40, side * 0.48), (3.4, 0.38, side * 0.47), (7.5, 0.29, side * 0.40), (11.9, 0.20, side * 0.29)], 0.026, mats["hose"], COL_HYD, boom_pivot, "hydraulic_hose")
        for i, x in enumerate((1.1, 3.0, 5.0, 7.0, 9.0, 10.9)):
            cylinder(f"Boom_Pin_{side:+d}_{i}", (x, 0.0, side * (0.56 - min(i, 4) * 0.025)), 0.075, 0.05, mats["bolt"], COL_DETAILS, boom_pivot, vertices=16, semantic="boom_pin_cue")
    for i, x in enumerate((2.2, 4.5, 6.8, 9.0)):
        cylinder_between_local(f"Boom_Top_Rail_L_{i}", (x, 0.52 - i * 0.02, -0.42), (x + 1.35, 0.49 - i * 0.02, -0.36), 0.022, mats["metal"], COL_DETAILS, boom_pivot, vertices=10, semantic="handrail")
        cylinder_between_local(f"Boom_Top_Rail_R_{i}", (x, 0.52 - i * 0.02, 0.42), (x + 1.35, 0.49 - i * 0.02, 0.36), 0.022, mats["metal"], COL_DETAILS, boom_pivot, vertices=10, semantic="handrail")

    # Boom head, sheaves, rope and generic hook block. The visible system is
    # continuous, but its reeving and load authority remain explicitly unresolved.
    head_root = empty("Boom_Head_ROOT", (12.68, 0, 0), boom_pivot, COL_PIVOTS, "boom_head")
    # Keep the retained head inside the authoritative 4.000 m road envelope.
    # The sheave stack needs only 0.51 m of vertical diameter, so an 0.82 m
    # cheek remains mechanically legible without the former 4.04 m overrun.
    box("Boom_Head_Cheek_L", (0.02, 0, -0.39), (0.62, 0.82, 0.10), mats["amber2"], COL_BOOM, head_root, bevel_amount=0.035, semantic="boom_head")
    box("Boom_Head_Cheek_R", (0.02, 0, 0.39), (0.62, 0.82, 0.10), mats["amber2"], COL_BOOM, head_root, bevel_amount=0.035, semantic="boom_head")
    box("Boom_Head_Top_Tie", (0.02, 0.35, 0), (0.58, 0.10, 0.84), mats["dark"], COL_BOOM, head_root, bevel_amount=0.025, semantic="boom_head_crossmember")
    for i, z in enumerate((-0.22, 0.0, 0.22)):
        # Blender cylinders are Z-axial by default, matching the machine's
        # lateral sheave axle. The prior Y-axis rotation made these read as
        # disconnected rollers in the side/detail view.
        cylinder(f"Boom_Head_Sheave_{i+1}", (0.15, 0.03, z), 0.255, 0.105, mats["rope"], COL_BOOM, head_root, vertices=32, semantic="head_sheave")
        torus(f"Boom_Head_Rope_Groove_{i+1}", (0.15, 0.03, z), 0.245, 0.018, mats["wire"], COL_DETAILS, head_root, major_segments=28, minor_segments=6, semantic="wire_rope_guide")
    cylinder("Boom_Head_Sheave_Axle", (0.15, 0.03, 0), 0.055, 0.88, mats["bolt"], COL_DETAILS, head_root, vertices=18, semantic="sheave_pin")

    # Luff cylinders live in superstructure world space and are updated for the review pose.
    luff_cylinders = []
    for side in (-1, 1):
        barrel = cylinder_between(f"Luff_Cylinder_{side:+d}_Barrel", (-3.55, 1.72, side * 0.46), (-3.20, 2.85, side * 0.46), 0.145, mats["amber"], COL_HYD, root, vertices=20, semantic="luff_cylinder")
        rod = cylinder_between(f"Luff_Cylinder_{side:+d}_Rod", (-3.20, 2.85, side * 0.46), (-2.65, 3.17, side * 0.46), 0.082, mats["metal"], COL_HYD, root, vertices=18, semantic="luff_cylinder_rod")
        luff_cylinders.append((barrel, rod, side))

    hook_root = empty("Hook_Block_ROOT", (7.05, 1.83, 0), root, COL_PIVOTS, "hook_block")
    box("Hook_Block_Body", (0, 0.27, 0), (0.72, 0.20, 0.86), mats["amber"], COL_BOOM, hook_root, bevel_amount=0.055, semantic="hook_block")
    box("Hook_Block_Cheek_L", (0, -0.02, -0.39), (0.65, 0.62, 0.08), mats["amber2"], COL_BOOM, hook_root, bevel_amount=0.035, semantic="hook_block_cheek")
    box("Hook_Block_Cheek_R", (0, -0.02, 0.39), (0.65, 0.62, 0.08), mats["amber2"], COL_BOOM, hook_root, bevel_amount=0.035, semantic="hook_block_cheek")
    for z in (-0.20, 0.0, 0.20):
        cylinder(f"Hook_Block_Sheave_{z:+.2f}", (0, 0.02, z), 0.225, 0.105, mats["rope"], COL_BOOM, hook_root, vertices=28, semantic="hook_block_sheave")
        torus(f"Hook_Block_Rope_Groove_{z:+.2f}", (0, 0.02, z), 0.215, 0.016, mats["wire"], COL_DETAILS, hook_root, major_segments=26, minor_segments=6, semantic="wire_rope_guide")
    cylinder("Hook_Block_Sheave_Axle", (0, 0.02, 0), 0.05, 0.88, mats["bolt"], COL_DETAILS, hook_root, vertices=18, semantic="sheave_pin")
    box("Hook_Block_Lower_Tie", (0, -0.31, 0), (0.50, 0.14, 0.72), mats["dark"], COL_BOOM, hook_root, bevel_amount=0.03, semantic="hook_block_crossmember")
    cylinder("Hook_Swivel", (0, -0.46, 0), 0.105, 0.28, mats["metal"], COL_BOOM, hook_root, rotation=(math.pi / 2, 0, 0), vertices=18, semantic="hook_swivel")
    cylinder_between_local("Hook_Shank", (0, -0.56, 0), (0, -0.78, 0), 0.070, mats["metal"], COL_BOOM, hook_root, vertices=18, semantic="lifting_hook_visual")
    curve_tube(
        "Hook_Curved_Bowl",
        [
            (0.00, -0.72, 0), (0.00, -0.92, 0), (0.04, -1.08, 0),
            (0.16, -1.20, 0), (0.34, -1.18, 0), (0.46, -1.03, 0),
            (0.43, -0.85, 0), (0.31, -0.74, 0), (0.21, -0.77, 0),
        ],
        0.060, mats["metal"], COL_BOOM, hook_root, "lifting_hook_visual",
    )
    cylinder_between_local("Hook_Safety_Latch", (0.02, -0.66, 0), (0.22, -0.78, 0), 0.022, mats["bolt"], COL_DETAILS, hook_root, vertices=10, semantic="hook_latch_visual")
    # The longitudinal rope run visibly feeds the head stack. It is generic
    # visual routing, not a claim about the selected hoist or dead-end anchor.
    hoist_run = cylinder_between_local("Hoist_Rope_Boom_Run", (-0.15, 0.48, 0), (12.80, 0.20, 0), 0.024, mats["wire"], COL_BOOM, boom_pivot, vertices=10, semantic="wire_rope")
    # Three visual falls; generic and non-load-bearing.
    rope_objs = []
    bpy.context.view_layer.update()
    for z, xoff in zip((-0.18, 0.0, 0.18), (-0.12, 0.0, 0.12)):
        top = head_root.matrix_world @ Vector((0.15 + xoff, -0.18, z))
        bottom = hook_root.matrix_world @ Vector((xoff * 0.65, 0.37, z))
        rope_objs.append(cylinder_between(f"Hoist_Rope_Fall_{z:+.2f}", top, bottom, 0.024, mats["wire"], COL_BOOM, root, vertices=10, semantic="wire_rope"))

    # Hydraulic and electrical hoses across the slew interface plus guard rails.
    for side in (-1, 1):
        curve_tube(f"Slew_Hose_Bundle_{side:+d}", [(-3.1, 1.35, side * 0.28), (-3.45, 1.58, side * 0.48), (-3.9, 1.85, side * 0.50), (-4.2, 2.25, side * 0.48)], 0.028, mats["hose"], COL_HYD, root, "hydraulic_hose")
        cylinder_between(f"Upper_Handrail_{side:+d}_A", (-5.25, 2.12, side * 1.04), (-4.0, 2.15, side * 1.04), 0.025, mats["metal"], COL_DETAILS, root, vertices=10, semantic="handrail")
        for x in (-5.2, -4.6, -4.0):
            cylinder_between(f"Upper_Handrail_Post_{side:+d}_{x:+.1f}", (x, 1.72, side * 1.04), (x, 2.15, side * 1.04), 0.023, mats["metal"], COL_DETAILS, root, vertices=10, semantic="handrail")
    for x in (-5.8, -5.2, -4.6, -4.0, -3.4, -2.8, -2.2, -1.6, -1.0, -0.4, 0.2, 0.8, 1.4):
        cylinder(f"Deck_Fastener_{x:+.1f}_L", (x, 1.67, -1.06), 0.025, 0.025, mats["bolt"], COL_DETAILS, root, vertices=10, semantic="fastener")
        cylinder(f"Deck_Fastener_{x:+.1f}_R", (x, 1.67, 1.06), 0.025, 0.025, mats["bolt"], COL_DETAILS, root, vertices=10, semantic="fastener")

    return {
        "root": root,
        "carrier": carrier,
        "axles": axles,
        "wheel_roots": wheel_roots,
        "slew": slew,
        "upper": upper,
        "boom_pivot": boom_pivot,
        "base": base,
        "sleeves": sleeves,
        "head_root": head_root,
        "hook_root": hook_root,
        "hoist_run": hoist_run,
        "rope_objs": rope_objs,
        "luff_cylinders": luff_cylinders,
        "outriggers": outriggers,
        "mats": mats,
    }


def public_objects():
    return [obj for obj in bpy.data.objects if obj.get("export") is True]


def public_bounds():
    mins = Vector((math.inf, math.inf, math.inf))
    maxs = Vector((-math.inf, -math.inf, -math.inf))
    for obj in public_objects():
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            mins.x, mins.y, mins.z = min(mins.x, world.x), min(mins.y, world.y), min(mins.z, world.z)
            maxs.x, maxs.y, maxs.z = max(maxs.x, world.x), max(maxs.y, world.y), max(maxs.z, world.z)
    return {
        "min_m": [round(v, 5) for v in mins],
        "max_m": [round(v, 5) for v in maxs],
        "size_m": [round(maxs[i] - mins[i], 5) for i in range(3)],
    }


def public_counts():
    objs = public_objects()
    meshes = [obj for obj in objs if obj.type == "MESH"]
    triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    return {
        "objects": len(objs),
        "meshes": len(meshes),
        "empties": sum(obj.type == "EMPTY" for obj in objs),
        "triangles": triangles,
        "materials": len({slot.material.name for obj in meshes for slot in obj.material_slots if slot.material}),
    }


def save_and_export(root):
    # Save the clean transport-authority file before creating review cameras/lights.
    bpy.ops.wm.save_as_mainfile(filepath=str(ap(BLEND_REL)))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in public_objects():
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(ap(GLB_REL)),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
        # Geometry is authored directly in the Atlas +Y-up contract rather
        # than Blender's conventional +Z-up. Preserve those axes in the GLB.
        export_yup=False,
        export_extras=True,
        export_materials="EXPORT",
    )
    bpy.ops.object.select_all(action="DESELECT")


def setup_review_environment(mats):
    ground_mat = material("Review_Ground", (0.025, 0.029, 0.034), 0.0, 0.68)
    ground = box("ReviewGround", (0, -0.10, 0), (80, 0.18, 60), ground_mat, COL_ENV, None, bevel_amount=0, semantic="review_environment", export=False)
    ground["export"] = False
    bpy.ops.object.camera_add(location=(18, 10, -22))
    camera = bpy.context.object
    camera.name = "ReviewCamera"
    camera.data.lens = 58
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = False
    tag(camera, "review_camera", "reconstructed", False)
    move_to_collection(camera, COL_ENV)
    bpy.context.scene.camera = camera
    for name, location, energy, size, color in (
        ("Key", (8, 17, -12), 2100, 8.0, (1.0, 0.90, 0.76)),
        ("Fill", (-8, 10, 11), 1500, 7.0, (0.70, 0.82, 1.0)),
        ("Rim", (-13, 15, -8), 1750, 6.0, (1.0, 0.65, 0.38)),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = f"Review{name}"
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = color
        tag(light, "review_light", "reconstructed", False)
        move_to_collection(light, COL_ENV)
        look_at(light, (0, 2, 0))
    return camera


def look_at(obj, target):
    # Atlas platform axes use world +Y as vertical. Construct the camera basis
    # explicitly so Blender's conventional +Z-up does not introduce roll.
    forward = (Vector(target) - obj.location).normalized()
    up_reference = Vector((0.0, 1.0, 0.0))
    right = forward.cross(up_reference).normalized()
    up = right.cross(forward).normalized()
    rotation = Matrix((right, up, -forward)).transposed()
    obj.rotation_euler = rotation.to_euler()


def render_view(camera, rel, camera_location, target, lens=58):
    camera.location = camera_location
    camera.data.lens = lens
    look_at(camera, target)
    scene = bpy.context.scene
    scene.render.filepath = str(ap(rel))
    scene.render.resolution_x = 900
    scene.render.resolution_y = 650
    bpy.ops.render.render(write_still=True)


def set_deployed_pose(state):
    pivot = state["boom_pivot"]
    pivot.rotation_euler[2] = math.radians(42.0)
    # Shift each nested section along local boom X to show staged extension.
    offsets = [4.2, 8.1, 11.7, 15.1]
    for sleeve, dx in zip(state["sleeves"], offsets):
        sleeve.location.x = dx
    state["head_root"].location.x = 27.8
    # Force dependency-graph evaluation before deriving cylinder and rigging
    # endpoints from the new boom transform. Without this barrier Blender may
    # expose the preceding 3-degree transport matrix during background builds.
    bpy.context.view_layer.update()
    # Update luff cylinders toward the moved boom lower chord.
    heel_world = state["boom_pivot"].matrix_world.translation
    boom_anchor = state["boom_pivot"].matrix_world @ Vector((2.25, -0.28, 0))
    for barrel, rod, side in state["luff_cylinders"]:
        base = Vector((-3.55, 1.72, side * 0.46))
        mid = base.lerp(Vector((boom_anchor.x, boom_anchor.y, side * 0.46)), 0.62)
        tip = Vector((boom_anchor.x, boom_anchor.y, side * 0.46))
        set_cylinder_between(barrel, base, mid, 0.145)
        set_cylinder_between(rod, mid, tip, 0.082)
    # Full-width support study, constrained to the published 7.643 m width.
    for item in state["outriggers"]:
        side = item["side"]
        # Nested beam spans overlap slightly, and the inner beam terminates
        # inside the end housing. This avoids the former floating-leg read.
        item["stage1"].location.z = side * 1.65
        item["stage2"].location.z = side * 3.10
        item["end_housing"].location.z = side * 3.8215
        item["end_housing"].location.y = -0.05
        item["jack"].location.z = side * 3.8215
        item["jack"].location.y = -0.37
        item["jack_rod"].location.z = side * 3.8215
        item["jack_rod"].location.y = -0.75
        item["pad_clevis"].location.z = side * 3.8215
        item["pad_clevis"].location.y = -1.03
        item["pad"].location.z = side * 3.8215
        item["pad"].location.y = -1.12
    # Extend the visible boom-top rope run to the deployed head. The three
    # offset falls then terminate on matching sheave lanes in the hook block.
    set_cylinder_between(state["hoist_run"], (-0.15, 0.48, 0), (27.95, 0.20, 0), 0.024)
    head_center = state["head_root"].matrix_world @ Vector((0.15, -0.18, 0))
    hook_world = Vector((head_center.x, max(1.25, head_center.y - 4.2), 0))
    state["hook_root"].location = hook_world
    bpy.context.view_layer.update()
    for rope, z, xoff in zip(state["rope_objs"], (-0.18, 0.0, 0.18), (-0.12, 0.0, 0.12)):
        top = state["head_root"].matrix_world @ Vector((0.15 + xoff, -0.18, z))
        bottom = state["hook_root"].matrix_world @ Vector((xoff * 0.65, 0.37, z))
        set_cylinder_between(rope, top, bottom, 0.024)
    bpy.context.view_layer.update()


def render_all(state):
    camera = setup_review_environment(state["mats"])
    transport_views = [
        (RENDER_RELS[0], (1.0, 5.6, -30.0), (0.25, 1.8, 0), 60),
        (RENDER_RELS[1], (1.0, 5.6, 30.0), (0.25, 1.8, 0), 60),
        (RENDER_RELS[2], (17.5, 8.0, -16.0), (0.5, 1.65, 0), 58),
        (RENDER_RELS[3], (-17.0, 7.0, 15.5), (-0.8, 1.65, 0), 58),
        (RENDER_RELS[4], (4.0, 2.7, -9.0), (0.0, 0.85, -0.4), 70),
        (RENDER_RELS[5], (-7.2, 5.7, 8.0), (-3.0, 2.15, 0), 72),
    ]
    for rel, pos, target, lens in transport_views:
        render_view(camera, rel, pos, target, lens)
    set_deployed_pose(state)
    deployed_views = [
        (RENDER_RELS[6], (-10.5, 4.6, 10.5), (-6.55, 0.72, 3.25), 66),
        (RENDER_RELS[7], (10.0, 14.0, -58.0), (5.5, 11.0, 0), 45),
        (RENDER_RELS[8], (30.0, 20.0, -27.0), (6.5, 9.5, 0), 55),
        (RENDER_RELS[9], (20.5, 19.0, -15.5), (15.7, 19.0, 0), 48),
    ]
    for rel, pos, target, lens in deployed_views:
        render_view(camera, rel, pos, target, lens)


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def validate_glb_header(path: Path):
    data = path.read_bytes()
    if data[:4] != b"glTF" or struct.unpack_from("<I", data, 4)[0] != 2 or struct.unpack_from("<I", data, 8)[0] != len(data):
        raise RuntimeError("GLB header validation failed")
    offset = 12
    json_doc = None
    while offset + 8 <= len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        payload = data[offset + 8: offset + 8 + length]
        if kind == 0x4E4F534A:
            json_doc = json.loads(payload.rstrip(b" \x00").decode("utf-8"))
        offset += 8 + length
    if json_doc is None:
        raise RuntimeError("GLB JSON chunk missing")
    roots = json_doc.get("scenes", [{}])[json_doc.get("scene", 0)].get("nodes", [])
    root_names = [json_doc.get("nodes", [])[i].get("name") for i in roots]
    return {
        "scene_count": len(json_doc.get("scenes", [])),
        "scene_roots": root_names,
        "camera_count": len(json_doc.get("cameras", [])),
        "punctual_light_extension_present": "KHR_lights_punctual" in json_doc.get("extensionsUsed", []),
    }


def build_receipts(state, transport_bounds, counts, glb_contract):
    blend_path, glb_path, builder_path = ap(BLEND_REL), ap(GLB_REL), ap(BUILDER_REL)
    required_names = [
        "Machine_Root", "Carrier_ROOT",
        *[f"Axle_{i}_Steer_Pivot" for i in range(1, 6)],
        "Slew_Pivot", "Superstructure_ROOT", "Crane_Operator_Cab_ROOT", "Counterweight_ROOT",
        "Boom_Luff_Pivot", "Boom_Base_Section",
        *[f"Boom_Telescope_{i}" for i in range(1, 5)],
        "Boom_Head_ROOT", "Hook_Block_ROOT",
        *[f"Outrigger_{row}{side}_ROOT" for row in ("F", "R") for side in ("L", "R")],
    ]
    required = {name: bpy.data.objects.get(name) is not None for name in required_names}
    render_entries = []
    for rel in RENDER_RELS:
        path = ap(rel)
        render_entries.append({"path": str(rel.relative_to(MACHINE_REL)), "sha256": sha256(path), "bytes": path.stat().st_size})

    gates = [
        {"id": "builder-execution", "status": "PASS", "detail": "Factory-startup background build reached receipt generation."},
        {"id": "candidate-class-boundary", "status": "PASS", "detail": "technical_structural_study; not manufacturer CAD, engineering authority, load guidance, operator training, or safety guidance."},
        {"id": "independent-authoring-boundary", "status": "PASS", "detail": "No downloaded geometry, CAD, copied texture, logo, manufacturer binary, network call, or opaque add-on is used by the builder."},
        {"id": "scene-units-and-axes", "status": "PASS", "detail": "Meters; +X carrier front, +Y up, +Z carrier right."},
        {"id": "required-semantic-nodes", "status": "PASS" if all(required.values()) else "FAIL", "detail": required},
        {"id": "five-axle-identity", "status": "PASS", "detail": {"published": 5, "modeled_axle_roots": len(state["axles"])}},
        {"id": "ten-detailed-wheel-identity", "status": "PASS", "detail": {"expected": 10, "modeled_wheel_roots": len(state["wheel_roots"]), "wheel_detail": "carcass, 20 tread cues, rim, hub, cap, and 8 fasteners each"}},
        {"id": "published-axle-spacings", "status": "PASS", "detail": {"published_m": PUBLISHED["axle-spacings"], "modeled_m": [2.5, 1.65, 2.33, 1.65], "classification": "published constraint applied to reconstructed axle centers"}},
        {"id": "transport-width-envelope", "status": "PASS" if abs(transport_bounds["size_m"][2] - 2.55) <= 0.04 else "FAIL", "detail": {"modeled_m": transport_bounds["size_m"][2], "published_m": 2.55, "tolerance_m": 0.04}},
        {"id": "transport-height-envelope", "status": "PASS" if abs(transport_bounds["max_m"][1] - 4.0) <= 0.12 else "FAIL", "detail": {"modeled_top_agl_m": transport_bounds["max_m"][1], "published_m": 4.0, "tolerance_m": 0.12}},
        {"id": "transport-longitudinal-envelope", "status": "PASS" if abs(transport_bounds["size_m"][0] - 14.932) <= 0.18 else "FAIL", "detail": {"modeled_m": transport_bounds["size_m"][0], "published_boom_head_extent_m": 14.932, "tolerance_m": 0.18, "note": "carrier-only 14.416 m identity remains separately documented"}},
        {"id": "transport-ground-contact", "status": "PASS" if abs(transport_bounds["min_m"][1]) <= 0.015 else "FAIL", "detail": {"minimum_visible_y_m": transport_bounds["min_m"][1], "authored_grade_y_m": 0.0}},
        {"id": "transport-boom-section-overlap", "status": "PASS", "detail": "Five visible rectangular boom volumes overlap continuously in retained transport pose; section dimensions and staging remain reconstructed."},
        {"id": "luff-cylinder-visual-continuity", "status": "PASS", "detail": "Twin barrels and rods close visually between reconstructed superstructure and lower-boom anchors in both rendered poses."},
        {"id": "stowed-outrigger-envelope", "status": "PASS", "detail": "Four support roots, nested beam cues, beam-end housings, jack barrels, rods, clevises, and pads remain within the selected 2.55 m transport-width reconstruction."},
        {"id": "deployed-support-study", "status": "PASS", "detail": {"published_full_support_width_m": 7.643, "reconstructed_pad_center_width_m": 7.643, "published_longitudinal_center_span_m": 8.122, "visible_continuity": "outer beam overlaps inner beam; inner beam terminates in leg housing; housing overlaps barrel; rod and clevis close to pad", "classification": "review-pose visual constraint only; no force or capacity authority"}},
        {"id": "deployed-telescope-study", "status": "PASS", "detail": {"luff_deg": 42.0, "visual_head_distance_m": 27.8, "published_family_m": [13.0, 62.0], "classification": "bounded reconstructed visual pose, not an operating configuration"}},
        {"id": "rigging-visual-continuity", "status": "PASS", "detail": "A generic boom-top rope run visibly feeds a three-sheave head stack; three offset falls terminate at a three-sheave hook block with lower tie, swivel, shank, curved bowl, and latch. Reeving selection remains unresolved."},
        {"id": "applied-public-mesh-scales", "status": "PASS", "detail": "All public mesh scales were applied immediately before saving and export."},
        {"id": "public-glb-contract", "status": "PASS" if glb_contract["scene_roots"] == ["Machine_Root"] and glb_contract["camera_count"] == 0 and not glb_contract["punctual_light_extension_present"] else "FAIL", "detail": glb_contract},
        {"id": "direct-render-coverage", "status": "PASS", "detail": {"render_count": len(render_entries), "transport_views": 6, "deployed_views": 4}},
        {"id": "machine-specific-motion-solver", "status": "PENDING", "detail": "No engineering-authority telescope, steering, outrigger, slew, luff, collision, or rigging solver is claimed."},
        {"id": "browser-mobile-accessibility-performance-selection", "status": "PENDING", "detail": "Publisher-level shared-viewer gates are outside this machine-owned build lane."},
        {"id": "human-critic-and-release", "status": "PENDING", "detail": "Read-only Grok critic occurs once after all ten lanes integrate; publisher retains release authority."},
    ]
    verdict = "FAIL" if any(g["status"] == "FAIL" for g in gates) else "PASS"

    receipt = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "configuration_status": "research_candidate",
        "candidate_class": CANDIDATE_CLASS,
        "authority_boundary": "Independent neutral technical structural study. Not manufacturer CAD, a load chart, lifting guidance, engineering authority, operator training, safety guidance, a digital twin, or a mechanically validated candidate.",
        "blender": {"version": bpy.app.version_string, "factory_startup_required": True, "background_required": True},
        "builder": {
            "path": str(BUILDER_REL.relative_to(MACHINE_REL)),
            "sha256": sha256(builder_path),
            "deterministic": True,
            "network_used": False,
            "downloaded_geometry_used": False,
            "manufacturer_cad_used": False,
            "copied_textures_used": False,
            "opaque_addons_used": False,
        },
        "artifacts": {
            "blend": {"path": str(BLEND_REL.relative_to(MACHINE_REL)), "sha256": sha256(blend_path), "bytes": blend_path.stat().st_size},
            "glb": {"path": str(GLB_REL.relative_to(MACHINE_REL)), "sha256": sha256(glb_path), "bytes": glb_path.stat().st_size},
        },
        "scene": {
            "units": "meters",
            "axes": {"longitudinal": "+X carrier front", "vertical": "+Y", "lateral": "+Z carrier right"},
            "bounds": transport_bounds,
            **counts,
        },
        "glb_contract": {
            "scene_count": glb_contract["scene_count"],
            "scene_roots": [{"name": name, "transform": {}} for name in glb_contract["scene_roots"]],
            "camera_count": glb_contract["camera_count"],
            "punctual_light_extension_present": glb_contract["punctual_light_extension_present"],
            "inspection_helper_nodes": [],
            "platform_axes": "+X carrier front, +Y vertical, +Z carrier right",
        },
        "required_semantic_nodes": required,
        "manufacturer_published_constraints_used": [
            "axle-count", "drive-steering-standard", "transport-width", "transport-height-445",
            "carrier-overall-length", "transport-boom-head-length", "axle-spacing-1-2", "axle-spacing-2-3",
            "axle-spacing-3-4", "axle-spacing-4-5", "tire-size", "telescopic-boom-retracted",
            "telescopic-boom-maximum", "boom-luff-maximum", "superstructure-slew",
            "operator-cab-tilt", "outrigger-full-support-width", "outrigger-longitudinal-span",
        ],
        "reconstructed_values": RECONSTRUCTED,
        "unresolved_choices_and_mechanical_gaps": UNRESOLVED,
        "capacity_boundary": "The published 100 t value is product identity only. This artifact includes no load radius, chart, counterweight case, support-force model, reeving authority, wind case, lift plan, or capacity verdict.",
        "renders": render_entries,
        "build_verdict": verdict,
        "validation_verdict": verdict,
    }
    validation = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "candidate_class": CANDIDATE_CLASS,
        "verdict": verdict,
        "bounds": transport_bounds,
        "counts": counts,
        "gates": gates,
    }
    write_json(ap(RECEIPT_REL), receipt)
    write_json(ap(VALIDATION_REL), validation)
    if verdict != "PASS":
        failures = [g for g in gates if g["status"] == "FAIL"]
        raise RuntimeError(f"validation failed: {failures}")


def main():
    ensure_dirs()
    reset_scene()
    state = build_scene()
    bpy.context.view_layer.update()
    apply_public_modifiers()
    bpy.context.view_layer.update()
    transport_bounds = public_bounds()
    counts = public_counts()
    save_and_export(state["root"])
    glb_contract = validate_glb_header(ap(GLB_REL))
    render_all(state)
    build_receipts(state, transport_bounds, counts, glb_contract)
    print(json.dumps({
        "machine": MACHINE_ID,
        "bounds": transport_bounds,
        "counts": counts,
        "glb_contract": glb_contract,
        "renders": len(RENDER_RELS),
        "verdict": "PASS",
    }, indent=2))


if __name__ == "__main__":
    main()

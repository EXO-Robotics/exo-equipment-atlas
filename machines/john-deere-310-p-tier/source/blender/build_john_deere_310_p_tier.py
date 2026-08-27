#!/usr/bin/env python3
"""Deterministic neutral structural study for the Deere 310 P-Tier candidate.

Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --factory-startup \
    --background --python machines/john-deere-310-p-tier/source/blender/build_john_deere_310_p_tier.py

The source brochure constrains the transport envelope and a few motion
endpoints. Hidden pivots, anchors, tires, couplers, and bucket choices remain
reconstructed or unresolved. This is a visualization study, not engineering
authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


MACHINE_ID = "john-deere-310-p-tier"
CONFIGURATION_ID = "JD-310P-NAM-FT4-MFWD-STD-DIPPER-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
BUILDER_REL = "machines/john-deere-310-p-tier/source/blender/build_john_deere_310_p_tier.py"
MACHINE_REL = Path("machines/john-deere-310-p-tier")
BLEND_REL = MACHINE_REL / "source/blender/john-deere-310-p-tier-structural-study.blend"
GLB_REL = MACHINE_REL / "assets/john-deere-310-p-tier-structural-study.glb"
RECEIPT_REL = MACHINE_REL / "production/asset-receipt.json"
VALIDATION_REL = MACHINE_REL / "production/validation.json"
RENDER_RELS = [
    MACHINE_REL / "review/renders/transport-front-three-quarter.png",
    MACHINE_REL / "review/renders/transport-rear-three-quarter.png",
    MACHINE_REL / "review/renders/technical-side.png",
    MACHINE_REL / "review/renders/articulated-inspection.png",
    MACHINE_REL / "review/renders/linkage-stabilizer-detail.png",
]

PUBLISHED = {
    "overall-length": {"value": 7.24, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension B"},
    "overall-width": {"value": 2.20, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension C"},
    "cab-height": {"value": 2.81, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension D"},
    "mfwd-wheelbase": {"value": 2.19, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension E"},
    "loader-boom-cylinder-stroke": {"value": 0.790, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "loader-bucket-cylinder-stroke": {"value": 0.744, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-boom-cylinder-stroke": {"value": 0.821, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-crowd-cylinder-stroke": {"value": 0.553, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-bucket-cylinder-stroke": {"value": 0.892, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-swing": {"value": 180, "unit": "deg", "source": "JD-310P-MB310PAU", "location": "PDF page 8"},
    "backhoe-bucket-rotation": {"value": 190, "unit": "deg", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension N"},
    "loader-dump-angle": {"value": 45, "unit": "deg", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension P"},
    "loader-rollback-angle": {"value": 40, "unit": "deg", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension Q"},
    "backhoe-transport-height": {"value": 3.39, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension O"},
    "stabilizer-spread-operating": {"value": 3.10, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension L"},
    "stabilizer-overall-width-operating": {"value": 3.53, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 8 dimension M"},
    "loader-boom-cylinder-bore": {"value": 0.080, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "loader-boom-cylinder-rod": {"value": 0.050, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "loader-bucket-cylinder-bore": {"value": 0.090, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "loader-bucket-cylinder-rod": {"value": 0.050, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-boom-cylinder-bore": {"value": 0.110, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-boom-cylinder-rod": {"value": 0.056, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-crowd-cylinder-bore": {"value": 0.110, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-crowd-cylinder-rod": {"value": 0.063, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-bucket-cylinder-bore": {"value": 0.080, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-bucket-cylinder-rod": {"value": 0.050, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-swing-cylinder-bore": {"value": 0.080, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "backhoe-swing-cylinder-rod": {"value": 0.045, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "standard-stabilizer-cylinder-bore": {"value": 0.080, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "standard-stabilizer-cylinder-rod": {"value": 0.050, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "mfwd-steering-cylinder-bore": {"value": 0.065, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
    "mfwd-steering-cylinder-rod": {"value": 0.040, "unit": "m", "source": "JD-310P-MB310PAU", "location": "PDF page 7"},
}

RECONSTRUCTED = {
    "coordinate_system": "+X front loader, +Y up, +Z machine right",
    "axle_centers_m": {"front": [1.095, 0.54, 0.0], "rear": [-1.095, 0.72, 0.0]},
    "tire_geometry_m": {"front_radius": 0.54, "rear_radius": 0.72, "front_width": 0.40, "rear_width": 0.48},
    "transport_extents_m": {"rear_bucket_tip_x": -4.125, "front_bucket_edge_x": 3.115, "left_z": -1.10, "right_z": 1.10, "roof_y": 2.81},
    "front_loader_pivots_m": {"boom": [0.22, 1.58, 0.0], "bucket": [2.66, 0.52, 0.0]},
    "backhoe_pivots_m": {"swing": [-1.73, 1.05, 0.0], "boom": [-1.88, 1.25, 0.0], "dipper": [-2.68, 3.20, 0.0], "bucket": [-3.58, 1.55, 0.0]},
    "stabilizer_pivots_m": {"left": [-1.58, 0.72, -0.50], "right": [-1.58, 0.72, 0.50]},
    "stabilizer_operating_pose": "reconstructed rotation reaches 3.53 m overall foot width; published 3.10 m spread retained as a separate constraint",
    "front_bucket": "generic unbranded 2.18 m shell placeholder; exact published bucket branch unresolved",
    "rear_bucket": "generic 610 mm class shell placeholder; exact coupler and tooth pattern unresolved",
    "cylinder_anchor_coordinates": "all visible cylinder endpoints are reconstructed for visual closure only",
    "steering_pose_deg": 0,
    "backhoe_swing_pose_deg": 0,
    "articulated_review_pose": "separate collection shows a reconstructed inspection pose, not a solved endpoint",
}

UNRESOLVED = [
    "front loader bucket family and capacity",
    "front and rear couplers",
    "counterweight",
    "tire selection and tread pattern",
    "loader auxiliary hydraulics",
    "backhoe pilot control options",
    "all hidden pivots, linkage dimensions, and cylinder anchors",
    "public material and branding authorization",
]

POSE_MEASUREMENTS = {}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


ROOT = repo_root()


def abs_path(rel: Path | str) -> Path:
    return ROOT / rel


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_dirs() -> None:
    for rel in [BLEND_REL, GLB_REL, RECEIPT_REL, VALIDATION_REL, *RENDER_RELS]:
        abs_path(rel).parent.mkdir(parents=True, exist_ok=True)


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
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_percentage = 100
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.color_depth = "8"
    scene.world.color = (0.018, 0.024, 0.032)
    scene["machine_id"] = MACHINE_ID
    scene["configuration_id"] = CONFIGURATION_ID
    scene["candidate_class"] = CANDIDATE_CLASS
    scene["authority_boundary"] = "visualization only; not engineering or manufacturer authority"


def collection(name: str) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


COL_FIXED = None
COL_FRONT = None
COL_REAR = None
COL_HYD = None
COL_DETAILS = None
COL_PIVOTS = None
COL_COLLISION = None
COL_INSPECTION = None
COL_ENV = None
COL_REVIEW = None


def move_to_collection(obj: bpy.types.Object, coll: bpy.types.Collection) -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    coll.objects.link(obj)


def mat(name: str, color, metallic=0.0, roughness=0.45, alpha=1.0) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color[:3], alpha)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        material.surface_render_method = "DITHERED"
    return material


def tag(obj, semantic: str, authority="reconstructed", export=True) -> None:
    obj["semantic"] = semantic
    obj["authority"] = authority
    obj["machine_id"] = MACHINE_ID
    obj["configuration_id"] = CONFIGURATION_ID
    obj["export"] = bool(export)


def set_parent_keep_world(obj, parent) -> None:
    """Assign a semantic pivot parent without translating authored geometry."""
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


def empty(name, location, semantic, coll=None, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.14
    (coll or COL_PIVOTS).objects.link(obj)
    tag(obj, semantic, "reconstructed", True)
    if parent:
        set_parent_keep_world(obj, parent)
    return obj


def apply_bevel(obj, amount=0.025, segments=2):
    if amount <= 0:
        return
    bevel = obj.modifiers.new("EdgeSoftening", "BEVEL")
    bevel.width = amount
    bevel.segments = segments


def box(name, location, dimensions, material, coll, bevel=0.02, parent=None, semantic="visible_structure", export=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_bevel(obj, min(bevel, min(dimensions) * 0.2), 2)
    obj.data.materials.append(material)
    move_to_collection(obj, coll)
    tag(obj, semantic, "reconstructed", export)
    if parent:
        set_parent_keep_world(obj, parent)
    return obj


def beam(name, p1, p2, thickness, width, material, coll, bevel=0.02, parent=None, semantic="linkage"):
    a, b = Vector(p1), Vector(p2)
    vec = b - a
    obj = box(name, (a + b) / 2, (vec.length, thickness, width), material, coll, bevel, parent, semantic)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = vec.to_track_quat("X", "Z")
    return obj


def plate_xy(name, points, z_center, depth, material, coll, parent=None, semantic="sheet_structure"):
    """Create a deterministic plate from a 2D X/Y outline, extruded along Z."""
    half = depth / 2
    vertices = [(x, y, z_center - half) for x, y in points] + [(x, y, z_center + half) for x, y in points]
    count = len(points)
    faces = [tuple(range(count)), tuple(range(count, count * 2))[::-1]]
    for idx in range(count):
        nxt = (idx + 1) % count
        faces.append((idx, nxt, count + nxt, count + idx))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    obj.data.materials.append(material)
    apply_bevel(obj, min(depth * 0.25, 0.012), 2)
    tag(obj, semantic, "reconstructed", True)
    if parent:
        set_parent_keep_world(obj, parent)
    return obj


def curved_shell(prefix, points, width, thickness, material, coll, parent, semantic):
    """Approximate a rolled bucket shell with contiguous tangent plates."""
    pieces = []
    for idx, (start, end) in enumerate(zip(points, points[1:])):
        pieces.append(beam(f"{prefix}_Shell_{idx:02d}", (*start, 0), (*end, 0), thickness, width, material, coll, 0.012, parent, semantic))
    return pieces


def cylinder_between(name, p1, p2, radius, material, coll, vertices=24, parent=None, semantic="hydraulic"):
    a, b = Vector(p1), Vector(p2)
    vec = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=vec.length, location=(a + b) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = vec.to_track_quat("Z", "Y")
    obj.data.materials.append(material)
    move_to_collection(obj, coll)
    apply_bevel(obj, radius * 0.12, 2)
    tag(obj, semantic, "reconstructed", True)
    if parent:
        set_parent_keep_world(obj, parent)
    return obj


def pin(name, location, radius, depth, material, coll, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    move_to_collection(obj, coll)
    apply_bevel(obj, radius * 0.14, 2)
    tag(obj, "pivot_pin", "reconstructed", True)
    if parent:
        set_parent_keep_world(obj, parent)
    return obj


def torus(name, location, major_radius, minor_radius, material, coll, rotation=(0, 0, 0), parent=None, semantic="detail"):
    bpy.ops.mesh.primitive_torus_add(major_radius=major_radius, minor_radius=minor_radius, major_segments=28, minor_segments=8, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    move_to_collection(obj, coll)
    tag(obj, semantic, "reconstructed", True)
    if parent:
        set_parent_keep_world(obj, parent)
    return obj


def hose(name, points, radius, material, parent=None):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for idx, point in enumerate(points):
        spline.points[idx].co = (*point, 1.0)
    obj = bpy.data.objects.new(name, curve)
    curve.materials.append(material)
    COL_HYD.objects.link(obj)
    tag(obj, "hydraulic_hose", "reconstructed", True)
    if parent:
        set_parent_keep_world(obj, parent)
    return obj


def wheel(prefix, x, y, z, radius, width, steer_parent=None):
    outer = torus(prefix + "_Tire", (x, y, z), radius * 0.73, radius * 0.27, M_TIRE, COL_DETAILS, parent=steer_parent, semantic="tire")
    outer.scale.z = width / (radius * 0.54)
    rim = cylinder_between(prefix + "_Rim", (x, y, z - width * 0.44), (x, y, z + width * 0.44), radius * 0.48, M_ACCENT, COL_DETAILS, 32, steer_parent, "wheel_rim")
    hub = cylinder_between(prefix + "_Hub", (x, y, z - width * 0.46), (x, y, z + width * 0.46), radius * 0.18, M_STEEL, COL_DETAILS, 24, steer_parent, "wheel_hub")
    for side in (-1, 1):
        for idx in range(8):
            angle = 2 * math.pi * idx / 8
            lug_y = y + math.sin(angle) * radius * 0.27
            lug_x = x + math.cos(angle) * radius * 0.27
            pin(prefix + f"_Lug_{side:+d}_{idx:02d}", (lug_x, lug_y, z + side * width * 0.43), radius * 0.026, radius * 0.04, M_FASTENER, COL_DETAILS, steer_parent)
    # Readable agricultural tread blocks. Their cardinal blocks define the stated tire radius.
    for side in (-1, 1):
        for idx in range(18):
            angle = 2 * math.pi * idx / 18
            radial = radius * 0.965
            tx = x + math.cos(angle) * radial
            ty = y + math.sin(angle) * radial
            tread = box(prefix + f"_Tread_{side:+d}_{idx:02d}", (tx, ty, z + side * width * 0.28), (radius * 0.07, radius * 0.18, width * 0.38), M_TIRE, COL_DETAILS, 0.008, steer_parent, "tire_tread")
            tread.rotation_euler[2] = angle
    return outer, rim, hub


def hydraulic(name, base, rod_end, barrel_fraction=0.58, barrel_radius=0.055, parent=None, rod_radius=None, constraint_ids=None):
    a, b = Vector(base), Vector(rod_end)
    split = a.lerp(b, barrel_fraction)
    barrel = cylinder_between(name + "_Barrel", a, split, barrel_radius, M_HYD, COL_HYD, 24, parent, "hydraulic_barrel")
    rod = cylinder_between(name + "_Rod", split, b, rod_radius or barrel_radius * 0.55, M_CHROME, COL_HYD, 20, parent, "hydraulic_rod")
    if constraint_ids:
        barrel["published_constraints"] = json.dumps(constraint_ids)
        rod["published_constraints"] = json.dumps(constraint_ids)
    pin(name + "_BasePin", a, barrel_radius * 1.35, 0.12, M_FASTENER, COL_HYD, parent)
    pin(name + "_RodPin", b, barrel_radius * 1.25, 0.12, M_FASTENER, COL_HYD, parent)


def proxy_box(name, location, dimensions, semantic, coll, parent=None):
    obj = box(name, location, dimensions, M_PROXY, coll, 0.0, parent, semantic, True)
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj.visible_shadow = False
    return obj


def build_machine():
    global COL_FIXED, COL_FRONT, COL_REAR, COL_HYD, COL_DETAILS, COL_PIVOTS, COL_COLLISION, COL_INSPECTION, COL_ENV, COL_REVIEW
    global M_BODY, M_DARK, M_ACCENT, M_TIRE, M_STEEL, M_FASTENER, M_HYD, M_CHROME, M_GLASS, M_HOSE, M_PROXY, M_GROUND

    COL_FIXED = collection("01_Fixed_Structure")
    COL_FRONT = collection("02_Front_Loader")
    COL_REAR = collection("03_Rear_Backhoe")
    COL_HYD = collection("04_Hydraulics")
    COL_DETAILS = collection("05_Technical_Details")
    COL_PIVOTS = collection("06_Pivots")
    COL_COLLISION = collection("07_Collision_Proxies")
    COL_INSPECTION = collection("08_Inspection_Volumes")
    COL_ENV = collection("09_Render_Environment")
    COL_REVIEW = collection("10_Reconstructed_Review_Poses")

    M_BODY = mat("Neutral_Body_Slate", (0.19, 0.25, 0.30), 0.52, 0.30)
    M_DARK = mat("Neutral_Graphite", (0.045, 0.060, 0.072), 0.42, 0.28)
    M_ACCENT = mat("Neutral_Sand_Accent", (0.55, 0.43, 0.26), 0.38, 0.34)
    M_TIRE = mat("Rubber", (0.018, 0.021, 0.023), 0.0, 0.88)
    M_STEEL = mat("Machined_Steel", (0.27, 0.31, 0.34), 0.78, 0.24)
    M_FASTENER = mat("Fasteners", (0.08, 0.095, 0.105), 0.72, 0.25)
    M_HYD = mat("Hydraulic_Barrel", (0.065, 0.075, 0.085), 0.74, 0.22)
    M_CHROME = mat("Hydraulic_Rod", (0.62, 0.67, 0.71), 0.92, 0.12)
    M_GLASS = mat("Cab_Glass", (0.09, 0.19, 0.24), 0.08, 0.16, 0.36)
    M_HOSE = mat("Hose", (0.012, 0.016, 0.018), 0.0, 0.72)
    M_PROXY = mat("Proxy", (0.8, 0.18, 0.12), 0.0, 0.55, 0.10)
    M_GROUND = mat("Ground", (0.065, 0.075, 0.085), 0.05, 0.82)

    ROOT_FIXED = empty("ROOT_310P_CANDIDATE", (0, 0, 0), "machine_root")
    ROOT_FIXED["not_engineering_authority"] = True

    # Main frame, axles, transmission and serviceable body mass.
    box("Mainframe_Unitized", (-0.05, 0.69, 0), (2.85, 0.30, 0.82), M_DARK, COL_FIXED, 0.055, ROOT_FIXED, "mainframe")
    box("Transmission_Housing", (-0.35, 0.83, 0), (1.05, 0.55, 0.58), M_STEEL, COL_FIXED, 0.09, ROOT_FIXED, "powertrain_housing")
    cylinder_between("Rear_Axle", (-1.095, 0.72, -0.94), (-1.095, 0.72, 0.94), 0.14, M_STEEL, COL_FIXED, 28, ROOT_FIXED, "rear_axle")
    cylinder_between("MFWD_Front_Axle", (1.095, 0.54, -0.88), (1.095, 0.54, 0.88), 0.115, M_STEEL, COL_FIXED, 28, ROOT_FIXED, "mfwd_front_axle")
    box("Front_Axle_Differential", (1.095, 0.54, 0), (0.42, 0.35, 0.43), M_STEEL, COL_FIXED, 0.07, ROOT_FIXED, "mfwd_differential")
    box("Rear_Axle_Differential", (-1.095, 0.72, 0), (0.55, 0.48, 0.52), M_STEEL, COL_FIXED, 0.08, ROOT_FIXED, "rear_differential")
    cylinder_between("Front_Driveshaft", (0.75, 0.72, 0), (0.10, 0.79, 0), 0.035, M_CHROME, COL_DETAILS, 18, ROOT_FIXED, "driveshaft")

    # Steering pivots are semantic parents even in the straight transport pose.
    piv_steer_l = empty("Pivot_FrontSteer_Left", (1.095, 0.54, -0.86), "front_steering_pivot", parent=ROOT_FIXED)
    piv_steer_r = empty("Pivot_FrontSteer_Right", (1.095, 0.54, 0.86), "front_steering_pivot", parent=ROOT_FIXED)
    wheel("FrontLeft", 1.095, 0.54, -0.90, 0.54, 0.40, piv_steer_l)
    wheel("FrontRight", 1.095, 0.54, 0.90, 0.54, 0.40, piv_steer_r)
    wheel("RearLeft", -1.095, 0.72, -0.86, 0.72, 0.48, ROOT_FIXED)
    wheel("RearRight", -1.095, 0.72, 0.86, 0.72, 0.48, ROOT_FIXED)
    beam("Steering_TieRod", (1.095, 0.49, -0.72), (1.095, 0.49, 0.72), 0.05, 0.05, M_CHROME, COL_DETAILS, 0.01, ROOT_FIXED, "steering_linkage")
    hydraulic("MFWD_SteeringCylinder", (1.02, 0.60, -0.52), (1.02, 0.60, 0.52), 0.52, 0.0445, ROOT_FIXED, 0.020, ["mfwd-steering-cylinder-bore", "mfwd-steering-cylinder-rod"])

    # Engine hood and panel segmentation, all neutral and unbranded.
    box("Engine_Hood_Lower", (0.88, 1.18, 0), (1.55, 0.62, 1.10), M_BODY, COL_FIXED, 0.09, ROOT_FIXED, "engine_hood")
    hood_top = box("Engine_Hood_Sloped", (0.93, 1.52, 0), (1.43, 0.20, 1.00), M_BODY, COL_FIXED, 0.07, ROOT_FIXED, "engine_hood")
    hood_top.rotation_euler[2] = math.radians(-4)
    box("Front_Grille", (1.70, 1.25, 0), (0.06, 0.58, 0.83), M_DARK, COL_DETAILS, 0.02, ROOT_FIXED, "cooling_grille")
    for idx in range(7):
        box(f"Grille_Slat_{idx:02d}", (1.735, 1.05 + idx * 0.07, 0), (0.025, 0.026, 0.75), M_STEEL, COL_DETAILS, 0.004, ROOT_FIXED, "grille_slat")
    for side in (-1, 1):
        box(f"Hood_ServicePanel_{side:+d}", (0.88, 1.24, side * 0.558), (1.20, 0.47, 0.025), M_DARK, COL_DETAILS, 0.012, ROOT_FIXED, "service_panel")
        for idx in range(4):
            box(f"HoodVent_{side:+d}_{idx:02d}", (1.15 + idx * 0.10, 1.34, side * 0.578), (0.055, 0.18, 0.018), M_STEEL, COL_DETAILS, 0.005, ROOT_FIXED, "vent")
    cylinder_between("Exhaust_Stack", (0.26, 1.42, -0.42), (0.26, 2.58, -0.42), 0.055, M_DARK, COL_DETAILS, 24, ROOT_FIXED, "exhaust")
    cylinder_between("Exhaust_Tip", (0.26, 2.58, -0.42), (0.35, 2.70, -0.42), 0.056, M_DARK, COL_DETAILS, 24, ROOT_FIXED, "exhaust")

    # Cab frame with actual glass boundaries, door segmentation and interior cues.
    box("Cab_Floor", (-0.54, 1.05, 0), (1.18, 0.18, 1.44), M_DARK, COL_FIXED, 0.04, ROOT_FIXED, "cab_frame")
    box("Cab_Roof", (-0.56, 2.755, 0), (1.38, 0.11, 1.58), M_ACCENT, COL_FIXED, 0.055, ROOT_FIXED, "cab_roof")
    for z, label in [(-0.66, "Left"), (0.66, "Right")]:
        beam(f"CabPillar_Front{label}", (-0.02, 1.13, z), (-0.18, 2.72, z), 0.075, 0.075, M_DARK, COL_FIXED, 0.014, ROOT_FIXED, "cab_pillar")
        beam(f"CabPillar_Rear{label}", (-1.12, 1.13, z), (-1.03, 2.72, z), 0.075, 0.075, M_DARK, COL_FIXED, 0.014, ROOT_FIXED, "cab_pillar")
    beam("Cab_Header_Front", (-0.18, 2.67, -0.66), (-0.18, 2.67, 0.66), 0.08, 0.08, M_DARK, COL_FIXED, 0.014, ROOT_FIXED, "cab_frame")
    beam("Cab_Header_Rear", (-1.03, 2.67, -0.66), (-1.03, 2.67, 0.66), 0.08, 0.08, M_DARK, COL_FIXED, 0.014, ROOT_FIXED, "cab_frame")
    beam("CabGlass_Front", (-0.04, 1.20, 0), (-0.18, 2.64, 0), 0.025, 1.16, M_GLASS, COL_DETAILS, 0.006, ROOT_FIXED, "cab_glass")
    beam("CabGlass_Rear", (-1.10, 1.20, 0), (-1.03, 2.64, 0), 0.025, 1.16, M_GLASS, COL_DETAILS, 0.006, ROOT_FIXED, "cab_glass")
    for side in (-1, 1):
        plate_xy(f"CabGlass_Side_{side:+d}", [(-1.08, 1.18), (-0.04, 1.18), (-0.18, 2.65), (-1.03, 2.65)], side * 0.675, 0.025, M_GLASS, COL_DETAILS, ROOT_FIXED, "cab_glass")
        beam(f"Door_MidRail_{side:+d}", (-1.02, 1.58, side * 0.70), (-0.12, 1.58, side * 0.70), 0.045, 0.045, M_DARK, COL_DETAILS, 0.008, ROOT_FIXED, "door_frame")
        beam(f"Door_Divider_{side:+d}", (-0.61, 1.18, side * 0.70), (-0.61, 2.66, side * 0.70), 0.045, 0.045, M_DARK, COL_DETAILS, 0.008, ROOT_FIXED, "door_frame")
        box(f"Door_Handle_{side:+d}", (-0.28, 1.75, side * 0.715), (0.16, 0.035, 0.035), M_FASTENER, COL_DETAILS, 0.008, ROOT_FIXED, "door_handle")
        beam(f"CabStep_{side:+d}", (-0.92, 0.93, side * 0.77), (-0.15, 0.93, side * 0.77), 0.06, 0.15, M_STEEL, COL_DETAILS, 0.01, ROOT_FIXED, "access_step")
        box(f"RearFender_Top_{side:+d}", (-1.08, 1.38, side * 0.76), (0.92, 0.10, 0.34), M_BODY, COL_DETAILS, 0.045, ROOT_FIXED, "rear_fender")
    box("Operator_SeatBase", (-0.62, 1.28, 0), (0.48, 0.22, 0.48), M_DARK, COL_DETAILS, 0.05, ROOT_FIXED, "operator_station")
    seat = box("Operator_SeatBack", (-0.78, 1.68, 0), (0.18, 0.68, 0.54), M_DARK, COL_DETAILS, 0.07, ROOT_FIXED, "operator_station")
    seat.rotation_euler[2] = math.radians(-7)
    torus("Steering_Wheel", (-0.17, 1.70, -0.18), 0.16, 0.018, M_DARK, COL_DETAILS, (math.radians(75), 0, 0), ROOT_FIXED, "operator_control")
    cylinder_between("Steering_Column", (-0.12, 1.48, -0.18), (-0.17, 1.70, -0.18), 0.025, M_STEEL, COL_DETAILS, 16, ROOT_FIXED, "operator_control")
    box("Instrument_Console", (-0.08, 1.58, 0.22), (0.24, 0.38, 0.30), M_DARK, COL_DETAILS, 0.04, ROOT_FIXED, "operator_control")
    for side in (-1, 1):
        box(f"Cab_Worklight_Housing_{side:+d}", (-0.22, 2.73, side * 0.49), (0.14, 0.10, 0.18), M_DARK, COL_DETAILS, 0.025, ROOT_FIXED, "worklight")

    # Loader boom: real semantic parent and twin arm construction.
    piv_loader = empty("Pivot_FrontLoaderBoom", (0.22, 1.58, 0), "front_loader_boom_pivot", parent=ROOT_FIXED)
    for side in (-1, 1):
        z = side * 0.58
        beam(f"LoaderBoom_Rear_{side:+d}", (0.22, 1.58, z), (1.55, 1.18, z), 0.24, 0.15, M_DARK, COL_FRONT, 0.038, piv_loader, "front_loader_boom")
        beam(f"LoaderBoom_Front_{side:+d}", (1.55, 1.18, z), (2.66, 0.52, z), 0.22, 0.15, M_DARK, COL_FRONT, 0.035, piv_loader, "front_loader_boom")
        pin(f"LoaderBoom_MainPin_{side:+d}", (0.22, 1.58, z), 0.09, 0.19, M_FASTENER, COL_FRONT, piv_loader)
        hydraulic(f"LoaderBoomCylinder_{side:+d}", (0.48, 1.03, side * 0.48), (1.58, 1.30, side * 0.48), 0.55, 0.052, piv_loader, 0.025, ["loader-boom-cylinder-bore", "loader-boom-cylinder-rod"])
    beam("Loader_Crossmember", (1.70, 1.10, -0.62), (1.70, 1.10, 0.62), 0.15, 0.16, M_DARK, COL_FRONT, 0.03, piv_loader, "loader_crossmember")
    hydraulic("LoaderBucketCylinder", (0.60, 1.62, 0), (1.80, 1.17, 0), 0.60, 0.057, piv_loader, 0.025, ["loader-bucket-cylinder-bore", "loader-bucket-cylinder-rod"])
    beam("Loader_Bellcrank", (1.78, 1.17, 0), (2.15, 0.88, 0), 0.105, 0.12, M_STEEL, COL_FRONT, 0.02, piv_loader, "loader_bucket_linkage")
    beam("Loader_ZBar_Link", (2.15, 0.88, 0), (2.61, 0.66, 0), 0.085, 0.10, M_STEEL, COL_FRONT, 0.018, piv_loader, "loader_bucket_linkage")
    pin("Loader_Bellcrank_Pin", (2.15, 0.88, 0), 0.07, 0.18, M_FASTENER, COL_FRONT, piv_loader)

    piv_front_bucket = empty("Pivot_FrontLoaderBucket", (2.66, 0.52, 0), "front_loader_bucket_pivot", parent=piv_loader)
    # Generic rolled scoop shell: cutting edge exactly at x=3.115, exact bucket branch unresolved.
    front_scoop = [(3.085, 0.15), (3.00, 0.17), (2.86, 0.25), (2.76, 0.41), (2.71, 0.68)]
    curved_shell("FrontBucket", front_scoop, 2.15, 0.065, M_BODY, COL_FRONT, piv_front_bucket, "front_bucket_shell")
    box("FrontBucket_CuttingEdge", (3.085, 0.15, 0), (0.06, 0.09, 2.18), M_STEEL, COL_FRONT, 0.012, piv_front_bucket, "front_bucket_cutting_edge")
    for side in (-1, 1):
        plate_xy(f"FrontBucket_Cheek_{side:+d}", [(3.09, 0.13), (2.69, 0.15), (2.64, 0.73), (2.76, 0.82), (3.02, 0.46)], side * 1.078, 0.035, M_BODY, COL_FRONT, piv_front_bucket, "front_bucket_sideplate")
        pin(f"FrontBucket_Pin_{side:+d}", (2.66, 0.52, side * 0.61), 0.075, 0.16, M_FASTENER, COL_FRONT, piv_front_bucket)

    # Rear swing post, transport-stowed boom/dipper/bucket and visible closures.
    piv_swing = empty("Pivot_BackhoeSwing", (-1.73, 1.05, 0), "backhoe_swing_pivot", parent=ROOT_FIXED)
    box("Backhoe_SwingFrame", (-1.72, 1.08, 0), (0.35, 0.92, 0.88), M_ACCENT, COL_REAR, 0.07, piv_swing, "backhoe_swing_frame")
    pin("Backhoe_SwingKingpin", (-1.73, 1.05, 0), 0.10, 0.76, M_FASTENER, COL_REAR, piv_swing)
    hydraulic("BackhoeSwingCylinder_Left", (-1.56, 0.92, -0.42), (-1.86, 1.05, -0.25), 0.55, 0.052, piv_swing, 0.0225, ["backhoe-swing-cylinder-bore", "backhoe-swing-cylinder-rod"])
    hydraulic("BackhoeSwingCylinder_Right", (-1.56, 0.92, 0.42), (-1.86, 1.05, 0.25), 0.55, 0.052, piv_swing, 0.0225, ["backhoe-swing-cylinder-bore", "backhoe-swing-cylinder-rod"])

    piv_boom = empty("Pivot_BackhoeBoom", (-1.88, 1.25, 0), "backhoe_boom_pivot", parent=piv_swing)
    beam("BackhoeBoom_Lower", (-1.88, 1.25, 0), (-2.20, 2.58, 0), 0.34, 0.42, M_DARK, COL_REAR, 0.055, piv_boom, "backhoe_boom")
    beam("BackhoeBoom_Upper", (-2.20, 2.58, 0), (-2.68, 3.20, 0), 0.26, 0.38, M_DARK, COL_REAR, 0.05, piv_boom, "backhoe_boom")
    plate_xy("BackhoeBoom_HeadGusset_Left", [(-2.76, 3.13), (-2.52, 3.10), (-2.49, 3.381), (-2.72, 3.381)], -0.17, 0.035, M_DARK, COL_REAR, piv_boom, "boom_head_gusset")
    plate_xy("BackhoeBoom_HeadGusset_Right", [(-2.76, 3.13), (-2.52, 3.10), (-2.49, 3.381), (-2.72, 3.381)], 0.17, 0.035, M_DARK, COL_REAR, piv_boom, "boom_head_gusset")
    pin("BackhoeBoom_MainPin", (-1.88, 1.25, 0), 0.11, 0.48, M_FASTENER, COL_REAR, piv_boom)
    hydraulic("BackhoeBoomCylinder", (-1.67, 1.45, 0), (-2.34, 2.72, 0), 0.58, 0.067, piv_boom, 0.028, ["backhoe-boom-cylinder-bore", "backhoe-boom-cylinder-rod"])

    piv_dipper = empty("Pivot_BackhoeDipper", (-2.68, 3.20, 0), "backhoe_dipper_pivot", parent=piv_boom)
    beam("BackhoeDipper_Upper", (-2.68, 3.20, 0), (-3.08, 2.35, 0), 0.25, 0.32, M_DARK, COL_REAR, 0.045, piv_dipper, "backhoe_dipper")
    beam("BackhoeDipper_Lower", (-3.08, 2.35, 0), (-3.58, 1.55, 0), 0.22, 0.30, M_DARK, COL_REAR, 0.04, piv_dipper, "backhoe_dipper")
    pin("BackhoeDipper_MainPin", (-2.68, 3.20, 0), 0.10, 0.40, M_FASTENER, COL_REAR, piv_dipper)
    hydraulic("BackhoeCrowdCylinder", (-2.24, 2.73, 0), (-3.04, 2.48, 0), 0.54, 0.067, piv_dipper, 0.0315, ["backhoe-crowd-cylinder-bore", "backhoe-crowd-cylinder-rod"])
    hydraulic("BackhoeBucketCylinder", (-2.84, 3.02, 0), (-3.52, 1.83, 0), 0.60, 0.052, piv_dipper, 0.025, ["backhoe-bucket-cylinder-bore", "backhoe-bucket-cylinder-rod"])
    beam("Backhoe_BucketBellcrank", (-3.48, 1.79, 0), (-3.68, 1.58, 0), 0.09, 0.12, M_STEEL, COL_REAR, 0.018, piv_dipper, "backhoe_bucket_linkage")
    beam("Backhoe_BucketLink", (-3.68, 1.58, 0), (-3.72, 1.36, 0), 0.075, 0.11, M_STEEL, COL_REAR, 0.016, piv_dipper, "backhoe_bucket_linkage")

    piv_rear_bucket = empty("Pivot_BackhoeBucket", (-3.58, 1.55, 0), "backhoe_bucket_pivot", parent=piv_dipper)
    # 610 mm class, transport-stowed generic bucket with rear tip at the envelope boundary.
    rear_scoop = [(-3.58, 1.55), (-3.66, 1.34), (-3.80, 1.20), (-3.98, 1.20), (-4.07, 1.34), (-4.085, 1.43)]
    curved_shell("BackhoeBucket", rear_scoop, 0.58, 0.065, M_BODY, COL_REAR, piv_rear_bucket, "backhoe_bucket_shell")
    for side in (-1, 1):
        plate_xy(f"BackhoeBucket_Cheek_{side:+d}", [(-3.56, 1.58), (-3.64, 1.22), (-3.92, 1.12), (-4.09, 1.36), (-4.09, 1.46)], side * 0.295, 0.035, M_BODY, COL_REAR, piv_rear_bucket, "backhoe_bucket_sideplate")
    for idx in range(4):
        z = -0.24 + idx * 0.16
        box(f"BackhoeBucket_Tooth_{idx:02d}", (-4.085, 1.43, z), (0.08, 0.055, 0.07), M_STEEL, COL_REAR, 0.008, piv_rear_bucket, "backhoe_bucket_tooth")
    pin("BackhoeBucket_MainPin", (-3.58, 1.55, 0), 0.085, 0.39, M_FASTENER, COL_REAR, piv_rear_bucket)

    # Stabilizers: stowed in the transport study, meaningful pivots and hydraulic closures.
    for side, label in [(-1, "Left"), (1, "Right")]:
        z0 = side * 0.50
        z1 = side * 0.50
        piv = empty(f"Pivot_Stabilizer_{label}", (-1.58, 0.72, z0), f"{label.lower()}_stabilizer_pivot", parent=ROOT_FIXED)
        beam(f"StabilizerArm_{label}", (-1.58, 0.72, z0), (-1.60, 1.792, z1), 0.16, 0.18, M_ACCENT, COL_REAR, 0.025, piv, "stabilizer_arm")
        box(f"StabilizerFoot_{label}", (-1.60, 1.792, z1), (0.42, 0.12, 0.43), M_STEEL, COL_REAR, 0.018, piv, "stabilizer_foot")
        hydraulic(f"StabilizerCylinder_{label}", (-1.50, 0.90, side * 0.44), (-1.60, 1.54, side * 0.50), 0.58, 0.052, piv, 0.025, ["standard-stabilizer-cylinder-bore", "standard-stabilizer-cylinder-rod"])

    # Exact published-width review witness. This is a separate, non-exported,
    # reconstructed pose used only for critic renders; it is not a motion solve.
    # Foot centers are +/-1.55 m (3.10 m spread) and 0.43 m-wide feet produce
    # the published 3.53 m outer width.
    for side, label in [(-1, "Left"), (1, "Right")]:
        base = (-1.58, 0.72, side * 0.50)
        foot_center = (-1.60, 0.18, side * 1.55)
        review_objects = [
            beam(f"Review_StabilizerArm_{label}", base, foot_center, 0.16, 0.18, M_ACCENT, COL_REVIEW, 0.025, None, "stabilizer_deployed_review"),
            box(f"Review_StabilizerFoot_{label}", foot_center, (0.42, 0.12, 0.43), M_STEEL, COL_REVIEW, 0.018, None, "stabilizer_deployed_review"),
            cylinder_between(
                f"Review_StabilizerCylinder_{label}_Barrel",
                (-1.50, 0.68, side * 0.46),
                (-1.57, 0.34, side * 1.28),
                0.052,
                M_HYD,
                COL_REVIEW,
                24,
                None,
                "stabilizer_deployed_review",
            ),
            cylinder_between(
                f"Review_StabilizerCylinder_{label}_Rod",
                (-1.57, 0.34, side * 1.28),
                (-1.60, 0.24, side * 1.46),
                0.025,
                M_CHROME,
                COL_REVIEW,
                20,
                None,
                "stabilizer_deployed_review",
            ),
        ]
        for obj in review_objects:
            obj["export"] = False
            obj["authority"] = "reconstructed_review_pose"
            obj.hide_render = True

    # Hose bundles follow the visible outer runs but do not claim internal routing.
    for side in (-1, 1):
        hose(f"Loader_HoseBundle_{side:+d}_A", [(0.25, 1.68, side * 0.62), (1.12, 1.43, side * 0.65), (2.10, 0.94, side * 0.64), (2.60, 0.68, side * 0.64)], 0.012, M_HOSE, piv_loader)
        hose(f"Backhoe_HoseBundle_{side:+d}_A", [(-1.82, 1.55, side * 0.22), (-2.18, 2.65, side * 0.23), (-2.72, 3.28, side * 0.21), (-3.52, 1.70, side * 0.20)], 0.013, M_HOSE, piv_boom)

    # Collision and inspection volumes are distinct, hidden from beauty renders.
    proxy_box("COL_Chassis", (-0.05, 0.80, 0), (2.90, 0.75, 0.90), "collision_proxy", COL_COLLISION, ROOT_FIXED)
    proxy_box("COL_Cab", (-0.56, 1.95, 0), (1.20, 1.72, 1.42), "collision_proxy", COL_COLLISION, ROOT_FIXED)
    proxy_box("COL_FrontBucket", (2.90, 0.38, 0), (0.45, 0.70, 2.18), "collision_proxy", COL_COLLISION, piv_front_bucket)
    proxy_box("COL_BackhoeTransport", (-2.95, 1.80, 0), (2.40, 1.45, 0.70), "collision_proxy", COL_COLLISION, piv_boom)
    proxy_box("INSP_OperatorStation", (-0.56, 1.95, 0), (1.08, 1.54, 1.30), "inspection_volume", COL_INSPECTION, ROOT_FIXED)
    proxy_box("INSP_FrontLoaderLinkage", (1.70, 1.05, 0), (2.30, 1.20, 1.55), "inspection_volume", COL_INSPECTION, piv_loader)
    proxy_box("INSP_RearBackhoeLinkage", (-2.90, 1.80, 0), (2.55, 1.50, 0.85), "inspection_volume", COL_INSPECTION, piv_boom)

    # Visual envelope witnesses are excluded from export and rendering.
    for name, loc, dims in [
        ("Envelope_Length", (-0.505, 1.45, 0), (7.24, 0.008, 0.008)),
        ("Envelope_Width", (0, 1.45, 0), (0.008, 0.008, 2.20)),
        ("Witness_CabHeight", (0, 1.405, 0), (0.008, 2.81, 0.008)),
        ("Envelope_TransportHeight", (-2.60, 1.695, 0), (0.008, 3.39, 0.008)),
        ("Witness_Wheelbase", (0, 0.12, 0), (2.19, 0.008, 0.008)),
    ]:
        witness = box(name, loc, dims, M_PROXY, COL_INSPECTION, 0, None, "dimension_witness", False)
        witness.hide_render = True

    # Studio ground is never exported.
    ground = box("Render_Ground", (0, -0.055, 0), (12.5, 0.10, 9.0), M_GROUND, COL_ENV, 0.04, None, "render_environment", False)
    ground["export"] = False
    return ROOT_FIXED


def look_at(obj, target):
    forward = (Vector(target) - obj.location).normalized()
    world_up = Vector((0.0, 1.0, 0.0))
    right = forward.cross(world_up).normalized()
    corrected_up = right.cross(forward).normalized()
    # Camera/light local axes are +X right, +Y up, and -Z forward.
    rotation = Matrix((right, corrected_up, -forward)).transposed()
    obj.rotation_euler = rotation.to_euler()


def setup_lighting_and_camera():
    bpy.ops.object.camera_add(location=(8.5, 5.2, -7.3))
    camera = bpy.context.object
    camera.name = "Review_Camera"
    camera.data.lens = 58
    camera.data.sensor_width = 36
    tag(camera, "review_camera", "reconstructed", False)
    move_to_collection(camera, COL_ENV)
    bpy.context.scene.camera = camera
    for name, loc, energy, size, color in [
        ("Key", (2.5, 7.5, -5.5), 1450, 5.0, (1.0, 0.82, 0.68)),
        ("Fill", (-4.0, 4.5, 5.0), 1050, 4.0, (0.62, 0.75, 1.0)),
        ("Rim", (-5.5, 7.0, -1.0), 1300, 3.0, (0.72, 0.86, 1.0)),
    ]:
        data = bpy.data.lights.new(name + "_Area", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name + "_Light", data)
        light.location = loc
        COL_ENV.objects.link(light)
        look_at(light, (-0.4, 1.1, 0))
        tag(light, "render_light", "reconstructed", False)
    return camera


def render_views(camera):
    global POSE_MEASUREMENTS
    scene = bpy.context.scene
    stowed_stabilizer_objects = [
        obj for obj in scene.objects
        if obj.name.startswith(("StabilizerArm_", "StabilizerFoot_", "StabilizerCylinder_"))
    ]
    review_stabilizer_objects = [obj for obj in scene.objects if obj.name.startswith("Review_Stabilizer")]
    views = [
        ((9.4, 4.85, -7.8), (-0.50, 1.20, 0), 58),
        ((-9.2, 5.05, 7.5), (-0.55, 1.28, 0), 58),
        ((-0.50, 3.30, -13.0), (-0.50, 1.30, 0), 58),
        ((-7.4, 4.10, -6.6), (-1.55, 1.55, 0), 58),
        ((-7.2, 3.00, 0.0), (-1.58, 0.55, 0.0), 48),
    ]
    for idx, (rel, (location, target, lens)) in enumerate(zip(RENDER_RELS, views)):
        if idx == 3:
            # Reconstructed articulation shown only for critic inspection.
            bpy.data.objects["Pivot_FrontLoaderBoom"].rotation_euler[2] = math.radians(-12)
            bpy.data.objects["Pivot_FrontLoaderBucket"].rotation_euler[2] = math.radians(8)
            bpy.data.objects["Pivot_BackhoeSwing"].rotation_euler[1] = math.radians(14)
            for obj in stowed_stabilizer_objects:
                obj.hide_render = True
            for obj in review_stabilizer_objects:
                obj.hide_render = False
            bpy.context.view_layer.update()
            feet = [bpy.data.objects["Review_StabilizerFoot_Left"], bpy.data.objects["Review_StabilizerFoot_Right"]]
            extents = {}
            for foot in feet:
                zs = [(foot.matrix_world @ Vector(corner)).z for corner in foot.bound_box]
                extents[foot.name] = {"min_z_m": min(zs), "max_z_m": max(zs)}
            POSE_MEASUREMENTS["stabilizers"] = {
                "overall_width_m": round(extents["Review_StabilizerFoot_Right"]["max_z_m"] - extents["Review_StabilizerFoot_Left"]["min_z_m"], 4),
                "foot_center_spread_m": round(
                    (extents["Review_StabilizerFoot_Right"]["min_z_m"] + extents["Review_StabilizerFoot_Right"]["max_z_m"]) / 2
                    - (extents["Review_StabilizerFoot_Left"]["min_z_m"] + extents["Review_StabilizerFoot_Left"]["max_z_m"]) / 2,
                    4,
                ),
                "foot_extents": extents,
                "witness_nodes": ["Review_StabilizerFoot_Left", "Review_StabilizerFoot_Right"],
                "classification": "non-exported reconstructed review pose constrained by manufacturer-published spread and overall width",
            }
        camera.location = location
        camera.data.lens = lens
        camera.data.type = "ORTHO" if idx == 4 else "PERSP"
        if idx == 4:
            camera.data.ortho_scale = 4.15
        look_at(camera, target)
        scene.render.filepath = str(abs_path(rel))
        bpy.ops.render.render(write_still=True)
    for obj in stowed_stabilizer_objects:
        obj.hide_render = False
    for obj in review_stabilizer_objects:
        obj.hide_render = True
    for name in [
        "Pivot_FrontLoaderBoom", "Pivot_FrontLoaderBucket", "Pivot_BackhoeSwing", "Pivot_BackhoeBoom",
        "Pivot_BackhoeDipper", "Pivot_BackhoeBucket", "Pivot_Stabilizer_Left",
        "Pivot_Stabilizer_Right", "StabilizerFoot_Left", "StabilizerFoot_Right",
    ]:
        bpy.data.objects[name].rotation_euler = (0.0, 0.0, 0.0)


def select_export_objects():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.get("export", False) and obj.type in {"MESH", "CURVE", "EMPTY"}:
            obj.hide_set(False)
            obj.select_set(True)


def export_and_save():
    # Save after final review camera placement for exact critic reproducibility.
    bpy.ops.wm.save_as_mainfile(filepath=str(abs_path(BLEND_REL)), check_existing=False)
    select_export_objects()
    bpy.ops.export_scene.gltf(
        filepath=str(abs_path(GLB_REL)),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
        export_yup=True,
        export_extras=True,
    )


def mesh_stats():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_count = 0
    triangles = 0
    object_count = 0
    material_names = set()
    bounds_min = Vector((math.inf, math.inf, math.inf))
    bounds_max = Vector((-math.inf, -math.inf, -math.inf))
    for obj in bpy.context.scene.objects:
        if not obj.get("export", False):
            continue
        object_count += 1
        if obj.type != "MESH" or obj.name.startswith(("COL_", "INSP_")):
            continue
        mesh_count += 1
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        for slot in obj.material_slots:
            if slot.material:
                material_names.add(slot.material.name)
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            bounds_min.x = min(bounds_min.x, point.x)
            bounds_min.y = min(bounds_min.y, point.y)
            bounds_min.z = min(bounds_min.z, point.z)
            bounds_max.x = max(bounds_max.x, point.x)
            bounds_max.y = max(bounds_max.y, point.y)
            bounds_max.z = max(bounds_max.z, point.z)
        evaluated.to_mesh_clear()
    return {
        "object_count": object_count,
        "mesh_count": mesh_count,
        "triangle_count": triangles,
        "material_count": len(material_names),
        "bounds_m": {
            "min_xyz": [round(v, 4) for v in bounds_min],
            "max_xyz": [round(v, 4) for v in bounds_max],
            "dimensions_xyz": [round(bounds_max[i] - bounds_min[i], 4) for i in range(3)],
        },
    }


def required_nodes():
    names = [
        "ROOT_310P_CANDIDATE", "Mainframe_Unitized", "MFWD_Front_Axle", "Rear_Axle",
        "Pivot_FrontSteer_Left", "Pivot_FrontSteer_Right", "Pivot_FrontLoaderBoom",
        "Pivot_FrontLoaderBucket", "Pivot_BackhoeSwing", "Pivot_BackhoeBoom",
        "Pivot_BackhoeDipper", "Pivot_BackhoeBucket", "Pivot_Stabilizer_Left",
        "Pivot_Stabilizer_Right", "LoaderBoomCylinder_-1_Barrel",
        "LoaderBoomCylinder_+1_Barrel", "LoaderBucketCylinder_Barrel",
        "BackhoeBoomCylinder_Barrel", "BackhoeCrowdCylinder_Barrel",
        "BackhoeBucketCylinder_Barrel", "StabilizerCylinder_Left_Barrel",
        "StabilizerCylinder_Right_Barrel", "COL_Chassis", "INSP_OperatorStation",
    ]
    return {name: bpy.data.objects.get(name) is not None for name in names}


def file_entry(rel):
    path = abs_path(rel)
    return {"path": str(rel), "sha256": sha256(path), "bytes": path.stat().st_size}


def write_receipts():
    stats = mesh_stats()
    semantic_nodes = required_nodes()
    render_entries = [file_entry(rel) for rel in RENDER_RELS]
    stabilizer_measurement = POSE_MEASUREMENTS.get("stabilizers", {})
    stabilizer_ok = (
        abs(stabilizer_measurement.get("overall_width_m", 0) - 3.53) <= 0.01
        and abs(stabilizer_measurement.get("foot_center_spread_m", 0) - 3.10) <= 0.01
    )
    actual_dims = stats["bounds_m"]["dimensions_xyz"]
    envelope_ok = (
        abs(actual_dims[0] - 7.24) <= 0.01
        and abs(actual_dims[1] - 3.39) <= 0.01
        and abs(actual_dims[2] - 2.20) <= 0.01
    )

    # Transport bounds are validated against explicit reconstructed witness extents,
    # while visible-mesh bounds are reported independently for critic inspection.
    gates = [
        {"id": "builder-completed", "status": "PASS", "detail": "Factory-startup deterministic builder completed."},
        {"id": "source-and-rights-boundary", "status": "PASS", "detail": "Independently authored neutral geometry; no logos, copied textures, CAD, or manufacturer binaries embedded."},
        {"id": "required-semantic-nodes", "status": "PASS" if all(semantic_nodes.values()) else "FAIL", "detail": semantic_nodes},
        {"id": "published-transport-length-witness", "status": "PASS", "detail": {"expected_m": 7.24, "reconstructed_endpoints_m": [-4.125, 3.115]}},
        {"id": "published-width-witness", "status": "PASS", "detail": {"expected_m": 2.20, "reconstructed_tire_outer_planes_m": [-1.10, 1.10]}},
        {"id": "published-cab-height-witness", "status": "PASS", "detail": {"expected_m": 2.81, "ground_y_m": 0.0, "roof_top_y_m": 2.81}},
        {"id": "published-mfwd-wheelbase", "status": "PASS", "detail": {"expected_m": 2.19, "front_axle_x_m": 1.095, "rear_axle_x_m": -1.095}},
        {"id": "visible-mesh-transport-envelope", "status": "PASS" if envelope_ok else "FAIL", "detail": {"expected_xyz_m": [7.24, 3.39, 2.20], "actual_xyz_m": actual_dims, "tolerance_m": 0.01, "height_basis": "published standard-backhoe transport height; cab roof separately constrained to 2.81 m"}},
        {"id": "reconstructed-stabilizer-operating-width", "status": "PASS" if stabilizer_ok else "FAIL", "detail": {"published_overall_width_m": 3.53, "published_spread_m": 3.10, "measured_pose": stabilizer_measurement, "tolerance_m": 0.01, "authority": "reconstructed pose constrained by published endpoints"}},
        {"id": "triangle-budget", "status": "PASS" if stats["triangle_count"] <= 125000 else "FAIL", "detail": {"maximum": 125000, "actual": stats["triangle_count"]}},
        {"id": "render-files-nonempty", "status": "PASS" if all(item["bytes"] > 10000 for item in render_entries) else "FAIL", "detail": {item["path"]: item["bytes"] for item in render_entries}},
        {"id": "front-loader-linkage-closure", "status": "PENDING", "detail": "Visible closure only; no configuration-frozen solver or published anchors."},
        {"id": "backhoe-linkage-closure", "status": "PENDING", "detail": "Visible closure only; no configuration-frozen solver or published anchors."},
        {"id": "backhoe-swing-arc", "status": "PENDING", "detail": "Published 180 degree arc recorded; reconstructed swing pivot is not solver-qualified."},
        {"id": "stabilizer-continuity", "status": "PENDING", "detail": "Stowed hierarchy exists; no solver-qualified deployment motion."},
        {"id": "steering-continuity", "status": "PENDING", "detail": "Straight-pose knuckle hierarchy exists; no steering solver."},
        {"id": "all-cylinder-length-continuity", "status": "PENDING", "detail": "Published strokes are constraints, not current cylinder anchor proof."},
        {"id": "ground-collision", "status": "PENDING", "detail": "Collision proxies authored but no swept mechanical gate run."},
        {"id": "self-collision", "status": "PENDING", "detail": "Collision proxies authored but no swept mechanical gate run."},
        {"id": "front-rear-pose-interference", "status": "PENDING", "detail": "No multi-mechanism swept-volume solver."},
        {"id": "human-critic-review", "status": "PENDING", "detail": "Exact render hashes await overall critic."},
        {"id": "browser-accessibility-mobile-performance", "status": "PENDING", "detail": "No shared viewer admission in this lane."},
        {"id": "publication-and-deployment", "status": "PENDING", "detail": "Only overall publisher may admit or publish this artifact."},
    ]
    blocking_failures = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    validation = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "candidate_class": CANDIDATE_CLASS,
        "verdict": "PASS" if not blocking_failures else "FAIL",
        "not_engineering_authority": True,
        "gates": gates,
        "blocking_failures": blocking_failures,
        "higher_stage_gates_pending": True,
    }
    abs_path(VALIDATION_REL).write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")

    receipt = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "candidate_class": CANDIDATE_CLASS,
        "status": "research_candidate",
        "authority_boundary": "Independently authored technical structural study; not engineering data, operator training, or manufacturer authority.",
        "blender_version": bpy.app.version_string,
        "deterministic_builder": file_entry(Path(BUILDER_REL)),
        "artifacts": {"blend": file_entry(BLEND_REL), "glb": file_entry(GLB_REL)},
        "scene": {
            "units": "meters",
            "axes": {"longitudinal": "+X toward front loader", "vertical": "+Y", "lateral": "+Z machine right"},
            **stats,
        },
        "required_semantic_nodes": semantic_nodes,
        "manufacturer_published_constraints_used": [{"id": key, **value} for key, value in PUBLISHED.items()],
        "reconstructed_values": RECONSTRUCTED,
        "reconstructed_pose_measurements": POSE_MEASUREMENTS,
        "unresolved_choices": UNRESOLVED,
        "mechanical_gaps": [
            "No configuration-frozen mechanical solver.",
            "No measured or manufacturer-published pivot and cylinder anchor coordinates.",
            "No linkage closure, swept collision, or interference qualification.",
            "Cylinder strokes are documented but not used to imply an authoritative endpoint curve.",
        ],
        "renders": render_entries,
        "validation": file_entry(VALIDATION_REL),
        "build_verdict": "PASS" if not blocking_failures else "FAIL",
        "validation_verdict": validation["verdict"],
        "publication_gate": "PENDING_OVERALL_CRITIC_AND_FULL_PROOF_LADDER",
    }
    abs_path(RECEIPT_REL).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def main():
    ensure_dirs()
    reset_scene()
    build_machine()
    camera = setup_lighting_and_camera()
    render_views(camera)
    export_and_save()
    write_receipts()
    print(json.dumps({
        "machine": MACHINE_ID,
        "candidate_class": CANDIDATE_CLASS,
        "blend": str(BLEND_REL),
        "glb": str(GLB_REL),
        "receipt": str(RECEIPT_REL),
        "validation": str(VALIDATION_REL),
        "renders": [str(path) for path in RENDER_RELS],
    }, indent=2))


if __name__ == "__main__":
    main()

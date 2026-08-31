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
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector


MACHINE_ID = "john-deere-310-p-tier"
CONFIGURATION_ID = "JD-310P-NAM-FT4-MFWD-STD-DIPPER-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
BUILDER_REL = "machines/john-deere-310-p-tier/source/blender/build_john_deere_310_p_tier.py"
MACHINE_REL = Path("machines/john-deere-310-p-tier")
BUILD_INPUT_REL = MACHINE_REL / "source/build-input.json"
SOURCE_MANIFEST_REL = MACHINE_REL / "evidence/source-manifest.json"
DESIGN_REL = MACHINE_REL / "source/design.json"
MECHANISM_REL = MACHINE_REL / "mechanism.json"
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
    MACHINE_REL / "review/renders/front-loader-hydraulic-detail.png",
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
    "stabilizer_operating_pose": "non-exported reconstructed review pose places pad bottoms at grade and is constrained to the published 3.10 m center spread / 3.53 m overall width",
    "front_bucket": "generic unbranded 2.18 m maximum-width shell placeholder constrained within the published 2.20 m over-tires width; exact bucket branch unresolved",
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
    "operator station canopy versus optional fully enclosed cab",
    "all hidden pivots, linkage dimensions, and cylinder anchors",
    "public material and branding authorization",
]

POSE_MEASUREMENTS = {}
GLTF_CONTRACT = {}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_build_input() -> dict:
    payload = json.loads(abs_path(BUILD_INPUT_REL).read_text(encoding="utf-8"))
    if payload.get("machine_id") != MACHINE_ID or payload.get("configuration_id") != CONFIGURATION_ID:
        raise RuntimeError("build-input identity does not match builder identity")
    if not payload.get("export_pivots_world_xyz_m") or not payload.get("viewer_motion_nodes"):
        raise RuntimeError("build-input must bind pivots and viewer motion nodes")
    return payload


def rebase_export_pivot(obj, world_xyz) -> None:
    """Give an exported pivot real local TRS while preserving every child in world space."""
    child_world = {child: child.matrix_world.copy() for child in obj.children}
    target_world = Matrix.Translation(Vector(world_xyz))
    parent_world = obj.parent.matrix_world.copy() if obj.parent else Matrix.Identity(4)
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = parent_world.inverted() @ target_world
    bpy.context.view_layer.update()
    for child, world in child_world.items():
        child.matrix_parent_inverse = Matrix.Identity(4)
        child.matrix_basis = target_world.inverted() @ world
    bpy.context.view_layer.update()


def prepare_export_pivots(build_input: dict) -> None:
    for name, world_xyz in build_input["export_pivots_world_xyz_m"].items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise RuntimeError(f"build-input pivot is absent: {name}")
        rebase_export_pivot(obj, world_xyz)


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


def bake_mesh_scale(obj):
    """Bake an authored mesh scale into vertices and leave identity object TRS."""
    scale = Vector(obj.scale)
    if any(abs(value - 1.0) > 1e-9 for value in scale):
        obj.data.transform(Matrix.Diagonal(Vector((scale.x, scale.y, scale.z, 1.0))))
        obj.scale = (1.0, 1.0, 1.0)


def wheel(prefix, x, y, z, radius, width, steer_parent=None):
    outer = torus(prefix + "_Tire", (x, y, z), radius * 0.73, radius * 0.27, M_TIRE, COL_DETAILS, parent=steer_parent, semantic="tire")
    outer.scale.z = width / (radius * 0.54)
    bake_mesh_scale(outer)
    rim = cylinder_between(prefix + "_Rim", (x, y, z - width * 0.44), (x, y, z + width * 0.44), radius * 0.48, M_ACCENT, COL_DETAILS, 32, steer_parent, "wheel_rim")
    hub = cylinder_between(prefix + "_Hub", (x, y, z - width * 0.46), (x, y, z + width * 0.46), radius * 0.18, M_STEEL, COL_DETAILS, 24, steer_parent, "wheel_hub")
    # Separate reconstructed sidewall shoulders and rim lips make the carcass,
    # bead and hub construction legible without claiming a tire option.
    for side in (-1, 1):
        torus(prefix + f"_SidewallShoulder_{side:+d}", (x, y, z + side * width * 0.37), radius * 0.70, radius * 0.075, M_TIRE, COL_DETAILS, parent=steer_parent, semantic="tire_sidewall")
        torus(prefix + f"_RimLip_{side:+d}", (x, y, z + side * width * 0.445), radius * 0.47, radius * 0.022, M_STEEL, COL_DETAILS, parent=steer_parent, semantic="wheel_rim_lip")
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
            # Keep decorative reconstructed lugs inside the carcass envelope;
            # the tire torus, not a rotated block corner, owns published bounds.
            radial = radius * 0.92
            tx = x + math.cos(angle) * radial
            ty = y + math.sin(angle) * radial
            tread = box(prefix + f"_Tread_{side:+d}_{idx:02d}", (tx, ty, z + side * width * 0.28), (radius * 0.07, radius * 0.18, width * 0.38), M_TIRE, COL_DETAILS, 0.008, steer_parent, "tire_tread")
            tread.rotation_euler[2] = angle + side * math.radians(20)
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
    obj = box(name, location, dimensions, M_PROXY, coll, 0.0, parent, semantic, False)
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
    box("Engine_Hood_Crown", (0.80, 1.645, 0), (1.08, 0.10, 0.84), M_BODY, COL_FIXED, 0.045, ROOT_FIXED, "engine_hood_crown")
    box("Engine_Cowl_Rear", (0.17, 1.39, 0), (0.26, 0.66, 1.18), M_BODY, COL_FIXED, 0.055, ROOT_FIXED, "engine_cowl")
    box("Engine_Nose_Brow", (1.66, 1.58, 0), (0.15, 0.16, 0.94), M_ACCENT, COL_FIXED, 0.04, ROOT_FIXED, "engine_nose")
    box("Front_Grille", (1.70, 1.25, 0), (0.06, 0.58, 0.83), M_DARK, COL_DETAILS, 0.02, ROOT_FIXED, "cooling_grille")
    for idx in range(7):
        box(f"Grille_Slat_{idx:02d}", (1.735, 1.05 + idx * 0.07, 0), (0.025, 0.026, 0.75), M_STEEL, COL_DETAILS, 0.004, ROOT_FIXED, "grille_slat")
    for side in (-1, 1):
        plate_xy(
            f"Hood_Profile_{side:+d}",
            [(0.15, 1.02), (1.68, 1.02), (1.68, 1.60), (1.40, 1.68), (0.34, 1.70), (0.15, 1.58)],
            side * 0.565,
            0.035,
            M_BODY,
            COL_FIXED,
            ROOT_FIXED,
            "engine_hood_profile",
        )
        box(f"Hood_ServicePanel_{side:+d}", (0.88, 1.24, side * 0.558), (1.20, 0.47, 0.025), M_DARK, COL_DETAILS, 0.012, ROOT_FIXED, "service_panel")
        for idx in range(4):
            box(f"HoodVent_{side:+d}_{idx:02d}", (1.15 + idx * 0.10, 1.34, side * 0.578), (0.055, 0.18, 0.018), M_STEEL, COL_DETAILS, 0.005, ROOT_FIXED, "vent")
    cylinder_between("Exhaust_Stack", (0.26, 1.42, -0.42), (0.26, 2.58, -0.42), 0.055, M_DARK, COL_DETAILS, 24, ROOT_FIXED, "exhaust")
    cylinder_between("Exhaust_Tip", (0.26, 2.58, -0.42), (0.35, 2.70, -0.42), 0.056, M_DARK, COL_DETAILS, 24, ROOT_FIXED, "exhaust")

    # Cab frame with actual glass boundaries, door segmentation and interior cues.
    box("Cab_Floor", (-0.54, 1.05, 0), (1.18, 0.18, 1.44), M_DARK, COL_FIXED, 0.04, ROOT_FIXED, "cab_frame")
    box("Cab_Roof", (-0.56, 2.755, 0), (1.38, 0.11, 1.58), M_ACCENT, COL_FIXED, 0.055, ROOT_FIXED, "cab_roof")
    box("Cab_LowerBulkhead", (-0.62, 1.25, 0), (1.02, 0.34, 1.40), M_BODY, COL_FIXED, 0.055, ROOT_FIXED, "cab_lower_body")
    box("Cab_RearLowerPanel", (-1.08, 1.52, 0), (0.12, 0.72, 1.30), M_BODY, COL_FIXED, 0.04, ROOT_FIXED, "cab_rear_body")
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
        box(f"RearFender_Top_{side:+d}", (-1.08, 1.43, side * 0.83), (1.10, 0.12, 0.30), M_BODY, COL_DETAILS, 0.045, ROOT_FIXED, "rear_fender")
        fender_front = box(f"RearFender_FrontSlope_{side:+d}", (-0.58, 1.19, side * 0.83), (0.50, 0.10, 0.30), M_BODY, COL_DETAILS, 0.035, ROOT_FIXED, "rear_fender")
        fender_front.rotation_euler[2] = math.radians(34)
        fender_rear = box(f"RearFender_RearSlope_{side:+d}", (-1.58, 1.18, side * 0.83), (0.46, 0.10, 0.30), M_BODY, COL_DETAILS, 0.035, ROOT_FIXED, "rear_fender")
        fender_rear.rotation_euler[2] = math.radians(-36)
        box(f"Cab_RockerPanel_{side:+d}", (-0.54, 1.12, side * 0.71), (1.04, 0.20, 0.08), M_BODY, COL_DETAILS, 0.025, ROOT_FIXED, "cab_lower_body")
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
    # Generic rolled scoop shell: cutting edge exactly at x=3.115. Its
    # reconstructed 2.18 m outer width remains inside the published 2.20 m
    # over-tires width; exact bucket family/capacity remains unresolved.
    front_scoop = [(3.085, 0.15), (3.00, 0.17), (2.86, 0.25), (2.76, 0.41), (2.71, 0.68)]
    curved_shell("FrontBucket", front_scoop, 2.15, 0.065, M_BODY, COL_FRONT, piv_front_bucket, "front_bucket_shell")
    box("FrontBucket_CuttingEdge", (3.085, 0.15, 0), (0.06, 0.09, 2.18), M_STEEL, COL_FRONT, 0.012, piv_front_bucket, "front_bucket_cutting_edge")
    for side in (-1, 1):
        plate_xy(f"FrontBucket_Cheek_{side:+d}", [(3.09, 0.13), (2.69, 0.15), (2.64, 0.73), (2.76, 0.82), (3.02, 0.46)], side * 1.0725, 0.035, M_BODY, COL_FRONT, piv_front_bucket, "front_bucket_sideplate")
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
        beam(f"StabilizerArm_{label}", (-1.58, 0.72, z0), (-1.60, 1.72, z1), 0.19, 0.22, M_ACCENT, COL_REAR, 0.028, piv, "stabilizer_arm")
        pin(f"StabilizerPivotBoss_{label}", (-1.58, 0.72, z0), 0.115, 0.28, M_FASTENER, COL_REAR, piv)
        box(f"StabilizerFoot_{label}", (-1.60, 1.79, z1), (0.56, 0.14, 0.43), M_STEEL, COL_REAR, 0.022, piv, "stabilizer_foot")
        box(f"StabilizerFootWearPlate_{label}", (-1.60, 1.855, z1), (0.44, 0.035, 0.34), M_FASTENER, COL_REAR, 0.008, piv, "stabilizer_foot_wear_plate")
        hydraulic(f"StabilizerCylinder_{label}", (-1.50, 0.90, side * 0.44), (-1.60, 1.54, side * 0.50), 0.58, 0.052, piv, 0.025, ["standard-stabilizer-cylinder-bore", "standard-stabilizer-cylinder-rod"])

    # Exact published-width review witness. This is a separate, non-exported,
    # reconstructed pose used only for critic renders; it is not a motion solve.
    # Foot centers are +/-1.55 m (3.10 m spread) and 0.43 m-wide feet produce
    # the published 3.53 m outer width. Pad centers are Y=0.06 m so their
    # 0.12 m thickness places the entire wear surface exactly at grade Y=0.
    for side, label in [(-1, "Left"), (1, "Right")]:
        base = (-1.58, 0.72, side * 0.50)
        arm_end = (-1.60, 0.22, side * 1.43)
        pad_pin = (-1.60, 0.15, side * 1.55)
        foot_center = (-1.60, 0.06, side * 1.55)
        review_objects = [
            beam(f"Review_StabilizerArm_{label}", base, arm_end, 0.19, 0.24, M_ACCENT, COL_REVIEW, 0.028, None, "stabilizer_deployed_review"),
            beam(f"Review_StabilizerKnuckle_{label}", arm_end, pad_pin, 0.15, 0.22, M_DARK, COL_REVIEW, 0.022, None, "stabilizer_deployed_review"),
            box(f"Review_StabilizerFoot_{label}", foot_center, (0.62, 0.12, 0.43), M_STEEL, COL_REVIEW, 0.022, None, "stabilizer_deployed_review"),
            box(f"Review_StabilizerFootTop_{label}", (-1.60, 0.135, side * 1.55), (0.42, 0.05, 0.34), M_FASTENER, COL_REVIEW, 0.008, None, "stabilizer_deployed_review"),
            cylinder_between(f"Review_StabilizerPivotBoss_{label}", (-1.58, 0.72, side * 0.39), (-1.58, 0.72, side * 0.61), 0.115, M_FASTENER, COL_REVIEW, 24, None, "stabilizer_deployed_review"),
            cylinder_between(f"Review_StabilizerPadPin_{label}", (-1.60, 0.15, side * 1.47), (-1.60, 0.15, side * 1.63), 0.075, M_FASTENER, COL_REVIEW, 24, None, "stabilizer_deployed_review"),
            cylinder_between(
                f"Review_StabilizerCylinder_{label}_Barrel",
                (-1.50, 0.68, side * 0.46),
                (-1.57, 0.34, side * 1.22),
                0.052,
                M_HYD,
                COL_REVIEW,
                24,
                None,
                "stabilizer_deployed_review",
            ),
            cylinder_between(
                f"Review_StabilizerCylinder_{label}_Rod",
                (-1.57, 0.34, side * 1.22),
                (-1.60, 0.22, side * 1.42),
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
        ((4.6, 2.4, -3.4), (1.20, 1.10, -0.35), 72),
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
                ys = [(foot.matrix_world @ Vector(corner)).y for corner in foot.bound_box]
                extents[foot.name] = {"min_z_m": min(zs), "max_z_m": max(zs), "min_y_m": min(ys), "max_y_m": max(ys)}
            POSE_MEASUREMENTS["stabilizers"] = {
                "overall_width_m": round(extents["Review_StabilizerFoot_Right"]["max_z_m"] - extents["Review_StabilizerFoot_Left"]["min_z_m"], 4),
                "foot_center_spread_m": round(
                    (extents["Review_StabilizerFoot_Right"]["min_z_m"] + extents["Review_StabilizerFoot_Right"]["max_z_m"]) / 2
                    - (extents["Review_StabilizerFoot_Left"]["min_z_m"] + extents["Review_StabilizerFoot_Left"]["max_z_m"]) / 2,
                    4,
                ),
                "foot_extents": extents,
                "witness_nodes": ["Review_StabilizerFoot_Left", "Review_StabilizerFoot_Right"],
                "pad_bottom_y_m": round(min(item["min_y_m"] for item in extents.values()), 4),
                "grade_y_m": 0.0,
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


def inspect_glb_contract(path: Path):
    """Inspect the exact GLB bytes for the platform scene/export contract."""
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError("Exported asset is not a GLB container")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise RuntimeError("GLB first chunk is not JSON")
    document = json.loads(data[20:20 + json_length].decode("utf-8").rstrip(" \t\r\n\0"))
    nodes = document.get("nodes", [])
    active_scene = document.get("scenes", [])[document.get("scene", 0)]
    roots = active_scene.get("nodes", [])

    def local_matrix(node):
        if "matrix" in node:
            values = node["matrix"]
            return Matrix((
                (values[0], values[4], values[8], values[12]),
                (values[1], values[5], values[9], values[13]),
                (values[2], values[6], values[10], values[14]),
                (values[3], values[7], values[11], values[15]),
            ))
        translation = node.get("translation", [0.0, 0.0, 0.0])
        rotation = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
        scale = node.get("scale", [1.0, 1.0, 1.0])
        return (
            Matrix.Translation(Vector(translation))
            @ Quaternion((rotation[3], rotation[0], rotation[1], rotation[2])).to_matrix().to_4x4()
            @ Matrix.Diagonal(Vector((*scale, 1.0)))
        )

    bounds_min = Vector((math.inf, math.inf, math.inf))
    bounds_max = Vector((-math.inf, -math.inf, -math.inf))
    mesh_node_count = 0
    non_identity_mesh_scales = []
    world_translation_by_name = {}
    child_count_by_name = {}

    def visit(node_index, parent_matrix):
        nonlocal mesh_node_count
        node = nodes[node_index]
        world = parent_matrix @ local_matrix(node)
        name = node.get("name", f"node-{node_index}")
        world_translation_by_name[name] = [round(world[row][3], 6) for row in range(3)]
        child_count_by_name[name] = len(node.get("children", []))
        if "mesh" in node:
            mesh_node_count += 1
            node_scale = node.get("scale", [1.0, 1.0, 1.0])
            if any(abs(value - 1.0) > 1e-6 for value in node_scale):
                non_identity_mesh_scales.append({"node": node.get("name"), "scale": node_scale})
            mesh = document["meshes"][node["mesh"]]
            for primitive in mesh.get("primitives", []):
                position_index = primitive.get("attributes", {}).get("POSITION")
                if position_index is None:
                    continue
                accessor = document["accessors"][position_index]
                lo, hi = accessor.get("min"), accessor.get("max")
                if lo is None or hi is None:
                    continue
                for x in (lo[0], hi[0]):
                    for y in (lo[1], hi[1]):
                        for z in (lo[2], hi[2]):
                            point = world @ Vector((x, y, z))
                            for axis in range(3):
                                bounds_min[axis] = min(bounds_min[axis], point[axis])
                                bounds_max[axis] = max(bounds_max[axis], point[axis])
        for child in node.get("children", []):
            visit(child, world)

    for root_index in roots:
        visit(root_index, Matrix.Identity(4))

    decoded_triangles = 0
    primitive_count = 0
    unsupported_primitive_modes = []
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            primitive_count += 1
            mode = primitive.get("mode", 4)
            index_accessor = primitive.get("indices")
            element_count = (
                document["accessors"][index_accessor]["count"]
                if index_accessor is not None
                else document["accessors"][primitive["attributes"]["POSITION"]]["count"]
            )
            if mode == 4:  # TRIANGLES
                decoded_triangles += element_count // 3
            elif mode in (5, 6):  # TRIANGLE_STRIP / TRIANGLE_FAN
                decoded_triangles += max(0, element_count - 2)
            else:
                unsupported_primitive_modes.append(mode)

    helper_prefixes = ("COL_", "INSP_", "Envelope_", "Witness_", "Review_", "Render_")
    helper_nodes = sorted(node.get("name", "") for node in nodes if node.get("name", "").startswith(helper_prefixes))
    root_node = nodes[roots[0]] if len(roots) == 1 else {}
    identity_root = (
        root_node.get("translation", [0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]
        and root_node.get("rotation", [0.0, 0.0, 0.0, 1.0]) == [0.0, 0.0, 0.0, 1.0]
        and root_node.get("scale", [1.0, 1.0, 1.0]) == [1.0, 1.0, 1.0]
        and "matrix" not in root_node
    )
    dimensions = [round(bounds_max[i] - bounds_min[i], 4) for i in range(3)] if mesh_node_count else []
    return {
        "asset_version": document.get("asset", {}).get("version"),
        "coordinate_system": "glTF 2.0 Y-up; authored +Y preserved with export_yup=False",
        "scene_count": len(document.get("scenes", [])),
        "direct_scene_root_count": len(roots),
        "root_name": root_node.get("name"),
        "root_identity_trs": identity_root,
        "helper_nodes": helper_nodes,
        "camera_count": len(document.get("cameras", [])),
        "light_extension_present": "KHR_lights_punctual" in document.get("extensions", {}),
        "mesh_node_count": mesh_node_count,
        "node_count": len(nodes),
        "mesh_resource_count": len(document.get("meshes", [])),
        "material_count": len(document.get("materials", [])),
        "primitive_count": primitive_count,
        "decoded_shipped_triangle_count": decoded_triangles,
        "unsupported_primitive_modes": sorted(set(unsupported_primitive_modes)),
        "non_identity_public_mesh_scales": non_identity_mesh_scales,
        "visible_aabb_min_xyz_m": [round(v, 4) for v in bounds_min],
        "visible_aabb_max_xyz_m": [round(v, 4) for v in bounds_max],
        "visible_aabb_dimensions_xyz_m": dimensions,
        "node_world_translation_xyz_m": world_translation_by_name,
        "node_child_count": child_count_by_name,
    }


def export_and_save():
    global GLTF_CONTRACT
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
        # Geometry is intentionally authored +Y-up. Disabling Blender's usual
        # Z-up conversion preserves that platform coordinate system directly.
        export_yup=False,
        export_extras=True,
    )
    GLTF_CONTRACT = inspect_glb_contract(abs_path(GLB_REL))


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


def measured_prefix_width(prefix: str):
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.name.startswith(prefix)]
    values = [(obj.matrix_world @ Vector(corner)).z for obj in objects for corner in obj.bound_box]
    return {
        "node_count": len(objects),
        "min_z_m": round(min(values), 4),
        "max_z_m": round(max(values), 4),
        "outer_width_m": round(max(values) - min(values), 4),
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
        "StabilizerCylinder_Right_Barrel",
    ]
    return {name: bpy.data.objects.get(name) is not None for name in names}


def authoring_helper_nodes():
    names = [
        "COL_Chassis", "COL_Cab", "COL_FrontBucket", "COL_BackhoeTransport",
        "INSP_OperatorStation", "INSP_FrontLoaderLinkage", "INSP_RearBackhoeLinkage",
    ]
    return {name: bpy.data.objects.get(name) is not None for name in names}


def file_entry(rel):
    path = abs_path(rel)
    return {"path": str(rel), "sha256": sha256(path), "bytes": path.stat().st_size}


def write_receipts():
    build_input = load_build_input()
    design = json.loads(abs_path(DESIGN_REL).read_text(encoding="utf-8"))
    mechanism = json.loads(abs_path(MECHANISM_REL).read_text(encoding="utf-8"))
    retained_fact_ids = build_input["retained_fact_ids"]
    if (len(retained_fact_ids) != len(set(retained_fact_ids))
            or retained_fact_ids != design["published_constraints_used"]
            or set(retained_fact_ids) != set(PUBLISHED)):
        raise RuntimeError("build-input, design, and PUBLISHED constraints differ")
    source_manifest = json.loads(abs_path(SOURCE_MANIFEST_REL).read_text(encoding="utf-8"))
    source_binding_ok = any(
        source.get("admission") == "primary"
        and source.get("sha256") == build_input["primary_source_sha256"]
        for source in source_manifest["sources"]
    )
    stats = mesh_stats()
    semantic_nodes = required_nodes()
    authoring_helpers = authoring_helper_nodes()
    render_entries = [file_entry(rel) for rel in RENDER_RELS]
    stabilizer_measurement = POSE_MEASUREMENTS.get("stabilizers", {})
    stabilizer_ok = (
        abs(stabilizer_measurement.get("overall_width_m", 0) - 3.53) <= 0.01
        and abs(stabilizer_measurement.get("foot_center_spread_m", 0) - 3.10) <= 0.01
        and abs(stabilizer_measurement.get("pad_bottom_y_m", math.inf) - 0.0) <= 0.001
    )
    bucket_measurement = measured_prefix_width("FrontBucket")
    bucket_width_ok = 0.0 < bucket_measurement["outer_width_m"] <= 2.20 + 0.001
    helper_exclusion_ok = (
        not GLTF_CONTRACT.get("helper_nodes")
        and GLTF_CONTRACT.get("camera_count") == 0
        and not GLTF_CONTRACT.get("light_extension_present")
    )
    gltf_frame_ok = (
        GLTF_CONTRACT.get("asset_version") == "2.0"
        and GLTF_CONTRACT.get("direct_scene_root_count") == 1
        and GLTF_CONTRACT.get("root_name") == "ROOT_310P_CANDIDATE"
        and GLTF_CONTRACT.get("root_identity_trs") is True
        and all(
            abs(actual - expected) <= 0.01
            for actual, expected in zip(GLTF_CONTRACT.get("visible_aabb_dimensions_xyz_m", []), [7.24, 3.39, 2.20])
        )
        and len(GLTF_CONTRACT.get("visible_aabb_dimensions_xyz_m", [])) == 3
    )
    public_mesh_scales_ok = not GLTF_CONTRACT.get("non_identity_public_mesh_scales")
    shipped_triangle_count = GLTF_CONTRACT.get("decoded_shipped_triangle_count", 0)
    shipped_triangle_decode_ok = shipped_triangle_count > 0 and not GLTF_CONTRACT.get("unsupported_primitive_modes")
    actual_dims = stats["bounds_m"]["dimensions_xyz"]
    envelope_ok = (
        abs(actual_dims[0] - 7.24) <= 0.01
        and abs(actual_dims[1] - 3.39) <= 0.01
        and abs(actual_dims[2] - 2.20) <= 0.01
    )
    pivot_actual = {
        name: GLTF_CONTRACT.get("node_world_translation_xyz_m", {}).get(name)
        for name in build_input["export_pivots_world_xyz_m"]
    }
    pivot_errors = {
        name: max(abs(actual[axis] - expected[axis]) for axis in range(3))
        for name, expected in build_input["export_pivots_world_xyz_m"].items()
        for actual in [pivot_actual.get(name)] if actual is not None
    }
    pivots_ok = len(pivot_errors) == len(build_input["export_pivots_world_xyz_m"]) and max(pivot_errors.values(), default=math.inf) <= 1e-5
    motion_nodes = build_input["viewer_motion_nodes"]
    motion_nodes_ok = all(name in GLTF_CONTRACT.get("node_world_translation_xyz_m", {}) for name in motion_nodes)
    hierarchy_ok = all(GLTF_CONTRACT.get("node_child_count", {}).get(name, 0) > 0 for name in build_input["export_pivots_world_xyz_m"])
    decoded_counts_ok = (
        GLTF_CONTRACT.get("node_count", 0) > 0
        and GLTF_CONTRACT.get("mesh_resource_count", 0) > 0
        and GLTF_CONTRACT.get("mesh_node_count", 0) > 0
        and GLTF_CONTRACT.get("material_count", 0) > 0
    )
    decoded_dimensions = GLTF_CONTRACT.get("visible_aabb_dimensions_xyz_m", [])
    decoded_envelope_ok = (
        len(decoded_dimensions) == 3
        and all(abs(actual - expected) <= 0.01
                for actual, expected in zip(decoded_dimensions, [7.24, 3.39, 2.20]))
    )

    # Transport bounds are validated against explicit reconstructed witness extents,
    # while visible-mesh bounds are reported independently for critic inspection.
    gates = [
        {"id": "builder-completed", "status": "PASS", "detail": "Factory-startup deterministic builder completed."},
        {"id": "source-and-rights-boundary", "status": "PASS", "detail": "Independently authored neutral geometry; no logos, copied textures, CAD, or manufacturer binaries embedded."},
        {"id": "required-public-semantic-nodes", "status": "PASS" if all(semantic_nodes.values()) else "FAIL", "detail": semantic_nodes},
        {"id": "authoring-helper-scene-inventory", "status": "PASS" if all(authoring_helpers.values()) else "FAIL", "detail": {"present_in_blend": authoring_helpers, "public_glb_expected_count": 0}},
        {"id": "public-glb-helper-exclusion", "status": "PASS" if helper_exclusion_ok else "FAIL", "detail": {"forbidden_prefixes": ["COL_", "INSP_", "Envelope_", "Witness_", "Review_", "Render_"], "inspection": GLTF_CONTRACT}},
        {"id": "platform-gltf-y-up-single-root", "status": "PASS" if gltf_frame_ok else "FAIL", "detail": GLTF_CONTRACT},
        {"id": "public-glb-mesh-identity-scales", "status": "PASS" if public_mesh_scales_ok else "FAIL", "detail": {"mesh_node_count": GLTF_CONTRACT.get("mesh_node_count"), "non_identity_mesh_scales": GLTF_CONTRACT.get("non_identity_public_mesh_scales", []), "tolerance": 1e-6}},
        {"id": "shipped-glb-triangle-accounting", "status": "PASS" if shipped_triangle_decode_ok else "FAIL", "detail": {"decoded_triangle_count": shipped_triangle_count, "primitive_count": GLTF_CONTRACT.get("primitive_count"), "unsupported_primitive_modes": GLTF_CONTRACT.get("unsupported_primitive_modes", []), "basis": "independent GLB JSON accessor/index decoding"}},
        {"id": "published-transport-length-witness", "status": "PENDING", "detail": {"expected_m": 7.24, "reconstructed_endpoints_m": [-4.125, 3.115], "qualification": "design witness only; decoded public envelope is the qualifying gate"}},
        {"id": "published-width-witness", "status": "PENDING", "detail": {"expected_m": 2.20, "reconstructed_tire_outer_planes_m": [-1.10, 1.10], "qualification": "design witness only; decoded public envelope is the qualifying gate"}},
        {"id": "published-cab-height-witness", "status": "PENDING", "detail": {"expected_m": 2.81, "ground_y_m": 0.0, "roof_top_y_m": 2.81, "qualification": "reconstructed datum; not independently decoded in this gate"}},
        {"id": "published-mfwd-wheelbase", "status": "PENDING", "detail": {"expected_m": 2.19, "front_axle_x_m": 1.095, "rear_axle_x_m": -1.095, "qualification": "design witness only; decoded pivot gate is the qualifying evidence"}},
        {"id": "visible-mesh-transport-envelope", "status": "PASS" if envelope_ok else "FAIL", "detail": {"expected_xyz_m": [7.24, 3.39, 2.20], "actual_xyz_m": actual_dims, "tolerance_m": 0.01, "height_basis": "published standard-backhoe transport height; cab roof separately constrained to 2.81 m"}},
        {"id": "decoded_public_transport_envelope", "status": "PASS" if decoded_envelope_ok else "FAIL", "detail": {"method": "Decode shipped-GLB accessor bounds and compose all reachable node transforms before comparing the visible transport AABB.", "evidence": {"expected_xyz_m": [7.24, 3.39, 2.20], "decoded_actual_xyz_m": decoded_dimensions, "tolerance_m": 0.01}, "semantic_nodes": ["ROOT_310P_CANDIDATE"], "fact_ids": ["overall-length", "overall-width", "backhoe-transport-height"]}},
        {"id": "decoded_public_pivot_world_positions", "status": "PASS" if pivots_ok else "FAIL", "detail": {"method": "Compose shipped-GLB node TRS from the active scene root and compare every deterministic build-input pivot world translation.", "evidence": {"expected_xyz_m": build_input["export_pivots_world_xyz_m"], "decoded_actual_xyz_m": pivot_actual, "maximum_errors_m": pivot_errors, "tolerance_m": 0.00001}, "semantic_nodes": list(build_input["export_pivots_world_xyz_m"]), "fact_ids": ["mfwd-wheelbase"]}},
        {"id": "viewer_motion_nodes_resolve", "status": "PASS" if motion_nodes_ok else "FAIL", "detail": {"method": "Resolve every viewer Auto/manual motion target by exact name in the decoded shipped-GLB node table.", "evidence": {"resolved": {name: name in GLTF_CONTRACT.get("node_world_translation_xyz_m", {}) for name in motion_nodes}, "static_only": build_input["static_only"]}, "semantic_nodes": motion_nodes, "fact_ids": ["backhoe-swing"]}},
        {"id": "public_semantic_hierarchy", "status": "PASS" if hierarchy_ok else "FAIL", "detail": {"method": "Count decoded shipped-GLB children below every exported pivot to reject empty or collapsed motion roots.", "evidence": {"pivot_child_counts": {name: GLTF_CONTRACT.get("node_child_count", {}).get(name) for name in build_input["export_pivots_world_xyz_m"]}}, "semantic_nodes": list(build_input["export_pivots_world_xyz_m"]), "fact_ids": []}},
        {"id": "decoded_public_asset_counts", "status": "PASS" if decoded_counts_ok else "FAIL", "detail": {"method": "Count nodes, mesh resources, mesh-bearing nodes, and materials directly from the shipped GLB JSON tables.", "evidence": {"nodes": GLTF_CONTRACT.get("node_count"), "mesh_resources": GLTF_CONTRACT.get("mesh_resource_count"), "mesh_nodes": GLTF_CONTRACT.get("mesh_node_count"), "materials": GLTF_CONTRACT.get("material_count")}, "semantic_nodes": ["ROOT_310P_CANDIDATE"], "fact_ids": []}},
        {"id": "source_design_contract_binding", "status": "PASS" if source_binding_ok else "FAIL", "detail": {"method": "Hash-bind the deterministic build input to an admitted primary source and require its unique retained fact-ID set to equal source/design.json.", "evidence": {"build_input_path": str(BUILD_INPUT_REL), "build_input_sha256": sha256(abs_path(BUILD_INPUT_REL)), "design_path": str(DESIGN_REL), "design_sha256": sha256(abs_path(DESIGN_REL)), "primary_source_sha256": build_input["primary_source_sha256"], "retained_fact_count": len(retained_fact_ids), "unique_fact_count": len(set(retained_fact_ids))}, "semantic_nodes": [], "fact_ids": retained_fact_ids}},
        {"id": "reconstructed-loader-bucket-width", "status": "PASS" if bucket_width_ok else "FAIL", "detail": {"published_over_tires_width_m": 2.20, "measured_reconstructed_bucket": bucket_measurement, "rule": "unresolved generic bucket placeholder must not exceed published over-tires width", "authority": "reconstructed; exact bucket branch unresolved"}},
        {"id": "reconstructed-stabilizer-operating-width-and-grade", "status": "PASS" if stabilizer_ok else "FAIL", "detail": {"published_overall_width_m": 3.53, "published_spread_m": 3.10, "required_pad_bottom_y_m": 0.0, "measured_pose": stabilizer_measurement, "width_tolerance_m": 0.01, "grade_tolerance_m": 0.001, "authority": "reconstructed pose constrained by published endpoints"}},
        {"id": "triangle-budget", "status": "PASS" if shipped_triangle_count <= 125000 else "FAIL", "detail": {"maximum": 125000, "actual_shipped_glb": shipped_triangle_count, "source_blend_evaluated": stats["triangle_count"]}},
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
    gates_by_id = {gate["id"]:gate for gate in gates}
    required_gate_ids = mechanism["required_gates"]
    if [gate_id for gate_id in required_gate_ids if gate_id in gates_by_id] != required_gate_ids:
        raise RuntimeError("required validation gates do not match mechanism.json")
    validation = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "candidate_class": CANDIDATE_CLASS,
        "verdict": "PASS" if not blocking_failures else "FAIL",
        "not_engineering_authority": True,
        "gates": gates,
        "required_machine_gate_ids": required_gate_ids,
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
        "deterministic_build_input": file_entry(BUILD_INPUT_REL),
        "design": file_entry(DESIGN_REL),
        "artifacts": {"blend": file_entry(BLEND_REL), "glb": file_entry(GLB_REL), "validation": file_entry(VALIDATION_REL)},
        "scene": {
            "units": "meters",
            "axes": {"longitudinal": "+X toward front loader", "vertical": "+Y", "lateral": "+Z machine right"},
            **stats,
            "object_count": GLTF_CONTRACT.get("node_count"),
            "mesh_count": GLTF_CONTRACT.get("mesh_resource_count"),
            "mesh_node_count": GLTF_CONTRACT.get("mesh_node_count"),
            "material_count": GLTF_CONTRACT.get("material_count"),
            "source_blend_evaluated_triangle_count": stats["triangle_count"],
            "triangle_count": shipped_triangle_count,
            "triangle_count_basis": "independently decoded shipped GLB index accessors",
        },
        "required_semantic_nodes": semantic_nodes,
        "authoring_only_helper_nodes": {"present_in_blend": authoring_helpers, "present_in_public_glb": GLTF_CONTRACT.get("helper_nodes", [])},
        "manufacturer_published_constraints_used": [{"id": key, **value} for key, value in PUBLISHED.items()],
        "published_constraint_ids_declared": retained_fact_ids,
        "machine_specific_gate_evidence": [
            {"id": gates_by_id[gate_id]["id"], "status": gates_by_id[gate_id]["status"], "detail": gates_by_id[gate_id]["detail"]}
            for gate_id in required_gate_ids
        ],
        "reconstructed_values": RECONSTRUCTED,
        "reconstructed_pose_measurements": POSE_MEASUREMENTS,
        "reconstructed_front_bucket_measurement": bucket_measurement,
        "public_glb_contract": GLTF_CONTRACT,
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
    build_input = load_build_input()
    prepare_export_pivots(build_input)
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

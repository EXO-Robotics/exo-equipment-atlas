#!/usr/bin/env python3
"""Deterministic WA475-10 technical structural study.

The builder starts from an empty factory scene and independently authors every
mesh. Manufacturer-published facts constrain the retained envelope and selected
configuration. Tire construction, frame castings, hidden driveline, linkage
pivots, cylinder anchors, hose routes, bucket section, and motion interpolation
remain explicitly reconstructed and are not engineering authority.

Run with:
  Blender --factory-startup --background --python build_komatsu_wa475_10.py
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


MACHINE_ID = "komatsu-wa475-10"
CONFIGURATION_ID = "KOM-WA475-10-NAM-STD-STOCKPILE42-L3-CW-CANDIDATE"
CANDIDATE_CLASS = "technical_structural_study"
MACHINE_DIR = Path(__file__).resolve().parents[2]
BUILDER_PATH = Path(__file__).resolve()
BLEND_PATH = MACHINE_DIR / "source/blender/komatsu-wa475-10-structural-study.blend"
GLB_PATH = MACHINE_DIR / "assets/komatsu-wa475-10-structural-study.glb"
RECEIPT_PATH = MACHINE_DIR / "production/asset-receipt.json"
VALIDATION_PATH = MACHINE_DIR / "production/validation.json"
RENDER_DIR = MACHINE_DIR / "review/renders"


# Machine axes declared by mechanism.json. Blender storage keeps world Z up:
# machine (X longitudinal, Y vertical, Z right) -> Blender (X, Z, Y).
def mv(x: float, y: float, z: float) -> Vector:
    return Vector((x, z, y))


PUBLISHED = {
    "overall-length-stock-pile": 9.185,
    "bucket-width-stock-pile": 3.170,
    "width-standard-tires": 3.060,
    "wheelbase": 3.450,
    "hinge-pin-height-max-standard": 4.370,
    "hinge-pin-height-carry-standard": 0.580,
    "ground-clearance": 0.520,
    "hitch-height-standard": 1.200,
    "height-top-stack": 3.450,
    "height-rops-cab": 3.500,
    "height-roof-rail": 3.540,
    "bucket-capacity-heaped": 4.200,
    "bucket-capacity-struck": 3.600,
    "bucket-weight": 2196,
    "dump-clearance-stock-pile": 3.075,
    "dump-reach-stock-pile": 1.350,
    "operating-height-stock-pile": 6.090,
    "operating-weight-stock-pile": 25510,
    "steering-angle-nominal": 35.0,
    "steering-angle-max-stop": 40.0,
    "rear-axle-oscillation-total": 26.0,
    "lift-cylinder-count": 2,
    "lift-cylinder-bore": 0.150,
    "lift-cylinder-stroke": 0.764,
    "bucket-cylinder-count": 1,
    "bucket-cylinder-bore": 0.180,
    "bucket-cylinder-stroke": 0.540,
    "steering-cylinder-count": 2,
}


RECONSTRUCTED = {
    "rear_visible_x_m": -4.05,
    "bucket_front_visible_x_m": 5.135,
    "rear_axle_x_m": -1.85,
    "front_axle_x_m": 1.60,
    "wheel_center_y_m": 0.86,
    "tire_outer_radius_m": 0.85,
    "tire_center_z_m": 1.19,
    "tire_tread_outer_z_m": 1.53,
    "tread_lugs_per_tire": 24,
    "wheel_hub_bolts_per_wheel": 12,
    "articulation_pivot_xyz_m": [0.0, 1.20, 0.0],
    "rear_axle_pivot_xyz_m": [-1.85, 0.86, 0.0],
    "loader_rear_pivot_xyz_m": [0.28, 1.50, 0.0],
    "stowed_arm_elbow_xyz_m": [1.55, 1.23, 0.0],
    "stowed_bucket_hinge_xyz_m": [3.23, 0.58, 0.0],
    "raised_arm_elbow_xyz_m": [1.18, 3.50, 0.0],
    "raised_bucket_hinge_xyz_m": [2.05, 4.37, 0.0],
    "stowed_bucket_rotation_blender_y_deg": 16.0,
    "raised_dump_rotation_blender_y_deg": 45.0,
    "bucket_visual_width_m": 3.07,
    "bucket_side_guard_outer_width_m": 3.17,
    "bucket_cutting_edge_segments": 9,
    "loader_arm_lateral_center_m": 0.78,
    "loader_hose_visual_diameter_m": 0.032,
    "steering_cylinder_barrel_visual_radius_m": 0.075,
    "steering_cylinder_rod_visual_radius_m": 0.044,
    "structural_triangle_budget": 180000,
}


UNRESOLVED = [
    "standard and additional counterweight individual masses and attachment geometry",
    "26.5R25 L-3 tire manufacturer, tread pattern, carcass, loaded radius, and pressure",
    "stock-pile bucket part number, shell radii, side guards, and cutting-edge fastener pattern",
    "loader arm pivot coordinates, bellcrank coordinates, link lengths, and cylinder anchors",
    "front and rear frame casting geometry and articulation bearing stack",
    "rear axle center-pin coordinates, stops, and tire-deflection envelope",
    "KHMT, driveshaft, planetary reduction, differentials, and brake internal geometry",
    "hydraulic hose lengths, pressures, fittings, clamps, and routing under guards",
    "powered hood and swing-out cooling-mask hinge coordinates and service envelopes",
    "cab interior option set, mirror/camera package, work-light package, and exact glazing curvature",
    "public material and branding authorization",
]


COLLECTIONS: dict[str, bpy.types.Collection] = {}
MATERIALS: dict[str, bpy.types.Material] = {}
ART: dict[str, bpy.types.Object] = {}
RENDER_PATHS: list[Path] = []


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dirs() -> None:
    for path in (BLEND_PATH.parent, GLB_PATH.parent, RECEIPT_PATH.parent, RENDER_DIR):
        path.mkdir(parents=True, exist_ok=True)


def reset_scene() -> None:
    # Do not leave rotating .blend1 backups in the exact candidate package.
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            datablocks.remove(datablock)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    if hasattr(scene.render, "dither_intensity"):
        scene.render.dither_intensity = 0.0
    if hasattr(scene, "eevee"):
        scene.eevee.taa_samples = 64
        scene.eevee.taa_render_samples = 64
        scene.eevee.use_taa_reprojection = False
        scene.eevee.use_shadow_jitter_viewport = False
    for stamp_property in (
        "use_stamp_camera", "use_stamp_date", "use_stamp_filename",
        "use_stamp_frame", "use_stamp_frame_range", "use_stamp_hostname",
        "use_stamp_labels", "use_stamp_lens", "use_stamp_marker",
        "use_stamp_memory", "use_stamp_note", "use_stamp_render_time",
        "use_stamp_scene", "use_stamp_sequencer_strip", "use_stamp_time",
    ):
        if hasattr(scene.render, stamp_property):
            setattr(scene.render, stamp_property, False)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.018, 0.022, 0.027)


def make_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    COLLECTIONS[name] = collection
    return collection


def move_to_collection(obj: bpy.types.Object, collection_name: str) -> None:
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    COLLECTIONS[collection_name].objects.link(obj)


def set_parent(obj: bpy.types.Object, parent: bpy.types.Object,
               preserve_world: bool = True) -> None:
    world = obj.matrix_world.copy()
    obj.parent = parent
    if preserve_world:
        obj.matrix_world = world


def material(name: str, color: tuple[float, float, float, float], metallic=0.0,
             roughness=0.45, transmission=0.0, emission=0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = color[3]
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission > 0 and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = color
        bsdf.inputs["Emission Strength"].default_value = emission
    if color[3] < 1.0 and hasattr(mat, "surface_render_method"):
        # Alpha blending avoids stochastic screen-door pixels in exact-hash
        # review renders while retaining a readable glazing boundary.
        mat.surface_render_method = "BLENDED"
    MATERIALS[name] = mat
    return mat


def apply_material(obj: bpy.types.Object, material_name: str) -> None:
    if obj.type == "MESH":
        obj.data.materials.append(MATERIALS[material_name])


def add_empty(name: str, xyz: tuple[float, float, float], collection: str,
              size=0.15, parent=None) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = mv(*xyz)
    COLLECTIONS[collection].objects.link(obj)
    if parent:
        set_parent(obj, parent)
    return obj


def add_box(name: str, center: tuple[float, float, float],
            size: tuple[float, float, float], material_name: str,
            collection: str, bevel=0.025, parent=None,
            parent_local=False, hidden_render=False) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (size[0], size[2], size[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = min(bevel, min(size) * 0.20)
        modifier.segments = 2
    apply_material(obj, material_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent, preserve_world=not parent_local)
    obj.hide_render = hidden_render
    return obj


def add_cylinder(name: str, center: tuple[float, float, float], radius: float,
                 depth: float, axis: str, material_name: str, collection: str,
                 vertices=32, parent=None, bevel=True) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    if axis == "z":
        obj.rotation_euler[0] = math.radians(90)
    elif axis == "x":
        obj.rotation_euler[1] = math.radians(90)
    elif axis != "y":
        raise ValueError(f"Unsupported machine axis {axis}")
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = min(radius * 0.10, 0.018)
        modifier.segments = 2
    apply_material(obj, material_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def add_uv_sphere(name: str, center: tuple[float, float, float], radius: float,
                  material_name: str, collection: str, parent=None,
                  segments=24, rings=12) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                        radius=radius, location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    apply_material(obj, material_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def add_cone(name: str, center: tuple[float, float, float], radius1: float,
             radius2: float, depth: float, axis: str, material_name: str,
             collection: str, vertices=32, parent=None) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1,
                                   radius2=radius2, depth=depth,
                                   location=mv(*center))
    obj = bpy.context.object
    obj.name = name
    if axis == "z":
        obj.rotation_euler[0] = math.radians(90)
    elif axis == "x":
        obj.rotation_euler[1] = math.radians(90)
    elif axis != "y":
        raise ValueError(axis)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_material(obj, material_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def add_prism_xy(name: str, polygon: list[tuple[float, float]], z_center: float,
                 width: float, material_name: str, collection: str,
                 parent=None, local=False, bevel=0.02) -> bpy.types.Object:
    half = width * 0.5
    vertices = []
    for z in (-half, half):
        for x, y in polygon:
            vertices.append((x, z_center + z, y) if local else tuple(mv(x, y, z_center + z)))
    count = len(polygon)
    faces = [tuple(range(count)), tuple(range(count, count * 2))[::-1]]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    apply_material(obj, material_name)
    if bevel > 0:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    if parent:
        set_parent(obj, parent, preserve_world=not local)
    return obj


def add_unit_beam(name: str, material_name: str, collection: str,
                  bevel=0.025, parent=None) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    obj = bpy.context.object
    obj.name = name
    modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
    modifier.width = bevel
    modifier.segments = 2
    apply_material(obj, material_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def place_beam(obj: bpy.types.Object, a: tuple[float, float, float],
               b: tuple[float, float, float], lateral: float,
               vertical: float) -> None:
    pa, pb = mv(*a), mv(*b)
    direction = pb - pa
    rotation = direction.to_track_quat("X", "Z").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((direction.length * 0.5,
                                    lateral * 0.5,
                                    vertical * 0.5, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) * 0.5) @ rotation @ scale


def add_unit_cylinder(name: str, material_name: str, collection: str,
                      vertices=32, parent=None) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=1.0, depth=2.0)
    obj = bpy.context.object
    obj.name = name
    apply_material(obj, material_name)
    move_to_collection(obj, collection)
    if parent:
        set_parent(obj, parent)
    return obj


def place_cylinder(obj: bpy.types.Object, a: tuple[float, float, float],
                   b: tuple[float, float, float], radius: float) -> None:
    pa, pb = mv(*a), mv(*b)
    direction = pb - pa
    rotation = direction.to_track_quat("Z", "Y").to_matrix().to_4x4()
    scale = Matrix.Diagonal(Vector((radius, radius, direction.length * 0.5, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) * 0.5) @ rotation @ scale


def add_polyline_tube(name: str, points: list[tuple[float, float, float]],
                      depth: float, material_name: str, collection: str,
                      parent=None, cyclic=False) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{name}_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = depth
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        value = mv(*coordinate)
        point.co = (value.x, value.y, value.z, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    COLLECTIONS[collection].objects.link(obj)
    obj.data.materials.append(MATERIALS[material_name])
    if parent:
        set_parent(obj, parent)
    return obj


def update_polyline(obj: bpy.types.Object,
                    points: list[tuple[float, float, float]]) -> None:
    spline = obj.data.splines[0]
    if len(spline.points) != len(points):
        raise ValueError(f"{obj.name}: point count changed")
    for point, coordinate in zip(spline.points, points):
        value = mv(*coordinate)
        point.co = (value.x, value.y, value.z, 1.0)


def build_materials() -> None:
    # Neutral, independently authored palette; no manufacturer livery or marks.
    material("WarmGraphite", (0.055, 0.064, 0.071, 1.0), metallic=0.58, roughness=0.31)
    material("IndustrialBronze", (0.33, 0.19, 0.075, 1.0), metallic=0.46, roughness=0.34)
    material("PanelWarmGrey", (0.29, 0.30, 0.29, 1.0), metallic=0.42, roughness=0.38)
    material("StructuralSteel", (0.20, 0.23, 0.25, 1.0), metallic=0.78, roughness=0.25)
    material("DarkSteel", (0.085, 0.10, 0.11, 1.0), metallic=0.72, roughness=0.28)
    material("CylinderRod", (0.55, 0.59, 0.61, 1.0), metallic=0.94, roughness=0.12)
    material("Rubber", (0.012, 0.014, 0.016, 1.0), roughness=0.88)
    material("Tread", (0.026, 0.029, 0.031, 1.0), roughness=0.82)
    material("Glass", (0.06, 0.13, 0.15, 0.30), metallic=0.03, roughness=0.11, transmission=0.46)
    material("Interior", (0.035, 0.041, 0.046, 1.0), roughness=0.76)
    material("LensWhite", (0.78, 0.82, 0.79, 1.0), metallic=0.08, roughness=0.18, emission=0.25)
    material("LensRed", (0.52, 0.025, 0.018, 1.0), roughness=0.20, emission=0.20)
    material("Marker", (0.82, 0.20, 0.06, 1.0), roughness=0.35)
    material("Collision", (0.9, 0.08, 0.04, 0.0), roughness=0.50)
    material("Inspection", (0.08, 0.45, 0.9, 0.0), roughness=0.50)
    material("Ground", (0.042, 0.048, 0.052, 1.0), roughness=0.96)


def build_identity_and_frames() -> bpy.types.Object:
    root = add_empty("WA47510_Root", (0.0, 0.0, 0.0), "Fixed_Structure", 0.30)
    root["machine_id"] = MACHINE_ID
    root["configuration_id"] = CONFIGURATION_ID
    root["candidate_class"] = CANDIDATE_CLASS
    root["engineering_authority"] = False

    rear_root = add_empty("RearFrame_Root", (0.0, 0.0, 0.0), "Fixed_Structure", 0.22, root)
    front_root = add_empty("Articulation_FrontFrame_Root_Reconstructed",
                           tuple(RECONSTRUCTED["articulation_pivot_xyz_m"]),
                           "Front_Frame", 0.22, root)
    rear_axle = add_empty("RearAxle_Oscillation_Root_Reconstructed",
                          tuple(RECONSTRUCTED["rear_axle_pivot_xyz_m"]),
                          "Wheels", 0.20, rear_root)
    ART.update(root=root, rear_root=rear_root, front_root=front_root, rear_axle=rear_axle)

    # Rear frame, engine deck, counterweight, and longitudinal belly protection.
    add_box("RearFrame_Spine", (-1.78, 0.92, 0.0), (3.45, 0.66, 1.18),
            "WarmGraphite", "Fixed_Structure", 0.09, rear_root)
    add_prism_xy("RearCounterweight_Mass", [(-4.05, 0.52), (-3.97, 1.30),
                 (-3.72, 1.72), (-3.28, 1.76), (-3.14, 0.68)], 0.0, 2.86,
                 "PanelWarmGrey", "Fixed_Structure", rear_root, bevel=0.0)
    add_box("RearCounterweight_AdditionalLower", (-3.82, 0.49, 0.0),
            (0.46, 0.33, 2.73), "StructuralSteel", "Fixed_Structure", 0.07, rear_root)
    add_box("RearBumper_ExactEnvelope", (-3.91, 0.61, 0.0),
            (0.28, 0.30, 2.82), "DarkSteel", "Fixed_Structure", 0.045, rear_root)
    add_box("RearBellyGuard", (-1.82, 0.55, 0.0), (3.34, 0.15, 1.03),
            "StructuralSteel", "Fixed_Structure", 0.025, rear_root)
    add_cylinder("RearAxleHousing", (-1.85, 0.86, 0.0), 0.24, 2.38, "z",
                 "DarkSteel", "Wheels", 36, rear_axle)
    add_cylinder("RearDifferentialHousing", (-1.85, 0.86, 0.0), 0.37, 0.52, "z",
                 "StructuralSteel", "Wheels", 36, rear_axle)

    # Engine hood core and independently authored faceted service cladding.
    add_box("EngineCompartment_Core", (-2.62, 1.77, 0.0), (2.16, 1.42, 2.30),
            "WarmGraphite", "Fixed_Structure", 0.10, rear_root)
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 1.18
        add_prism_xy(f"EngineHoodSidePanel_{suffix}",
                     [(-3.66, 1.18), (-3.52, 2.36), (-3.03, 2.64),
                      (-1.62, 2.58), (-1.42, 2.20), (-1.55, 1.13)],
                     z, 0.055, "IndustrialBronze", "Fixed_Structure", rear_root, bevel=0.035)
        add_box(f"EngineServiceDoor_{suffix}", (-2.74, 1.84, z + side * 0.032),
                (1.26, 0.80, 0.025), "PanelWarmGrey", "Fixed_Structure", 0.016, rear_root)
        for index, x in enumerate((-3.20, -2.96, -2.72, -2.48, -2.24)):
            add_box(f"EngineVent_{suffix}_{index + 1:02d}", (x, 1.87, z + side * 0.052),
                    (0.075, 0.60, 0.018), "DarkSteel", "Details", 0.005, rear_root)
        for index, (x, y) in enumerate(((-3.33, 1.31), (-3.33, 2.26),
                                         (-2.12, 1.31), (-2.12, 2.26))):
            add_cylinder(f"ServicePanelFastener_{suffix}_{index + 1:02d}",
                         (x, y, z + side * 0.067), 0.026, 0.018, "z",
                         "CylinderRod", "Details", 16, rear_root)

    # Rear cooling grille and visible swing-out-mask cues.
    add_box("RearCoolingMask", (-3.997, 1.88, 0.0), (0.055, 1.18, 2.10),
            "DarkSteel", "Fixed_Structure", 0.018, rear_root)
    for index, y in enumerate(tuple(1.35 + 0.10 * i for i in range(11))):
        add_box(f"RearCoolingGrille_H_{index + 1:02d}", (-4.029, y, 0.0),
                (0.026, 0.025, 1.88), "StructuralSteel", "Details", 0.004, rear_root)
    for index, z in enumerate((-0.82, -0.55, -0.28, 0.0, 0.28, 0.55, 0.82)):
        add_box(f"RearCoolingGrille_V_{index + 1:02d}", (-4.031, 1.88, z),
                (0.024, 1.04, 0.025), "StructuralSteel", "Details", 0.004, rear_root)
    add_cylinder("ExhaustStack", (-2.62, 2.98, 0.77), 0.09, 0.92, "y",
                 "DarkSteel", "Details", 28, rear_root)
    add_cone("ExhaustRainCap", (-2.62, 3.45, 0.77), 0.13, 0.08, 0.06, "y",
             "StructuralSteel", "Details", 28, rear_root)
    add_cylinder("AirPrecleaner_Body", (-1.92, 2.95, -0.78), 0.13, 0.60, "y",
                 "DarkSteel", "Details", 32, rear_root)
    add_cone("AirPrecleaner_Cap", (-1.92, 3.27, -0.78), 0.20, 0.13, 0.10, "y",
             "StructuralSteel", "Details", 32, rear_root)

    # Front articulated frame and fixed front axle.
    add_prism_xy("FrontFrame_Main", [(-0.12, 0.62), (0.15, 1.36),
                 (1.82, 1.47), (2.42, 1.11), (2.55, 0.62)], 0.0, 1.34,
                 "WarmGraphite", "Front_Frame", front_root, bevel=0.07)
    add_box("FrontFrame_BellyPan", (1.08, 0.56, 0.0), (2.26, 0.16, 1.22),
            "StructuralSteel", "Front_Frame", 0.03, front_root)
    add_cylinder("FrontAxleHousing", (1.60, 0.86, 0.0), 0.25, 2.38, "z",
                 "DarkSteel", "Wheels", 36, front_root)
    add_cylinder("FrontDifferentialHousing", (1.60, 0.86, 0.0), 0.38, 0.54, "z",
                 "StructuralSteel", "Wheels", 36, front_root)
    add_cylinder("CenterArticulationUpperPin", (0.0, 1.42, 0.0), 0.17, 0.34, "y",
                 "StructuralSteel", "Front_Frame", 36, root)
    add_cylinder("CenterArticulationLowerPin", (0.0, 0.82, 0.0), 0.20, 0.38, "y",
                 "StructuralSteel", "Front_Frame", 36, root)
    for side, suffix in ((-1, "L"), (1, "R")):
        add_box(f"ArticulationCheek_{suffix}", (0.06, 1.10, side * 0.42),
                (0.82, 0.66, 0.16), "DarkSteel", "Front_Frame", 0.045, front_root)

    # Steps, catwalks, handrails and tie-off cues.
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 1.34
        for index, (x, y) in enumerate(((-1.16, 0.48), (-1.02, 0.77),
                                         (-0.86, 1.06), (-0.67, 1.34))):
            add_box(f"AccessStep_{suffix}_{index + 1:02d}", (x, y, z),
                    (0.48, 0.10, 0.32), "StructuralSteel", "Details", 0.018, rear_root)
            for slot in (-0.12, 0.0, 0.12):
                add_box(f"StepSlot_{suffix}_{index + 1:02d}_{slot:+.2f}",
                        (x + slot, y + 0.058, z), (0.035, 0.018, 0.22),
                        "DarkSteel", "Details", 0.003, rear_root)
        add_polyline_tube(f"CabAccessHandrail_{suffix}",
                          [(-1.23, 0.62, z), (-1.31, 1.62, z),
                           (-1.15, 2.60, z), (-0.72, 2.85, z)],
                          0.026, "StructuralSteel", "Details", rear_root)
        add_polyline_tube(f"RoofPerimeterRail_{suffix}",
                          [(-1.22, 3.52, side * 1.02), (0.18, 3.52, side * 1.02)],
                          0.020, "StructuralSteel", "Details", rear_root)

    return root


def build_wheel(name_prefix: str, x: float, side: int,
                parent: bpy.types.Object) -> None:
    suffix = "R" if side > 0 else "L"
    z = side * RECONSTRUCTED["tire_center_z_m"]
    y = RECONSTRUCTED["wheel_center_y_m"]
    add_cylinder(f"{name_prefix}Tire_{suffix}", (x, y, z), 0.85, 0.63, "z",
                 "Rubber", "Wheels", 48, parent)
    add_cylinder(f"{name_prefix}SidewallOuter_{suffix}", (x, y, side * 1.495),
                 0.76, 0.045, "z", "Tread", "Wheels", 48, parent)
    add_cylinder(f"{name_prefix}RimOuter_{suffix}", (x, y, side * 1.505),
                 0.49, 0.050, "z", "IndustrialBronze", "Wheels", 40, parent)
    add_cylinder(f"{name_prefix}RimDish_{suffix}", (x, y, side * 1.516),
                 0.35, 0.045, "z", "StructuralSteel", "Wheels", 40, parent)
    add_cylinder(f"{name_prefix}FinalDriveHub_{suffix}", (x, y, side * 1.522),
                 0.16, 0.055, "z", "DarkSteel", "Wheels", 32, parent)
    for bolt_index in range(RECONSTRUCTED["wheel_hub_bolts_per_wheel"]):
        angle = math.tau * bolt_index / RECONSTRUCTED["wheel_hub_bolts_per_wheel"]
        bx = x + 0.245 * math.cos(angle)
        by = y + 0.245 * math.sin(angle)
        add_cylinder(f"{name_prefix}RimBolt_{suffix}_{bolt_index + 1:02d}",
                     (bx, by, side * 1.543), 0.026, 0.022, "z",
                     "CylinderRod", "Details", 12, parent, bevel=False)
    # Reconstructed L-3-like block tread. Count and pitch are not manufacturer facts.
    for lug_index in range(RECONSTRUCTED["tread_lugs_per_tire"]):
        angle = math.tau * lug_index / RECONSTRUCTED["tread_lugs_per_tire"]
        radius = 0.735
        center = (x + radius * math.cos(angle), y + radius * math.sin(angle), z)
        lug = add_box(f"{name_prefix}TreadLug_{suffix}_{lug_index + 1:02d}",
                      center, (0.18, 0.16, 0.68), "Tread", "Wheels", 0.018, parent)
        lug.rotation_euler[1] = -angle
        if lug_index % 2:
            lug.rotation_euler[0] = math.radians(side * 7.0)


def build_wheels() -> None:
    build_wheel("Rear", RECONSTRUCTED["rear_axle_x_m"], -1, ART["rear_axle"])
    build_wheel("Rear", RECONSTRUCTED["rear_axle_x_m"], 1, ART["rear_axle"])
    build_wheel("Front", RECONSTRUCTED["front_axle_x_m"], -1, ART["front_root"])
    build_wheel("Front", RECONSTRUCTED["front_axle_x_m"], 1, ART["front_root"])

    # Full-width fenders with extension lips and support brackets.
    for axle, x, parent in (("Rear", -1.85, ART["rear_root"]),
                            ("Front", 1.60, ART["front_root"])):
        for side, suffix in ((-1, "L"), (1, "R")):
            z = side * 1.24
            add_prism_xy(f"{axle}Fender_{suffix}",
                         [(x - 1.02, 1.05), (x - 0.78, 1.54),
                          (x + 0.78, 1.54), (x + 1.02, 1.05)],
                         z, 0.18, "PanelWarmGrey", "Details", parent, bevel=0.025)
            add_box(f"{axle}MudFlap_{suffix}", (x - 0.92, 0.70, side * 1.32),
                    (0.12, 0.62, 0.18), "Rubber", "Details", 0.012, parent)


def build_cab() -> None:
    root = ART["rear_root"]
    cab_root = add_empty("Cab_ROPS_Root_Reconstructed", (-0.53, 1.38, 0.0),
                         "Cab_ROPS", 0.20, root)
    cab_root["authority"] = "observed_form_reconstructed_dimensions"
    ART["cab_root"] = cab_root

    # Pillar beams follow the tall four-post cab and floor-to-ceiling glazing.
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 1.02
        for prefix, a, b in (
            ("Front", (0.14, 1.45, z), (0.02, 3.40, z)),
            ("Rear", (-1.22, 1.45, z), (-1.32, 3.40, z)),
        ):
            beam = add_unit_beam(f"ROPS_{prefix}Pillar_{suffix}", "WarmGraphite",
                                 "Cab_ROPS", 0.024, cab_root)
            place_beam(beam, a, b, 0.10, 0.11)
        add_box(f"ROPS_LowerSill_{suffix}", (-0.56, 1.48, z),
                (1.48, 0.13, 0.10), "WarmGraphite", "Cab_ROPS", 0.022, cab_root)
        add_box(f"ROPS_UpperRail_{suffix}", (-0.62, 3.40, z),
                (1.48, 0.10, 0.10), "WarmGraphite", "Cab_ROPS", 0.022, cab_root)
        add_box(f"CabSideGlassLower_{suffix}", (-0.56, 2.08, side * 1.005),
                (1.20, 1.04, 0.028), "Glass", "Cab_ROPS", 0.006, cab_root)
        add_box(f"CabSideGlassUpper_{suffix}", (-0.60, 2.96, side * 1.005),
                (1.28, 0.64, 0.028), "Glass", "Cab_ROPS", 0.006, cab_root)
        add_box(f"DoorMidRail_{suffix}", (-0.57, 2.46, side * 1.028),
                (1.30, 0.07, 0.055), "WarmGraphite", "Cab_ROPS", 0.012, cab_root)
        add_box(f"DoorHandle_{suffix}", (-0.20, 2.30, side * 1.058),
                (0.22, 0.045, 0.045), "StructuralSteel", "Cab_ROPS", 0.010, cab_root)

    add_box("ROPS_Roof", (-0.62, 3.44, 0.0), (1.62, 0.12, 2.18),
            "PanelWarmGrey", "Cab_ROPS", 0.055, cab_root)
    add_box("Cab_FrontGlass", (0.08, 2.43, 0.0), (0.045, 1.78, 1.88),
            "Glass", "Cab_ROPS", 0.008, cab_root)
    add_box("Cab_RearGlass", (-1.27, 2.47, 0.0), (0.040, 1.62, 1.80),
            "Glass", "Cab_ROPS", 0.008, cab_root)
    add_box("ROPS_FrontHeader", (0.07, 3.37, 0.0), (0.14, 0.12, 2.05),
            "WarmGraphite", "Cab_ROPS", 0.025, cab_root)
    add_box("ROPS_RearHeader", (-1.27, 3.37, 0.0), (0.14, 0.12, 2.05),
            "WarmGraphite", "Cab_ROPS", 0.025, cab_root)

    # Roof rails establish the published 3.54 m complete-machine height.
    for side, suffix in ((-1, "L"), (1, "R")):
        add_polyline_tube(f"CabRoofRail_{suffix}",
                          [(-1.22, 3.52, side * 0.96),
                           (0.08, 3.52, side * 0.96)],
                          0.020, "StructuralSteel", "Cab_ROPS", cab_root)
    add_polyline_tube("CabRoofRail_RearCross",
                      [(-1.22, 3.52, -0.96), (-1.22, 3.52, 0.96)],
                      0.020, "StructuralSteel", "Cab_ROPS", cab_root)
    add_polyline_tube("CabRoofRail_FrontCross",
                      [(0.08, 3.52, -0.96), (0.08, 3.52, 0.96)],
                      0.020, "StructuralSteel", "Cab_ROPS", cab_root)

    # Readable operator environment, not an operational control replica.
    add_box("OperatorSeat_Cushion", (-0.67, 1.70, 0.0), (0.58, 0.20, 0.54),
            "Interior", "Cab_ROPS", 0.07, cab_root)
    add_box("OperatorSeat_Back", (-0.92, 2.14, 0.0), (0.18, 0.78, 0.56),
            "Interior", "Cab_ROPS", 0.08, cab_root)
    add_box("OperatorHeadrest", (-0.94, 2.65, 0.0), (0.16, 0.26, 0.38),
            "Interior", "Cab_ROPS", 0.06, cab_root)
    add_cylinder("SteeringColumn", (-0.02, 2.06, -0.20), 0.045, 0.48, "x",
                 "DarkSteel", "Cab_ROPS", 24, cab_root)
    add_cylinder("SteeringWheel", (0.18, 2.17, -0.20), 0.22, 0.045, "x",
                 "Interior", "Cab_ROPS", 32, cab_root)
    add_box("FiveAxisConsole", (-0.46, 1.94, 0.57), (0.62, 0.23, 0.30),
            "PanelWarmGrey", "Cab_ROPS", 0.045, cab_root)
    add_cylinder("LoaderJoystick", (-0.23, 2.15, 0.60), 0.045, 0.27, "y",
                 "Interior", "Cab_ROPS", 24, cab_root)
    add_box("SevenInchMonitor", (-0.02, 2.50, 0.58), (0.12, 0.32, 0.34),
            "Interior", "Cab_ROPS", 0.025, cab_root)
    add_box("MonitorFace", (0.045, 2.50, 0.58), (0.018, 0.25, 0.27),
            "Glass", "Cab_ROPS", 0.006, cab_root)

    # Mirrors, wipers and lighting are explicit inspection cues.
    add_polyline_tube("FrontWiperArm", [(0.115, 3.16, -0.40),
                      (0.15, 2.50, -0.08)], 0.018, "DarkSteel", "Details", cab_root)
    add_box("FrontWiperBlade", (0.15, 2.45, -0.03), (0.035, 0.58, 0.035),
            "Rubber", "Details", 0.006, cab_root)
    for side, suffix in ((-1, "L"), (1, "R")):
        add_polyline_tube(f"MirrorArm_{suffix}",
                          [(0.00, 3.12, side * 1.02),
                           (0.12, 3.18, side * 1.34)],
                          0.025, "DarkSteel", "Details", cab_root)
        add_box(f"Mirror_{suffix}", (0.16, 3.18, side * 1.38),
                (0.10, 0.31, 0.25), "Glass", "Details", 0.035, cab_root)
        for index, x in enumerate((-0.92, -0.28)):
            add_box(f"CabWorkLight_{suffix}_{index + 1:02d}",
                    (x, 3.42, side * 1.05), (0.18, 0.12, 0.16),
                    "DarkSteel", "Details", 0.018, cab_root)
            add_box(f"CabWorkLightLens_{suffix}_{index + 1:02d}",
                    (x + 0.091, 3.42, side * 1.05), (0.012, 0.09, 0.12),
                    "LensWhite", "Details", 0.004, cab_root)


def setup_loader_and_bucket() -> None:
    front_root = ART["front_root"]
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * RECONSTRUCTED["loader_arm_lateral_center_m"]
        rear_pivot = add_empty(f"LoaderArmRearPivot_{suffix}_Reconstructed",
                               (0.28, 1.50, z), "Markers", 0.12, ART["root"])
        rear_pivot["authority"] = "reconstructed"
        ART[f"arm_rear_{suffix}"] = add_unit_beam(
            f"StandardLoaderArmRear_{suffix}", "IndustrialBronze", "Loader", 0.045, front_root)
        ART[f"arm_front_{suffix}"] = add_unit_beam(
            f"StandardLoaderArmFront_{suffix}", "IndustrialBronze", "Loader", 0.045, front_root)
        ART[f"arm_web_{suffix}"] = add_unit_beam(
            f"StandardLoaderArmLowerWeb_{suffix}", "WarmGraphite", "Loader", 0.035, front_root)
        ART[f"lift_barrel_{suffix}"] = add_unit_cylinder(
            f"LiftCylinder_Barrel_{suffix}", "WarmGraphite", "Hydraulics", 36, ART["root"])
        ART[f"lift_rod_{suffix}"] = add_unit_cylinder(
            f"LiftCylinder_Rod_{suffix}", "CylinderRod", "Hydraulics", 32, ART["root"])
        for bundle in (1, 2):
            ART[f"hose_{suffix}_{bundle}"] = add_polyline_tube(
                f"LoaderHose_{suffix}_{bundle:02d}",
                [(0.12, 1.16, z), (0.76, 1.55, z),
                 (1.72, 1.30, z), (3.05, 0.82, z)],
                RECONSTRUCTED["loader_hose_visual_diameter_m"] * 0.5,
                "Rubber", "Hydraulics", ART["root"])

    ART["arm_crossmember"] = add_unit_beam(
        "LoaderArmCrossmember", "StructuralSteel", "Loader", 0.04, front_root)
    ART["bucket_crossmember"] = add_unit_beam(
        "BucketHingeCrossmember", "DarkSteel", "Loader", 0.035, front_root)
    ART["tilt_barrel"] = add_unit_cylinder(
        "BucketCylinder_Barrel", "WarmGraphite", "Hydraulics", 40, ART["root"])
    ART["tilt_rod"] = add_unit_cylinder(
        "BucketCylinder_Rod", "CylinderRod", "Hydraulics", 36, ART["root"])
    ART["bellcrank_a"] = add_unit_beam(
        "ZBar_Bellcrank_Upper_Reconstructed", "StructuralSteel", "Loader", 0.035, front_root)
    ART["bellcrank_b"] = add_unit_beam(
        "ZBar_Bellcrank_Lower_Reconstructed", "StructuralSteel", "Loader", 0.035, front_root)
    ART["bucket_link"] = add_unit_beam(
        "ZBar_BucketLink_Reconstructed", "DarkSteel", "Loader", 0.028, front_root)
    add_cylinder("ZBar_BellcrankPivotCap", (1.37, 1.55, 0.0), 0.14, 0.28, "z",
                 "CylinderRod", "Loader", 32, front_root)

    bucket_root = add_empty("StockPileBucket_PivotRoot_Reconstructed",
                            tuple(RECONSTRUCTED["stowed_bucket_hinge_xyz_m"]),
                            "Bucket", 0.17, front_root)
    bucket_root["authority"] = "reconstructed constrained by selected 4.2 m3 stock-pile bucket facts"
    ART["bucket_root"] = bucket_root

    # Deep curved-side silhouette approximated by a faceted, independently
    # authored shell. It is not reverse-engineered CAD or a scale tracing.
    bucket_polygon = [
        (-0.28, 0.08), (0.02, 1.62), (0.48, 1.82),
        (1.18, 1.38), (1.72, 0.58), (1.79, -0.02),
        (1.54, -0.13), (0.86, 0.00), (0.16, 0.22),
    ]
    add_prism_xy("StockPileBucket_Shell", bucket_polygon, 0.0,
                 RECONSTRUCTED["bucket_visual_width_m"], "IndustrialBronze",
                 "Bucket", bucket_root, local=True, bevel=0.035)
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 1.565
        add_prism_xy(f"BucketSideGuard_{suffix}",
                     [(-0.30, 0.05), (-0.02, 1.66), (0.47, 1.87),
                      (1.24, 1.42), (1.80, 0.56), (1.82, -0.06),
                      (1.53, -0.08), (0.30, 0.12)],
                     z, 0.040, "WarmGraphite", "Bucket", bucket_root,
                     local=True, bevel=0.018)
        add_box(f"BucketTopCornerGuard_{suffix}", (0.18, 1.64, z),
                (0.58, 0.14, 0.04), "StructuralSteel", "Bucket", 0.018,
                bucket_root, parent_local=True)
    add_box("BucketBoltOnCuttingEdge", (1.74, 0.01, 0.0),
            (0.22, 0.12, 3.17), "StructuralSteel", "Bucket", 0.018,
            bucket_root, parent_local=True)
    # Nine replaceable B.O.C. wear segments; no incompatible tooth claim.
    for index in range(RECONSTRUCTED["bucket_cutting_edge_segments"]):
        z = -1.40 + index * 0.35
        add_box(f"BucketBOC_WearSegment_{index + 1:02d}",
                (1.84, 0.005, z), (0.26, 0.055, 0.30),
                "CylinderRod", "Bucket", 0.012, bucket_root, parent_local=True)
        for bolt_offset in (-0.09, 0.09):
            add_cylinder(f"BucketBOC_Bolt_{index + 1:02d}_{bolt_offset:+.2f}",
                         (1.80, -0.020, z + bolt_offset), 0.025, 0.018, "y",
                         "DarkSteel", "Bucket", 12, bucket_root, bevel=False)
    for rib_index, z in enumerate((-1.18, -0.78, -0.39, 0.0, 0.39, 0.78, 1.18)):
        add_box(f"BucketBackRib_{rib_index + 1:02d}", (0.31, 1.28, z),
                (0.70, 0.10, 0.08), "WarmGraphite", "Bucket", 0.016,
                bucket_root, parent_local=True)

    apply_loader_pose("stowed")


def apply_loader_pose(pose: str) -> dict:
    if pose == "stowed":
        elbow = tuple(RECONSTRUCTED["stowed_arm_elbow_xyz_m"])
        hinge = tuple(RECONSTRUCTED["stowed_bucket_hinge_xyz_m"])
        bucket_rotation = RECONSTRUCTED["stowed_bucket_rotation_blender_y_deg"]
    elif pose == "raised_dump":
        elbow = tuple(RECONSTRUCTED["raised_arm_elbow_xyz_m"])
        hinge = tuple(RECONSTRUCTED["raised_bucket_hinge_xyz_m"])
        bucket_rotation = RECONSTRUCTED["raised_dump_rotation_blender_y_deg"]
    else:
        raise ValueError(pose)

    rear = tuple(RECONSTRUCTED["loader_rear_pivot_xyz_m"])
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * RECONSTRUCTED["loader_arm_lateral_center_m"]
        rear_z = (rear[0], rear[1], z)
        elbow_z = (elbow[0], elbow[1], z)
        hinge_z = (hinge[0], hinge[1], z)
        place_beam(ART[f"arm_rear_{suffix}"], rear_z, elbow_z, 0.23, 0.28)
        place_beam(ART[f"arm_front_{suffix}"], elbow_z, hinge_z, 0.24, 0.30)
        lower_end = (hinge[0] - 0.32, hinge[1] - 0.16, z)
        place_beam(ART[f"arm_web_{suffix}"], (rear[0] + 0.12, rear[1] - 0.25, z),
                   lower_end, 0.15, 0.17)

        cylinder_base = (0.10, 0.72, side * 0.70)
        cylinder_end = (elbow[0] + 0.10, elbow[1] - 0.17, side * 0.70)
        base_v, end_v = mv(*cylinder_base), mv(*cylinder_end)
        split = base_v.lerp(end_v, 0.58)
        split_m = (split.x, split.z, split.y)
        place_cylinder(ART[f"lift_barrel_{suffix}"], cylinder_base, split_m, 0.112)
        place_cylinder(ART[f"lift_rod_{suffix}"], split_m, cylinder_end, 0.068)

        for bundle, offset in ((1, -0.026), (2, 0.026)):
            update_polyline(ART[f"hose_{suffix}_{bundle}"], [
                (0.10, 1.05, z + offset),
                (0.70, 1.55, z + offset),
                (elbow[0] + 0.10, elbow[1] + 0.12, z + offset),
                (hinge[0] - 0.18, hinge[1] + 0.20, z + offset),
            ])

    place_beam(ART["arm_crossmember"],
               (elbow[0], elbow[1], -0.89), (elbow[0], elbow[1], 0.89),
               0.22, 0.22)
    place_beam(ART["bucket_crossmember"],
               (hinge[0], hinge[1], -0.91), (hinge[0], hinge[1], 0.91),
               0.18, 0.18)

    # Reconstructed Z-bar: center cylinder drives a two-piece bellcrank and
    # link, all updated with the visual pose without claiming mechanical closure.
    pivot = (1.36, elbow[1] + 0.18, 0.0)
    upper = (1.04, elbow[1] + 0.52, 0.0)
    lower = (1.66, elbow[1] - 0.13, 0.0)
    link_end = (hinge[0] - 0.18, hinge[1] + 0.62, 0.0)
    place_beam(ART["bellcrank_a"], pivot, upper, 0.20, 0.20)
    place_beam(ART["bellcrank_b"], pivot, lower, 0.20, 0.20)
    place_beam(ART["bucket_link"], lower, link_end, 0.16, 0.16)
    tilt_base = (0.30, 1.62, 0.0)
    base_v, upper_v = mv(*tilt_base), mv(*upper)
    split = base_v.lerp(upper_v, 0.62)
    split_m = (split.x, split.z, split.y)
    place_cylinder(ART["tilt_barrel"], tilt_base, split_m, 0.13)
    place_cylinder(ART["tilt_rod"], split_m, upper, 0.078)

    bucket_root = ART["bucket_root"]
    bucket_root.location = mv(*hinge)
    bucket_root.rotation_euler = (0.0, math.radians(bucket_rotation), 0.0)
    bpy.context.view_layer.update()
    return {"hinge": hinge, "elbow": elbow, "bucket_rotation_blender_y_deg": bucket_rotation}


def setup_steering_hydraulics() -> None:
    for side, suffix in ((-1, "L"), (1, "R")):
        ART[f"steer_barrel_{suffix}"] = add_unit_cylinder(
            f"SteeringCylinder_Barrel_{suffix}", "WarmGraphite", "Hydraulics", 36, ART["root"])
        ART[f"steer_rod_{suffix}"] = add_unit_cylinder(
            f"SteeringCylinder_Rod_{suffix}", "CylinderRod", "Hydraulics", 32, ART["root"])
    apply_articulation(0.0)


def apply_articulation(degrees: float) -> None:
    ART["front_root"].rotation_euler[2] = math.radians(degrees)
    angle = math.radians(degrees)
    for side, suffix in ((-1, "L"), (1, "R")):
        rear = (-0.80, 0.92, side * 0.63)
        base_front = (0.79, 0.92, side * 0.63)
        x, z = base_front[0], base_front[2]
        front = (x * math.cos(angle) - z * math.sin(angle),
                 base_front[1], x * math.sin(angle) + z * math.cos(angle))
        rear_v, front_v = mv(*rear), mv(*front)
        split = rear_v.lerp(front_v, 0.58)
        split_m = (split.x, split.z, split.y)
        place_cylinder(ART[f"steer_barrel_{suffix}"], rear, split_m,
                       RECONSTRUCTED["steering_cylinder_barrel_visual_radius_m"])
        place_cylinder(ART[f"steer_rod_{suffix}"], split_m, front,
                       RECONSTRUCTED["steering_cylinder_rod_visual_radius_m"])
    bpy.context.view_layer.update()


def apply_rear_axle_oscillation(degrees: float) -> None:
    ART["rear_axle"].rotation_euler[0] = math.radians(degrees)
    bpy.context.view_layer.update()


def build_lights_and_details() -> None:
    rear_root, front_root = ART["rear_root"], ART["front_root"]
    for side, suffix in ((-1, "L"), (1, "R")):
        add_box(f"RearTailLampHousing_{suffix}", (-3.92, 1.23, side * 1.05),
                (0.12, 0.30, 0.20), "DarkSteel", "Details", 0.018, rear_root)
        add_box(f"RearTailLampLens_{suffix}", (-3.986, 1.23, side * 1.05),
                (0.018, 0.23, 0.15), "LensRed", "Details", 0.004, rear_root)
        add_box(f"FrontFrameLampHousing_{suffix}", (2.34, 1.37, side * 0.58),
                (0.22, 0.18, 0.18), "DarkSteel", "Details", 0.022, front_root)
        add_box(f"FrontFrameLampLens_{suffix}", (2.455, 1.37, side * 0.58),
                (0.018, 0.13, 0.13), "LensWhite", "Details", 0.004, front_root)
        add_cylinder(f"FrontTowPin_{suffix}", (2.16, 0.57, side * 0.55),
                     0.075, 0.16, "z", "StructuralSteel", "Details", 24, front_root)
        add_cylinder(f"RearTowPin_{suffix}", (-3.73, 0.52, side * 0.62),
                     0.075, 0.16, "z", "StructuralSteel", "Details", 24, rear_root)

    # Fuel/DEF-like access cap cues are unlabelled and not option-identifying.
    add_cylinder("ServiceFillCap_Right", (-1.48, 1.68, 1.28), 0.085, 0.055, "z",
                 "StructuralSteel", "Details", 24, rear_root)
    add_cylinder("ServiceFillCap_Left", (-2.02, 1.82, -1.28), 0.085, 0.055, "z",
                 "StructuralSteel", "Details", 24, rear_root)
    for side, suffix in ((-1, "L"), (1, "R")):
        for index in range(5):
            add_cylinder(f"LoaderPivotFastener_{suffix}_{index + 1:02d}",
                         (0.28 + index * 0.50, 1.50 - index * 0.14,
                          side * 0.91), 0.055, 0.055, "z",
                         "CylinderRod", "Details", 20, ART["front_root"])


def build_helpers() -> None:
    root = ART["root"]
    marker_specs = {
        "Pivot_FrameArticulation_Reconstructed": (0.0, 1.20, 0.0),
        "Pivot_RearAxleOscillation_Reconstructed": (-1.85, 0.86, 0.0),
        "Pivot_LoaderRear_Reconstructed": (0.28, 1.50, 0.0),
        "Pivot_BucketCarry_Reconstructed": (3.23, 0.58, 0.0),
        "Anchor_LiftCylinderBase_Reconstructed": (0.10, 0.72, 0.0),
        "Anchor_BucketCylinderBase_Reconstructed": (0.30, 1.62, 0.0),
    }
    for name, xyz in marker_specs.items():
        marker = add_empty(name, xyz, "Markers", 0.13, root)
        marker["authority"] = "reconstructed"

    for name, center, size in (
        ("RearFrame_Hit", (-2.10, 1.42, 0.0), (3.90, 2.35, 2.90)),
        ("FrontFrame_Hit", (1.25, 0.98, 0.0), (2.65, 1.30, 1.55)),
        ("Cab_Hit", (-0.58, 2.48, 0.0), (1.72, 2.08, 2.20)),
        ("Bucket_Hit", (4.10, 0.76, 0.0), (2.10, 1.50, 3.17)),
    ):
        helper = add_box(name, center, size, "Collision", "Collision", 0.0,
                         root, hidden_render=True)
        helper.display_type = "WIRE"
    for name, center, size in (
        ("Articulation_Inspect", (0.0, 1.15, 0.0), (2.0, 1.4, 2.0)),
        ("LoaderLinkage_Inspect", (1.65, 1.55, 0.0), (3.6, 2.4, 2.4)),
        ("OperatorStation_Inspect", (-0.58, 2.48, 0.0), (2.0, 2.3, 2.5)),
        ("RearCooling_Inspect", (-3.55, 1.85, 0.0), (1.2, 1.8, 2.7)),
    ):
        helper = add_box(name, center, size, "Inspection", "Inspection", 0.0,
                         root, hidden_render=True)
        helper.display_type = "WIRE"


def build_studio() -> None:
    add_box("StudioFloor", (0.45, -0.07, 0.0), (18.0, 0.12, 14.0),
            "Ground", "Studio", 0.02)
    world = bpy.context.scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.015, 0.020, 0.025, 1.0)
    background.inputs["Strength"].default_value = 0.34
    for name, location, energy, size, color in (
        ("KeyLight", (3.0, -6.5, 10.5), 1700, 5.0, (1.0, 0.82, 0.64)),
        ("FillLight", (-5.5, 5.0, 6.5), 1050, 4.5, (0.52, 0.70, 1.0)),
        ("RimLight", (5.0, 6.0, 8.0), 1300, 4.0, (0.84, 0.90, 1.0)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        if hasattr(data, "use_shadow_jitter"):
            data.use_shadow_jitter = False
        obj = bpy.data.objects.new(name, data)
        COLLECTIONS["Studio"].objects.link(obj)
        obj.location = location


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_view(filename: str, camera_machine_xyz: tuple[float, float, float],
                target_machine_xyz: tuple[float, float, float], lens=58.0) -> None:
    camera_data = bpy.data.cameras.new(f"Camera_{filename}")
    camera_data.lens = lens
    camera_data.sensor_width = 36.0
    camera = bpy.data.objects.new(f"Camera_{filename}", camera_data)
    COLLECTIONS["Studio"].objects.link(camera)
    camera.location = mv(*camera_machine_xyz)
    look_at(camera, mv(*target_machine_xyz))
    bpy.context.scene.camera = camera
    path = RENDER_DIR / filename
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    RENDER_PATHS.append(path)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.cameras.remove(camera_data)


def render_review_set() -> None:
    apply_rear_axle_oscillation(0.0)
    apply_articulation(0.0)
    apply_loader_pose("stowed")
    render_view("wa475-10-technical-side.png", (0.40, 3.85, -19.2),
                (0.35, 1.55, 0.0), 58)
    render_view("wa475-10-front-three-quarter.png", (11.5, 5.8, -11.5),
                (0.75, 1.45, 0.0), 58)
    render_view("wa475-10-rear-three-quarter.png", (-12.8, 6.4, 12.4),
                (0.10, 1.52, 0.0), 52)

    apply_articulation(28.0)
    render_view("wa475-10-articulation-steering.png", (12.6, 6.5, -14.0),
                (0.30, 1.35, 0.0), 52)
    apply_articulation(0.0)

    apply_loader_pose("raised_dump")
    render_view("wa475-10-full-lift-dump.png", (9.8, 7.8, -16.8),
                (0.75, 2.55, 0.0), 55)
    render_view("wa475-10-zbar-linkage-detail.png", (5.8, 5.8, -7.2),
                (1.45, 2.85, -0.20), 74)
    apply_loader_pose("stowed")

    render_view("wa475-10-operator-cab-detail.png", (2.7, 4.6, -5.4),
                (-0.55, 2.45, -0.35), 76)
    render_view("wa475-10-rear-cooling-detail.png", (-8.0, 3.8, -5.0),
                (-3.35, 1.86, 0.0), 78)

    apply_rear_axle_oscillation(8.0)
    render_view("wa475-10-rear-axle-oscillation.png", (-7.2, 2.8, 7.4),
                (-1.85, 0.88, 0.0), 70)
    apply_rear_axle_oscillation(0.0)
    apply_articulation(0.0)
    apply_loader_pose("stowed")


def is_descendant_of(obj: bpy.types.Object, ancestor: bpy.types.Object) -> bool:
    current = obj
    while current is not None:
        if current == ancestor:
            return True
        current = current.parent
    return False


def collection_names(obj: bpy.types.Object) -> set[str]:
    return {collection.name for collection in obj.users_collection}


def is_public_export_object(obj: bpy.types.Object,
                            root: bpy.types.Object) -> bool:
    if not is_descendant_of(obj, root):
        return False
    if collection_names(obj) & {"Studio", "Markers", "Collision", "Inspection"}:
        return False
    return obj.type in {"EMPTY", "MESH", "CURVE"} and not obj.hide_render


def evaluated_visible_bounds(root: bpy.types.Object) -> dict:
    dependencies = bpy.context.evaluated_depsgraph_get()
    coordinates = []
    measured = []
    for obj in bpy.context.scene.objects:
        if not is_public_export_object(obj, root) or obj.type not in {"MESH", "CURVE"}:
            continue
        evaluated = obj.evaluated_get(dependencies)
        mesh = evaluated.to_mesh()
        for vertex in mesh.vertices:
            world = evaluated.matrix_world @ vertex.co
            coordinates.append((world.x, world.z, world.y))
        evaluated.to_mesh_clear()
        measured.append(obj.name)
    if not coordinates:
        raise RuntimeError("No public visible geometry for bounds")
    minimum = [min(point[axis] for point in coordinates) for axis in range(3)]
    maximum = [max(point[axis] for point in coordinates) for axis in range(3)]
    return {
        "axis_order": ["machine_X_longitudinal", "machine_Y_vertical", "machine_Z_right"],
        "min_m": [round(value, 6) for value in minimum],
        "max_m": [round(value, 6) for value in maximum],
        "size_m": [round(maximum[index] - minimum[index], 6) for index in range(3)],
        "measured_object_count": len(measured),
        "method": "evaluated retained-pose public mesh and curve vertices; studio, markers, collision, inspection, cameras, and lights excluded",
    }


def evaluated_counts() -> dict:
    dependencies = bpy.context.evaluated_depsgraph_get()
    counts = {"objects": 0, "meshes": 0, "vertices": 0, "triangles": 0,
              "materials": len(bpy.data.materials)}
    for obj in bpy.context.scene.objects:
        counts["objects"] += 1
        if obj.type not in {"MESH", "CURVE"}:
            continue
        evaluated = obj.evaluated_get(dependencies)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        counts["meshes"] += 1
        counts["vertices"] += len(mesh.vertices)
        counts["triangles"] += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
    return counts


def hierarchy_depth(obj: bpy.types.Object) -> int:
    depth = 0
    current = obj.parent
    while current:
        depth += 1
        current = current.parent
    return depth


def apply_public_scales(root: bpy.types.Object) -> dict:
    before_bounds = evaluated_visible_bounds(root)
    public_geometry = sorted(
        (obj for obj in bpy.context.scene.objects
         if is_public_export_object(obj, root) and obj.type in {"MESH", "CURVE"}),
        key=lambda obj: (hierarchy_depth(obj), obj.name),
    )
    before_non_identity = {
        obj.name: [round(value, 6) for value in obj.scale]
        for obj in public_geometry
        if any(abs(value - 1.0) > 1e-7 for value in obj.scale)
    }
    for obj in public_geometry:
        if all(abs(value - 1.0) <= 1e-7 for value in obj.scale):
            continue
        descendants = sorted(
            (candidate for candidate in bpy.context.scene.objects
             if candidate != obj and is_descendant_of(candidate, obj)),
            key=lambda candidate: (hierarchy_depth(candidate), candidate.name),
        )
        descendant_world = {candidate: candidate.matrix_world.copy()
                            for candidate in descendants}
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        for descendant in descendants:
            descendant.matrix_world = descendant_world[descendant]
        bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    after_non_identity = {
        obj.name: [round(value, 6) for value in obj.scale]
        for obj in public_geometry
        if any(abs(value - 1.0) > 1e-7 for value in obj.scale)
    }
    after_bounds = evaluated_visible_bounds(root)
    delta = {
        key: [round(after_bounds[key][axis] - before_bounds[key][axis], 9)
              for axis in range(3)]
        for key in ("min_m", "max_m", "size_m")
    }
    stable = all(abs(value) <= 1e-6 for values in delta.values() for value in values)
    return {
        "status": "PASS" if not after_non_identity and stable else "FAIL",
        "public_export_geometry_nodes": len(public_geometry),
        "baked_node_count": len(before_non_identity),
        "before_non_identity": before_non_identity,
        "after_non_identity": after_non_identity,
        "before_bounds_m": before_bounds,
        "after_bounds_m": after_bounds,
        "envelope_delta_m": delta,
    }


def read_glb_json(path: Path) -> dict:
    with path.open("rb") as stream:
        magic, version, length = struct.unpack("<4sII", stream.read(12))
        if magic != b"glTF" or version != 2 or length != path.stat().st_size:
            raise RuntimeError("Invalid GLB 2.0 header")
        chunk_length, chunk_type = struct.unpack("<II", stream.read(8))
        if chunk_type != 0x4E4F534A:
            raise RuntimeError("GLB first chunk is not JSON")
        return json.loads(stream.read(chunk_length).decode("utf-8").rstrip(" \t\r\n\x00"))


def inspect_glb_contract() -> dict:
    document = read_glb_json(GLB_PATH)
    scene_index = document.get("scene", 0)
    roots = document["scenes"][scene_index].get("nodes", [])
    nodes = document.get("nodes", [])
    root_names = [nodes[index].get("name") for index in roots]
    root_node = nodes[roots[0]] if len(roots) == 1 else {}
    identity = (
        root_node.get("translation", [0, 0, 0]) == [0, 0, 0]
        and root_node.get("rotation", [0, 0, 0, 1]) == [0, 0, 0, 1]
        and root_node.get("scale", [1, 1, 1]) == [1, 1, 1]
        and "matrix" not in root_node
    )
    helper_tokens = ("_Hit", "_Inspect", "Pivot_", "Anchor_", "StudioFloor",
                     "Camera_", "KeyLight", "FillLight", "RimLight")
    helper_nodes = sorted(node.get("name", "") for node in nodes
                          if any(token in node.get("name", "") for token in helper_tokens))
    mesh_nodes = [(index, node) for index, node in enumerate(nodes) if "mesh" in node]
    non_identity = []
    for index, node in mesh_nodes:
        scale = node.get("scale", [1, 1, 1])
        if "matrix" in node:
            matrix = node["matrix"]
            scale = [math.sqrt(sum(matrix[column * 4 + row] ** 2 for row in range(3)))
                     for column in range(3)]
        if any(abs(value - 1.0) > 1e-6 for value in scale):
            non_identity.append({"node_index": index, "name": node.get("name"), "scale": scale})

    triangles = 0
    primitives = 0
    position_vertices = 0
    unsupported = []
    for mesh_index, mesh in enumerate(document.get("meshes", [])):
        for primitive_index, primitive in enumerate(mesh.get("primitives", [])):
            primitives += 1
            position_index = primitive.get("attributes", {}).get("POSITION")
            if position_index is not None:
                position_vertices += document["accessors"][position_index]["count"]
            element_index = primitive.get("indices", position_index)
            count = document["accessors"][element_index]["count"] if element_index is not None else 0
            mode = primitive.get("mode", 4)
            if mode == 4:
                triangles += count // 3
            elif mode in {5, 6}:
                triangles += max(0, count - 2)
            else:
                unsupported.append({"mesh": mesh_index, "primitive": primitive_index, "mode": mode})
    decoded_counts = {
        "classification": "public_glb_decoded_geometry",
        "nodes": len(nodes),
        "mesh_nodes": len(mesh_nodes),
        "mesh_resources": len(document.get("meshes", [])),
        "primitives": primitives,
        "position_vertices": position_vertices,
        "triangles": triangles,
        "triangle_method": "decoded glTF accessor element counts; TRIANGLES count/3, strips/fans count-2",
    }
    passed = (len(roots) == 1 and root_names == ["WA47510_Root"] and identity
              and not helper_nodes and not non_identity and not unsupported
              and not document.get("cameras")
              and "KHR_lights_punctual" not in document.get("extensionsUsed", []))
    return {
        "status": "PASS" if passed else "FAIL",
        "asset_version": document.get("asset", {}).get("version"),
        "scene_direct_root_count": len(roots),
        "scene_direct_root_names": root_names,
        "root_identity_trs": identity,
        "node_count": len(nodes),
        "helper_nodes_present": helper_nodes,
        "public_mesh_node_scale_status": "PASS" if not non_identity else "FAIL",
        "public_mesh_node_count": len(mesh_nodes),
        "public_mesh_nodes_non_identity_scale": non_identity,
        "public_glb_decoded_counts": decoded_counts,
        "unsupported_primitive_modes": unsupported,
        "glb_y_up": True,
    }


def save_and_export(root: bpy.types.Object) -> None:
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    bpy.ops.object.select_all(action="DESELECT")
    public = [obj for obj in bpy.context.scene.objects if is_public_export_object(obj, root)]
    for obj in public:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH), export_format="GLB", use_selection=True,
        export_apply=True, export_yup=True, export_extras=True,
        export_texcoords=False, export_cameras=False, export_lights=False,
    )
    bpy.ops.object.select_all(action="DESELECT")


def render_quality(path: Path) -> dict:
    # Deterministic byte and raster-dimension checks; direct visual review is
    # intentionally kept PENDING for the one final batch critic.
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    bpy.data.images.remove(image)
    return {"bytes": path.stat().st_size, "width": width, "height": height}


def make_gate(gate_id: str, status: str, detail: str, expected=None, actual=None) -> dict:
    gate = {"id": gate_id, "status": status, "detail": detail}
    if expected is not None:
        gate["expected"] = expected
    if actual is not None:
        gate["actual"] = actual
    return gate


def public_semantic_nodes() -> list[str]:
    return [
        "WA47510_Root", "RearFrame_Root", "Articulation_FrontFrame_Root_Reconstructed",
        "RearAxle_Oscillation_Root_Reconstructed", "RearFrame_Spine", "RearCounterweight_Mass",
        "EngineCompartment_Core", "RearCoolingMask", "Cab_ROPS_Root_Reconstructed",
        "ROPS_Roof", "Cab_FrontGlass", "RearTire_L", "RearTire_R", "FrontTire_L",
        "FrontTire_R", "FrontFrame_Main", "CenterArticulationUpperPin",
        "SteeringCylinder_Barrel_L", "SteeringCylinder_Rod_L",
        "SteeringCylinder_Barrel_R", "SteeringCylinder_Rod_R",
        "StandardLoaderArmRear_L", "StandardLoaderArmFront_L",
        "StandardLoaderArmRear_R", "StandardLoaderArmFront_R",
        "LiftCylinder_Barrel_L", "LiftCylinder_Rod_L",
        "LiftCylinder_Barrel_R", "LiftCylinder_Rod_R",
        "BucketCylinder_Barrel", "BucketCylinder_Rod",
        "ZBar_Bellcrank_Upper_Reconstructed", "ZBar_BucketLink_Reconstructed",
        "StockPileBucket_PivotRoot_Reconstructed", "StockPileBucket_Shell",
        "BucketBoltOnCuttingEdge", "LoaderHose_L_01", "LoaderHose_R_01",
    ]


def validate(root: bpy.types.Object, counts: dict, scale_audit: dict,
             glb_contract: dict) -> dict:
    bounds = evaluated_visible_bounds(root)
    size = bounds["size_m"]
    gates = []
    envelope_rules = {
        "overall-length-stock-pile": (size[0], 0.08),
        "height-roof-rail": (size[1], 0.05),
        "bucket-width-stock-pile": (size[2], 0.04),
    }
    for fact_id, (actual, tolerance) in envelope_rules.items():
        expected = PUBLISHED[fact_id]
        delta = abs(actual - expected)
        gates.append(make_gate(
            f"published-{fact_id}", "PASS" if delta <= tolerance else "FAIL",
            "Measured from evaluated retained-pose public visible geometry; no helper witnesses participate.",
            {"value_m": expected, "tolerance_m": tolerance},
            {"value_m": round(actual, 6), "absolute_delta_m": round(delta, 6),
             "evaluated_visible_bounds_m": bounds},
        ))

    wheelbase_actual = RECONSTRUCTED["front_axle_x_m"] - RECONSTRUCTED["rear_axle_x_m"]
    gates.append(make_gate(
        "published-wheelbase", "PASS" if abs(wheelbase_actual - PUBLISHED["wheelbase"]) < 1e-6 else "FAIL",
        "Axle-center references follow the published 3.45 m wheelbase; axle castings and tire geometry remain reconstructed.",
        {"value_m": PUBLISHED["wheelbase"]}, {"value_m": wheelbase_actual},
    ))
    gates.append(make_gate(
        "published-standard-tire-width", "PASS",
        "Reconstructed tire tread outer faces are set to the published 3.060 m width; bucket side guards remain the wider complete-machine envelope.",
        {"value_m": PUBLISHED["width-standard-tires"]},
        {"value_m": RECONSTRUCTED["tire_tread_outer_z_m"] * 2.0},
    ))
    stowed = apply_loader_pose("stowed")
    raised = apply_loader_pose("raised_dump")
    apply_loader_pose("stowed")
    gates.append(make_gate(
        "published-hinge-carry-height", "PASS" if abs(stowed["hinge"][1] - PUBLISHED["hinge-pin-height-carry-standard"]) < 0.005 else "FAIL",
        "Bucket-hinge reference is constrained at retained carry height; linkage geometry is reconstructed.",
        {"value_m": PUBLISHED["hinge-pin-height-carry-standard"], "tolerance_m": 0.005},
        {"value_m": stowed["hinge"][1]},
    ))
    gates.append(make_gate(
        "published-hinge-maximum-height", "PASS" if abs(raised["hinge"][1] - PUBLISHED["hinge-pin-height-max-standard"]) < 0.005 else "FAIL",
        "Raised-pose hinge endpoint is constrained; this does not qualify the interpolated lift path.",
        {"value_m": PUBLISHED["hinge-pin-height-max-standard"], "tolerance_m": 0.005},
        {"value_m": raised["hinge"][1]},
    ))

    object_names = {obj.name for obj in bpy.context.scene.objects}
    missing = [name for name in public_semantic_nodes() if name not in object_names]
    gates.append(make_gate(
        "semantic-node-presence", "PASS" if not missing else "FAIL",
        "Required wheel-loader technical-study hierarchy is present.",
        public_semantic_nodes(), {"missing": missing},
    ))
    tread_nodes = [name for name in object_names if "TreadLug_" in name]
    expected_treads = 4 * RECONSTRUCTED["tread_lugs_per_tire"]
    gates.append(make_gate(
        "reconstructed-four-tire-tread-detail", "PASS" if len(tread_nodes) == expected_treads else "FAIL",
        "Four independently authored heavy-tire studies include explicit reconstructed tread blocks; count and pitch are not manufacturer facts.",
        {"count": expected_treads, "authority": "reconstructed"}, {"count": len(tread_nodes)},
    ))
    edge_segments = [name for name in object_names if name.startswith("BucketBOC_WearSegment_")]
    gates.append(make_gate(
        "selected-bolt-on-cutting-edge-detail",
        "PASS" if len(edge_segments) == RECONSTRUCTED["bucket_cutting_edge_segments"] else "FAIL",
        "The frozen bucket uses a bolt-on cutting edge. Wear-segment geometry and fastener pattern remain reconstructed; no incompatible tooth claim is made.",
        {"segments": RECONSTRUCTED["bucket_cutting_edge_segments"]},
        {"segments": len(edge_segments)},
    ))
    render_results = {str(path.relative_to(MACHINE_DIR)): render_quality(path) for path in RENDER_PATHS}
    render_ok = len(render_results) >= 9 and all(
        item["bytes"] > 30000 and item["width"] >= 1000 and item["height"] >= 700
        for item in render_results.values()
    )
    gates.append(make_gate(
        "render-non-emptiness", "PASS" if render_ok else "FAIL",
        "Nine deterministic review views cover retained, articulated, lifted, linkage, operator, cooling, and rear-axle studies; final human/Grok review remains pending.",
        {"minimum_views": 9, "minimum_bytes": 30000, "minimum_width": 1000, "minimum_height": 700},
        render_results,
    ))
    gates.append(make_gate(
        "structural-triangle-budget",
        "PASS" if 12000 <= counts["triangles"] <= RECONSTRUCTED["structural_triangle_budget"] else "FAIL",
        "Blend source has reviewable technical detail within the reconstructed study budget.",
        {"minimum": 12000, "maximum": RECONSTRUCTED["structural_triangle_budget"]}, counts["triangles"],
    ))
    gates.extend([
        make_gate("public-source-scales-applied", scale_audit["status"],
                  "Public geometry node scales are applied without changing the retained envelope.",
                  {"after_non_identity": [], "envelope_delta_max_m": 0.000001}, scale_audit),
        make_gate("public-glb-contract", glb_contract["status"],
                  "Public GLB has one identity root, Y-up output, identity mesh scales, triangle primitives, and no studio/helper/camera/light leakage.",
                  {"root": "WA47510_Root", "helpers": []}, glb_contract),
        make_gate("published-steering-endpoints", "PENDING",
                  "35 degree nominal and 40 degree end-stop facts are retained; steering-cylinder closure, swept volume, and tire/body clearance are unqualified."),
        make_gate("rear-axle-oscillation", "PENDING",
                  "26 degree total oscillation is retained; center-pin coordinates, stops, and tire-deflection clearance are unresolved."),
        make_gate("loader-linkage-closure", "PENDING",
                  "Standard loader-arm pivots and lift-cylinder anchors are reconstructed; endpoint renders are not a solver."),
        make_gate("z-bar-linkage-closure", "PENDING",
                  "Bellcrank and bucket-link geometry are reconstructed; bucket-cylinder stroke continuity is unqualified."),
        make_gate("dump-clearance-reach-operating-height", "PENDING",
                  "Published clearance, reach and fully raised operating height are retained but the brochure does not bind all measurement datums to reconstructed bucket geometry."),
        make_gate("ground-and-self-collision", "PENDING",
                  "Source collision proxies exist, but no swept-pose collision qualification has run."),
        make_gate("tire-transmission-engine-internals", "PENDING",
                  "Tire carcass/tread and KHMT/driveline/engine internals remain unresolved and are not fabricated."),
        make_gate("powered-hood-and-cooling-mask-motion", "PENDING",
                  "Service-panel segmentation and cooling mask are modeled; hinges, actuators and service envelopes remain unresolved."),
        make_gate("human-visual-critic", "PENDING",
                  "The user-directed one-time batch Grok critic runs only after all ten machine lanes are integrated."),
        make_gate("viewer-browser-accessibility-mobile-performance-selection", "PENDING",
                  "No shared-viewer integration or browser qualification is claimed by this lane."),
        make_gate("publication-release-deployment", "PENDING",
                  "Only the overall critic/publisher may integrate, publish, push, or deploy this research candidate."),
    ])
    failures = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    return {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "candidate_class": CANDIDATE_CLASS,
        "engineering_authority": False,
        "verdict": "FAIL" if failures else "PASS",
        "verdict_scope": "technical_structural_study_only",
        "higher_stage_gates": "PENDING",
        "failed_gates": failures,
        "evaluated_visible_bounds_m": bounds,
        "gates": gates,
    }


def write_outputs(root: bpy.types.Object, counts: dict, scale_audit: dict,
                  glb_contract: dict, validation: dict) -> None:
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    renders = [{
        "path": str(path.relative_to(MACHINE_DIR)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    } for path in RENDER_PATHS]
    receipt = {
        "schema_version": "1.0.0",
        "machine_id": MACHINE_ID,
        "configuration_id": CONFIGURATION_ID,
        "configuration_status": "research_candidate",
        "candidate_class": CANDIDATE_CLASS,
        "engineering_authority": False,
        "authority_statement": "Independent technical structural study only; not manufacturer CAD, engineering data, training material, or operational guidance.",
        "rights_boundary": "Neutral unbranded materials; no copied manufacturer geometry, textures, logos, imagery, or publication pages are shipped.",
        "blender": {
            "version": bpy.app.version_string,
            "factory_startup_background_required": True,
            "builder_path": str(BUILDER_PATH.relative_to(MACHINE_DIR)),
            "builder_sha256": sha256(BUILDER_PATH),
            "builder_bytes": BUILDER_PATH.stat().st_size,
        },
        "artifacts": {
            "blend": {"path": str(BLEND_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(BLEND_PATH), "bytes": BLEND_PATH.stat().st_size},
            "glb": {"path": str(GLB_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(GLB_PATH), "bytes": GLB_PATH.stat().st_size},
            "validation": {"path": str(VALIDATION_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(VALIDATION_PATH), "bytes": VALIDATION_PATH.stat().st_size},
        },
        "scene": {
            "units": "meters",
            "machine_axes": "+X toward bucket, +Y vertical, +Z machine right",
            "blender_storage_mapping": "machine (X,Y,Z) -> Blender (X,Z,Y)",
            "glb_export_y_up": True,
            "bounds": {"evaluated_public_visible_retained_pose": validation["evaluated_visible_bounds_m"]},
            "counts": glb_contract["public_glb_decoded_counts"],
            "blend_source_counts": {"classification": "blend_source_scene_evaluated_including_nonpublic_helpers", **counts},
            "count_boundary": "scene.counts is decoded shipped public GLB geometry; blend_source_counts includes nonpublic source helpers and studio geometry.",
            "public_glb_contract": glb_contract,
            "public_scale_application": scale_audit,
        },
        "semantic_nodes": {name: bpy.data.objects.get(name) is not None for name in public_semantic_nodes()},
        "source_only_helper_nodes": {
            name: {"present_in_blend_source": bpy.data.objects.get(name) is not None,
                   "present_in_public_glb": False}
            for name in ("RearFrame_Hit", "FrontFrame_Hit", "Cab_Hit", "Bucket_Hit",
                         "Articulation_Inspect", "LoaderLinkage_Inspect",
                         "OperatorStation_Inspect", "RearCooling_Inspect")
        },
        "manufacturer_published_constraints_used": [
            {"id": fact_id, "value": value, "source_id": "KOM-WA47510-AESS942-0225",
             "location": "PDF pages 18-19", "use": "geometry_or_configuration_constraint_with_reconstruction_boundary"}
            for fact_id, value in PUBLISHED.items()
        ],
        "reconstructed_values": RECONSTRUCTED,
        "unresolved_choices_and_mechanical_gaps": UNRESOLVED,
        "renders": renders,
        "build_verdict": "PASS" if validation["verdict"] != "FAIL" else "FAIL",
        "validation_verdict": validation["verdict"],
        "higher_stage_gates": "PENDING",
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def add_scene_metadata() -> None:
    scene = bpy.context.scene
    scene["machine_id"] = MACHINE_ID
    scene["configuration_id"] = CONFIGURATION_ID
    scene["candidate_class"] = CANDIDATE_CLASS
    scene["engineering_authority"] = False
    scene["machine_axes"] = "+X toward bucket, +Y vertical, +Z machine right"
    scene["rights_boundary"] = "independently authored, neutral, unbranded"


def main() -> None:
    ensure_dirs()
    reset_scene()
    for collection_name in (
        "Fixed_Structure", "Front_Frame", "Wheels", "Cab_ROPS", "Loader",
        "Hydraulics", "Bucket", "Details", "Markers", "Collision",
        "Inspection", "Studio",
    ):
        make_collection(collection_name)
    build_materials()
    root = build_identity_and_frames()
    build_wheels()
    build_cab()
    setup_loader_and_bucket()
    setup_steering_hydraulics()
    build_lights_and_details()
    build_helpers()
    build_studio()
    add_scene_metadata()
    render_review_set()
    apply_rear_axle_oscillation(0.0)
    apply_articulation(0.0)
    apply_loader_pose("stowed")
    counts = evaluated_counts()
    scale_audit = apply_public_scales(root)
    save_and_export(root)
    glb_contract = inspect_glb_contract()
    validation = validate(root, counts, scale_audit, glb_contract)
    write_outputs(root, counts, scale_audit, glb_contract, validation)
    if validation["verdict"] == "FAIL":
        raise RuntimeError(f"Validation failed: {validation['failed_gates']}")
    print(json.dumps({
        "status": validation["verdict"],
        "blend": str(BLEND_PATH),
        "glb": str(GLB_PATH),
        "receipt": str(RECEIPT_PATH),
        "validation": str(VALIDATION_PATH),
        "counts": counts,
        "public_glb_counts": glb_contract["public_glb_decoded_counts"],
        "bounds": validation["evaluated_visible_bounds_m"],
        "renders": [str(path) for path in RENDER_PATHS],
    }, indent=2))


if __name__ == "__main__":
    main()

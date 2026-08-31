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
FACTS_PATH = MACHINE_DIR / "evidence/facts.json"
MECHANISM_PATH = MACHINE_DIR / "mechanism.json"


# Machine axes declared by mechanism.json. Blender storage keeps world Z up:
# machine (X longitudinal, Y vertical, Z right) -> Blender (X, Z, Y).
def mv(x: float, y: float, z: float) -> Vector:
    return Vector((x, z, y))


def load_manufacturer_facts() -> tuple[dict[str, dict], dict[str, float | int]]:
    """Bind geometry inputs to the admitted, source-addressed fact records.

    A missing, duplicate, non-published, or non-numeric record is a build error;
    the builder therefore cannot silently drift from evidence/facts.json.
    """
    document = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    records: dict[str, dict] = {}
    for record in document.get("facts", []):
        fact_id = record.get("id")
        if not isinstance(fact_id, str) or not fact_id or fact_id in records:
            raise RuntimeError(f"Invalid or duplicate manufacturer fact id: {fact_id!r}")
        if record.get("authority") != "manufacturer_published":
            raise RuntimeError(f"{fact_id}: builder accepts manufacturer_published facts only")
        if not isinstance(record.get("value"), (int, float)):
            raise RuntimeError(f"{fact_id}: numeric value required")
        for field in ("unit", "source_id", "location"):
            if not isinstance(record.get(field), str) or not record[field]:
                raise RuntimeError(f"{fact_id}: source-addressed {field} required")
        records[fact_id] = record
    return records, {fact_id: record["value"] for fact_id, record in records.items()}


FACT_RECORDS, PUBLISHED = load_manufacturer_facts()

# Only facts that actually constrain the selected configuration or generated
# study are promoted into the receipt. Operating mass and static tipping loads
# remain browseable evidence but are not geometry inputs.
USED_FACT_IDS = (
    "overall-length-stock-pile", "bucket-width-stock-pile",
    "width-standard-tires", "wheelbase", "hinge-pin-height-max-standard",
    "hinge-pin-height-carry-standard", "ground-clearance",
    "hitch-height-standard", "height-top-stack", "height-rops-cab",
    "height-roof-rail", "bucket-capacity-heaped", "bucket-capacity-struck",
    "bucket-weight", "dump-clearance-stock-pile", "dump-reach-stock-pile",
    "operating-height-stock-pile", "steering-angle-nominal",
    "steering-angle-max-stop", "rear-axle-oscillation",
    "lift-cylinder-count", "lift-cylinder-bore", "lift-cylinder-stroke",
    "bucket-cylinder-count", "bucket-cylinder-bore", "bucket-cylinder-stroke",
    "steering-cylinder-count", "steering-cylinder-bore",
    "steering-cylinder-stroke",
)
missing_used_facts = sorted(set(USED_FACT_IDS) - set(FACT_RECORDS))
if missing_used_facts:
    raise RuntimeError(f"Builder-required fact records missing: {missing_used_facts}")


RECONSTRUCTED = {
    "rear_visible_x_m": -3.795,
    "bucket_front_visible_x_m": 5.39,
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
    "loader_rear_pivot_xyz_m": [0.28, 1.74, 0.0],
    "stowed_arm_elbow_xyz_m": [1.55, 1.23, 0.0],
    "stowed_bucket_hinge_xyz_m": [3.23, 0.58, 0.0],
    "raised_bucket_hinge_xyz_m": [2.05, 4.37, 0.0],
    "stowed_bucket_rotation_blender_y_deg": 14.85,
    "raised_dump_rotation_blender_y_deg": 45.0,
    "bucket_link_ear_local_xy_m": [-0.10, 0.25],
    "loader_lift_barrel_length_m": 1.05,
    "loader_lift_rod_insertion_m": 0.78,
    "bucket_cylinder_barrel_length_m": 0.74,
    "bucket_cylinder_rod_insertion_m": 0.53,
    "steering_cylinder_barrel_length_m": 0.66,
    "steering_cylinder_rod_insertion_m": 0.48,
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
        # Newly linked empties do not have a current matrix_world until the
        # dependency graph updates. Without this update, preserve_world would
        # collapse every nested pivot to its parent's origin.
        bpy.context.view_layer.update()
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
                 vertices=32, parent=None, bevel=True,
                 parent_local=False) -> bpy.types.Object:
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
        set_parent(obj, parent, preserve_world=not parent_local)
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
    local_size = Vector((
        max(vertex.co.x for vertex in obj.data.vertices)
        - min(vertex.co.x for vertex in obj.data.vertices),
        max(vertex.co.y for vertex in obj.data.vertices)
        - min(vertex.co.y for vertex in obj.data.vertices),
        max(vertex.co.z for vertex in obj.data.vertices)
        - min(vertex.co.z for vertex in obj.data.vertices),
    ))
    scale = Matrix.Diagonal(Vector((direction.length / local_size.x,
                                    lateral / local_size.y,
                                    vertical / local_size.z, 1.0)))
    obj.matrix_world = Matrix.Translation((pa + pb) * 0.5) @ rotation @ scale


def beam_axis_endpoints(obj: bpy.types.Object) -> list[Vector]:
    """Return the two world endpoints of a unit beam's shipped mesh axis."""
    endpoints = (min(vertex.co.x for vertex in obj.data.vertices),
                 max(vertex.co.x for vertex in obj.data.vertices))
    return [obj.matrix_world @ Vector((endpoint, 0.0, 0.0))
            for endpoint in endpoints]


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
    local_radius_x = 0.5 * (
        max(vertex.co.x for vertex in obj.data.vertices)
        - min(vertex.co.x for vertex in obj.data.vertices))
    local_radius_y = 0.5 * (
        max(vertex.co.y for vertex in obj.data.vertices)
        - min(vertex.co.y for vertex in obj.data.vertices))
    local_depth = (
        max(vertex.co.z for vertex in obj.data.vertices)
        - min(vertex.co.z for vertex in obj.data.vertices))
    scale = Matrix.Diagonal(Vector((radius / local_radius_x,
                                    radius / local_radius_y,
                                    direction.length / local_depth, 1.0)))
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
    root = add_empty("Machine_Root", (0.0, 0.0, 0.0), "Fixed_Structure", 0.30)
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
    add_prism_xy("RearCounterweight_Mass", [(-3.795, 0.52), (-3.715, 1.30),
                 (-3.465, 1.72), (-3.025, 1.76), (-2.885, 0.68)], 0.0, 2.86,
                 "PanelWarmGrey", "Fixed_Structure", rear_root, bevel=0.0)
    add_box("RearCounterweight_AdditionalLower", (-3.565, 0.49, 0.0),
            (0.46, 0.33, 2.73), "StructuralSteel", "Fixed_Structure", 0.07, rear_root)
    add_box("RearBumper_ExactEnvelope", (-3.655, 0.61, 0.0),
            (0.28, 0.30, 2.82), "DarkSteel", "Fixed_Structure", 0.045, rear_root)
    add_box("RearBellyGuard", (-1.82, 0.595, 0.0), (3.34, 0.15, 1.03),
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
    add_box("RearCoolingMask", (-3.742, 1.88, 0.0), (0.055, 1.18, 2.10),
            "DarkSteel", "Fixed_Structure", 0.018, rear_root)
    for index, y in enumerate(tuple(1.35 + 0.10 * i for i in range(11))):
        add_box(f"RearCoolingGrille_H_{index + 1:02d}", (-3.774, y, 0.0),
                (0.026, 0.025, 1.88), "StructuralSteel", "Details", 0.004, rear_root)
    for index, z in enumerate((-0.82, -0.55, -0.28, 0.0, 0.28, 0.55, 0.82)):
        add_box(f"RearCoolingGrille_V_{index + 1:02d}", (-3.776, 1.88, z),
                (0.024, 1.04, 0.025), "StructuralSteel", "Details", 0.004, rear_root)
    add_cylinder("ExhaustStack", (-2.62, 2.96, 0.77), 0.09, 0.86, "y",
                 "DarkSteel", "Details", 28, rear_root)
    add_cone("ExhaustRainCap", (-2.62, 3.42, 0.77), 0.13, 0.08, 0.06, "y",
             "StructuralSteel", "Details", 28, rear_root)
    add_cylinder("AirPrecleaner_Body", (-1.92, 2.95, -0.78), 0.13, 0.60, "y",
                 "DarkSteel", "Details", 32, rear_root)
    add_cone("AirPrecleaner_Cap", (-1.92, 3.27, -0.78), 0.20, 0.13, 0.10, "y",
             "StructuralSteel", "Details", 32, rear_root)

    # Front articulated frame and fixed front axle.
    add_prism_xy("FrontFrame_Main", [(-0.12, 0.62), (0.15, 1.36),
                 (1.82, 1.47), (2.42, 1.11), (2.55, 0.62)], 0.0, 1.34,
                 "WarmGraphite", "Front_Frame", front_root, bevel=0.07)
    add_box("FrontFrame_BellyPan", (1.08, 0.60, 0.0), (2.26, 0.16, 1.22),
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
    add_cylinder(f"{name_prefix}SidewallOuter_{suffix}", (x, y, side * 1.5075),
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
    for axle, x, axle_parent in (
        ("Rear", RECONSTRUCTED["rear_axle_x_m"], ART["rear_axle"]),
        ("Front", RECONSTRUCTED["front_axle_x_m"], ART["front_root"]),
    ):
        for side, suffix in ((-1, "L"), (1, "R")):
            wheel_root = add_empty(
                f"{axle}Wheel_{suffix}_Pivot_ROOT",
                (x, RECONSTRUCTED["wheel_center_y_m"],
                 side * RECONSTRUCTED["tire_center_z_m"]),
                "Wheels", 0.14, axle_parent,
            )
            wheel_root["joint_axis_machine"] = "+Z"
            wheel_root["authority"] = "reconstructed visual wheel rotation"
            ART[f"{axle.lower()}_wheel_{suffix}"] = wheel_root
            build_wheel(axle, x, side, wheel_root)

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


def rotate_xy(point: tuple[float, float], pivot: tuple[float, float],
              angle_rad: float) -> tuple[float, float]:
    dx, dy = point[0] - pivot[0], point[1] - pivot[1]
    cosine, sine = math.cos(angle_rad), math.sin(angle_rad)
    return (pivot[0] + dx * cosine - dy * sine,
            pivot[1] + dx * sine + dy * cosine)


def loader_lift_angle_rad() -> float:
    pivot = tuple(RECONSTRUCTED["loader_rear_pivot_xyz_m"][:2])
    carry = tuple(RECONSTRUCTED["stowed_bucket_hinge_xyz_m"][:2])
    radius = math.dist(pivot, carry)
    raised_dy = PUBLISHED["hinge-pin-height-max-standard"] - pivot[1]
    if abs(raised_dy) >= radius:
        raise RuntimeError("Reconstructed loader radius cannot reach published hinge height")
    carry_angle = math.atan2(carry[1] - pivot[1], carry[0] - pivot[0])
    raised_angle = math.asin(raised_dy / radius)
    return raised_angle - carry_angle


def loader_pose_geometry(pose: str) -> dict:
    if pose not in {"stowed", "raised_dump"}:
        raise ValueError(pose)
    alpha = 0.0 if pose == "stowed" else loader_lift_angle_rad()
    pivot = tuple(RECONSTRUCTED["loader_rear_pivot_xyz_m"][:2])
    carry_hinge = tuple(RECONSTRUCTED["stowed_bucket_hinge_xyz_m"][:2])
    carry_elbow = tuple(RECONSTRUCTED["stowed_arm_elbow_xyz_m"][:2])
    hinge = rotate_xy(carry_hinge, pivot, alpha)
    elbow = rotate_xy(carry_elbow, pivot, alpha)
    bucket_blender_world_deg = (
        RECONSTRUCTED["stowed_bucket_rotation_blender_y_deg"]
        if pose == "stowed" else RECONSTRUCTED["raised_dump_rotation_blender_y_deg"]
    )

    # Closed reconstructed Z-bar in the loader-arm reference frame. The lower
    # bellcrank radius and bucket-link length remain invariant between poses.
    bellcrank_pivot_ref = (1.65, 1.25)
    bellcrank_radius = 0.40
    bucket_ear_local = tuple(RECONSTRUCTED["bucket_link_ear_local_xy_m"])
    stowed_phi = math.radians(-160.0)
    stowed_bucket_machine = math.radians(-RECONSTRUCTED["stowed_bucket_rotation_blender_y_deg"])
    stowed_ear_ref = (
        carry_hinge[0] + bucket_ear_local[0] * math.cos(stowed_bucket_machine)
        - bucket_ear_local[1] * math.sin(stowed_bucket_machine),
        carry_hinge[1] + bucket_ear_local[0] * math.sin(stowed_bucket_machine)
        + bucket_ear_local[1] * math.cos(stowed_bucket_machine),
    )
    stowed_lower_ref = (
        bellcrank_pivot_ref[0] + bellcrank_radius * math.cos(stowed_phi),
        bellcrank_pivot_ref[1] + bellcrank_radius * math.sin(stowed_phi),
    )
    link_length = math.dist(stowed_lower_ref, stowed_ear_ref)

    bucket_machine_relative = math.radians(-bucket_blender_world_deg) - alpha
    ear_ref = (
        carry_hinge[0] + bucket_ear_local[0] * math.cos(bucket_machine_relative)
        - bucket_ear_local[1] * math.sin(bucket_machine_relative),
        carry_hinge[1] + bucket_ear_local[0] * math.sin(bucket_machine_relative)
        + bucket_ear_local[1] * math.cos(bucket_machine_relative),
    )
    dx = ear_ref[0] - bellcrank_pivot_ref[0]
    dy = ear_ref[1] - bellcrank_pivot_ref[1]
    distance = math.hypot(dx, dy)
    along = (bellcrank_radius ** 2 - link_length ** 2 + distance ** 2) / (2.0 * distance)
    height_sq = bellcrank_radius ** 2 - along ** 2
    if height_sq < -1e-9:
        raise RuntimeError(f"{pose}: reconstructed Z-bar circles do not intersect")
    height = math.sqrt(max(0.0, height_sq))
    midpoint = (bellcrank_pivot_ref[0] + along * dx / distance,
                bellcrank_pivot_ref[1] + along * dy / distance)
    candidates = [
        (midpoint[0] + sign * height * -dy / distance,
         midpoint[1] + sign * height * dx / distance)
        for sign in (1.0, -1.0)
    ]
    target_phi = stowed_phi if pose == "stowed" else math.radians(-102.0)
    lower_ref = min(
        candidates,
        key=lambda point: abs(math.atan2(point[1] - bellcrank_pivot_ref[1],
                                         point[0] - bellcrank_pivot_ref[0]) - target_phi),
    )
    phi = math.atan2(lower_ref[1] - bellcrank_pivot_ref[1],
                     lower_ref[0] - bellcrank_pivot_ref[0])
    upper_radius = 0.45
    upper_ref = (bellcrank_pivot_ref[0] - upper_radius * math.cos(phi),
                 bellcrank_pivot_ref[1] - upper_radius * math.sin(phi))
    bucket_cylinder_base_ref = (0.40, 1.80)

    return {
        "pose": pose,
        "alpha_rad": alpha,
        "alpha_deg": math.degrees(alpha),
        "pivot": (*pivot, 0.0),
        "hinge": (*hinge, 0.0),
        "elbow": (*elbow, 0.0),
        "bucket_rotation_blender_y_deg": bucket_blender_world_deg,
        "bellcrank_pivot": (*rotate_xy(bellcrank_pivot_ref, pivot, alpha), 0.0),
        "bellcrank_lower": (*rotate_xy(lower_ref, pivot, alpha), 0.0),
        "bellcrank_upper": (*rotate_xy(upper_ref, pivot, alpha), 0.0),
        "bucket_ear": (*rotate_xy(ear_ref, pivot, alpha), 0.0),
        "bucket_link_length_m": link_length,
        "bucket_cylinder_base": (*rotate_xy(bucket_cylinder_base_ref, pivot, alpha), 0.0),
        "bellcrank_angle_deg": math.degrees(phi),
    }


def place_telescoping_pair(barrel: bpy.types.Object, rod: bpy.types.Object,
                           base: tuple[float, float, float],
                           moving: tuple[float, float, float],
                           barrel_length: float, rod_insertion: float,
                           barrel_radius: float, rod_radius: float) -> dict:
    start, end = Vector(base), Vector(moving)
    direction = end - start
    length = direction.length
    if length <= max(barrel_length, rod_insertion):
        raise RuntimeError(f"{barrel.name}: invalid telescoping length {length:.6f} m")
    unit = direction.normalized()
    barrel_end = start + unit * barrel_length
    rod_start = start + unit * rod_insertion
    place_cylinder(barrel, tuple(start), tuple(barrel_end), barrel_radius)
    place_cylinder(rod, tuple(rod_start), tuple(end), rod_radius)
    return {
        "anchor_distance_m": length,
        "barrel_length_m": barrel_length,
        "rod_visible_length_m": length - rod_insertion,
        "barrel_rod_overlap_m": barrel_length - rod_insertion,
        "base_anchor": [round(value, 6) for value in base],
        "moving_anchor": [round(value, 6) for value in moving],
    }


def measure_telescoping_pair(barrel: bpy.types.Object, rod: bpy.types.Object,
                             base_clevis: bpy.types.Object,
                             moving_clevis: bpy.types.Object) -> dict:
    """Measure the shipped mesh endpoints against clevis transforms."""
    base = Vector(base_clevis.matrix_world.translation)
    moving = Vector(moving_clevis.matrix_world.translation)
    barrel_axis = (min(vertex.co.z for vertex in barrel.data.vertices),
                   max(vertex.co.z for vertex in barrel.data.vertices))
    rod_axis = (min(vertex.co.z for vertex in rod.data.vertices),
                max(vertex.co.z for vertex in rod.data.vertices))
    barrel_endpoints = [barrel.matrix_world @ Vector((0.0, 0.0, endpoint))
                        for endpoint in barrel_axis]
    rod_endpoints = [rod.matrix_world @ Vector((0.0, 0.0, endpoint))
                     for endpoint in rod_axis]
    barrel_base = min(barrel_endpoints, key=lambda point: (point - base).length)
    rod_moving = min(rod_endpoints, key=lambda point: (point - moving).length)
    anchor_distance = (moving - base).length
    barrel_length = (barrel_endpoints[1] - barrel_endpoints[0]).length
    rod_mesh_length = (rod_endpoints[1] - rod_endpoints[0]).length
    return {
        "anchor_distance_m": anchor_distance,
        "barrel_length_m": barrel_length,
        "rod_visible_length_m": rod_mesh_length,
        "barrel_rod_overlap_m": barrel_length + rod_mesh_length - anchor_distance,
        "base_closure_residual_m": (barrel_base - base).length,
        "moving_closure_residual_m": (rod_moving - moving).length,
        "base_anchor": [round(base.x, 6), round(base.z, 6), round(base.y, 6)],
        "moving_anchor": [round(moving.x, 6), round(moving.z, 6), round(moving.y, 6)],
    }


def cylinder_mesh_bore(obj: bpy.types.Object) -> float:
    """Measure diameter from baked local radial mesh extents."""
    x_values = [vertex.co.x for vertex in obj.data.vertices]
    y_values = [vertex.co.y for vertex in obj.data.vertices]
    return 0.5 * ((max(x_values) - min(x_values))
                  + (max(y_values) - min(y_values)))


def setup_loader_and_bucket() -> None:
    front_root = ART["front_root"]
    pivot = tuple(RECONSTRUCTED["loader_rear_pivot_xyz_m"])
    loader_root = add_empty("LoaderArm_LiftPivot_ROOT_Reconstructed", pivot,
                            "Loader", 0.20, front_root)
    loader_root["joint_axis_machine"] = "+Z"
    loader_root["authority"] = "reconstructed; endpoint heights source-constrained"
    ART["loader_root"] = loader_root

    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * RECONSTRUCTED["loader_arm_lateral_center_m"]
        side_pivot = add_empty(f"LoaderArmRearPivot_{suffix}_Reconstructed",
                               (pivot[0], pivot[1], z), "Loader", 0.12, loader_root)
        side_pivot["authority"] = "reconstructed"
        ART[f"arm_rear_{suffix}"] = add_unit_beam(
            f"StandardLoaderArmRear_{suffix}", "IndustrialBronze", "Loader", 0.045, loader_root)
        ART[f"arm_front_{suffix}"] = add_unit_beam(
            f"StandardLoaderArmFront_{suffix}", "IndustrialBronze", "Loader", 0.045, loader_root)
        ART[f"arm_web_{suffix}"] = add_unit_beam(
            f"StandardLoaderArmLowerWeb_{suffix}", "WarmGraphite", "Loader", 0.035, loader_root)
        # Barrel stays with the fixed front frame; rod follows the loader arm.
        ART[f"lift_barrel_{suffix}"] = add_unit_cylinder(
            f"LiftCylinder_Barrel_{suffix}", "WarmGraphite", "Hydraulics", 36, front_root)
        ART[f"lift_rod_{suffix}"] = add_unit_cylinder(
            f"LiftCylinder_Rod_{suffix}", "CylinderRod", "Hydraulics", 32, loader_root)
        ART[f"lift_base_clevis_{suffix}"] = add_uv_sphere(
            f"LiftCylinder_BaseClevis_{suffix}",
            (0.20, 1.20, side * 0.70), 0.105,
            "StructuralSteel", "Hydraulics", front_root, 24, 12)
        ART[f"lift_arm_clevis_{suffix}"] = add_uv_sphere(
            f"LiftCylinder_ArmClevis_{suffix}",
            (1.65, 1.06, side * 0.70), 0.092,
            "StructuralSteel", "Hydraulics", loader_root, 24, 12)
        for bundle in (1, 2):
            ART[f"hose_{suffix}_{bundle}"] = add_polyline_tube(
                f"LoaderHose_{suffix}_{bundle:02d}",
                [(0.18, 1.24, z), (0.72, 1.62, z),
                 (1.65, 1.34, z), (3.02, 0.88, z)],
                RECONSTRUCTED["loader_hose_visual_diameter_m"] * 0.5,
                "Rubber", "Hydraulics", front_root)

    ART["arm_crossmember"] = add_unit_beam(
        "LoaderArmCrossmember", "StructuralSteel", "Loader", 0.04, loader_root)
    ART["bucket_crossmember"] = add_unit_beam(
        "BucketHingeCrossmember", "DarkSteel", "Loader", 0.035, loader_root)
    ART["tilt_barrel"] = add_unit_cylinder(
        "BucketCylinder_Barrel", "WarmGraphite", "Hydraulics", 40, loader_root)

    stowed_geometry = loader_pose_geometry("stowed")
    zbar_root = add_empty("ZBar_Bellcrank_Pivot_ROOT_Reconstructed",
                          stowed_geometry["bellcrank_pivot"], "Loader", 0.16, loader_root)
    zbar_root["joint_axis_machine"] = "+Z"
    zbar_root["authority"] = "reconstructed closed four-bar study"
    ART["zbar_root"] = zbar_root
    ART["tilt_rod"] = add_unit_cylinder(
        "BucketCylinder_Rod", "CylinderRod", "Hydraulics", 36, zbar_root)
    ART["tilt_base_clevis"] = add_uv_sphere(
        "BucketCylinder_BaseClevis", stowed_geometry["bucket_cylinder_base"], 0.120,
        "StructuralSteel", "Hydraulics", loader_root, 28, 14)
    ART["tilt_moving_clevis"] = add_uv_sphere(
        "BucketCylinder_BellcrankClevis", stowed_geometry["bellcrank_upper"], 0.105,
        "StructuralSteel", "Hydraulics", zbar_root, 28, 14)
    ART["bellcrank_a"] = add_unit_beam(
        "ZBar_Bellcrank_Upper_Reconstructed", "StructuralSteel", "Loader", 0.035, zbar_root)
    ART["bellcrank_b"] = add_unit_beam(
        "ZBar_Bellcrank_Lower_Reconstructed", "StructuralSteel", "Loader", 0.035, zbar_root)
    ART["bucket_link"] = add_unit_beam(
        "ZBar_BucketLink_Reconstructed", "DarkSteel", "Loader", 0.028, loader_root)
    add_cylinder("ZBar_BellcrankPivotCap", stowed_geometry["bellcrank_pivot"],
                 0.14, 0.28, "z", "CylinderRod", "Loader", 32, loader_root)

    bucket_root = add_empty("StockPileBucket_PivotRoot_Reconstructed",
                            tuple(RECONSTRUCTED["stowed_bucket_hinge_xyz_m"]),
                            "Bucket", 0.17, loader_root)
    bucket_root["joint_axis_machine"] = "+Z"
    bucket_root["authority"] = "reconstructed constrained by selected 4.2 m3 stock-pile bucket facts"
    ART["bucket_root"] = bucket_root

    # Deep curved-side silhouette approximated by a faceted, independently
    # authored shell. It is not reverse-engineered CAD or a scale tracing.
    bucket_polygon = [
        (-0.28, 0.08), (-0.02, 2.35), (0.25, 2.38), (0.48, 1.82),
        (1.18, 1.38), (1.72, 0.58), (1.79, -0.02),
        (1.54, -0.13), (0.86, 0.00), (0.16, 0.22),
    ]
    add_prism_xy("StockPileBucket_Shell", bucket_polygon, 0.0,
                 RECONSTRUCTED["bucket_visual_width_m"], "IndustrialBronze",
                 "Bucket", bucket_root, local=True, bevel=0.035)
    for side, suffix in ((-1, "L"), (1, "R")):
        z = side * 1.565
        add_prism_xy(f"BucketSideGuard_{suffix}",
                     [(-0.30, 0.05), (-0.02, 2.35), (0.25, 2.38), (0.47, 1.87),
                      (1.24, 1.42), (1.80, 0.56), (1.82, -0.06),
                      (1.53, -0.08), (0.30, 0.12)],
                     z, 0.040, "WarmGraphite", "Bucket", bucket_root,
                     local=True, bevel=0.018)
        add_box(f"BucketTopCornerGuard_{suffix}", (0.18, 1.64, z),
                (0.58, 0.14, 0.04), "StructuralSteel", "Bucket", 0.018,
                bucket_root, parent_local=True)
    add_box("BucketBoltOnCuttingEdge", (1.99, 0.318, 0.0),
            (0.22, 0.12, 3.17), "StructuralSteel", "Bucket", 0.018,
            bucket_root, parent_local=True)
    # Nine replaceable B.O.C. wear segments; no incompatible tooth claim.
    for index in range(RECONSTRUCTED["bucket_cutting_edge_segments"]):
        z = -1.40 + index * 0.35
        add_box(f"BucketBOC_WearSegment_{index + 1:02d}",
                (2.05, 0.310, z), (0.18, 0.055, 0.30),
                "CylinderRod", "Bucket", 0.012, bucket_root, parent_local=True)
        for bolt_offset in (-0.09, 0.09):
            add_cylinder(f"BucketBOC_Bolt_{index + 1:02d}_{bolt_offset:+.2f}",
                         (2.01, 0.286, z + bolt_offset), 0.025, 0.018, "y",
                         "DarkSteel", "Bucket", 12, bucket_root, bevel=False,
                         parent_local=True)
    for rib_index, z in enumerate((-1.18, -0.78, -0.39, 0.0, 0.39, 0.78, 1.18)):
        add_box(f"BucketBackRib_{rib_index + 1:02d}", (0.31, 1.28, z),
                (0.70, 0.10, 0.08), "WarmGraphite", "Bucket", 0.016,
                bucket_root, parent_local=True)

    bucket_ear_local = RECONSTRUCTED["bucket_link_ear_local_xy_m"]
    bucket_ear = add_uv_sphere(
        "Bucket_ZBar_LinkEar_Reconstructed",
        (RECONSTRUCTED["stowed_bucket_hinge_xyz_m"][0] + bucket_ear_local[0],
         RECONSTRUCTED["stowed_bucket_hinge_xyz_m"][1] + bucket_ear_local[1],
         0.0),
        0.095, "StructuralSteel", "Bucket", bucket_root, 24, 12)
    bucket_ear["authority"] = "reconstructed linkage anchor"

    apply_loader_pose("stowed")


def apply_loader_pose(pose: str) -> dict:
    geometry = loader_pose_geometry(pose)
    elbow = geometry["elbow"]
    hinge = geometry["hinge"]
    rear = geometry["pivot"]
    ART["loader_root"].rotation_euler[1] = -geometry["alpha_rad"]
    ART["bucket_root"].rotation_euler = (
        0.0,
        math.radians(geometry["bucket_rotation_blender_y_deg"] + geometry["alpha_deg"]),
        0.0,
    )
    bpy.context.view_layer.update()

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

        cylinder_base = (0.20, 1.20, side * 0.70)
        carry_attach = (1.65, 1.06)
        moving_xy = rotate_xy(carry_attach, (rear[0], rear[1]), geometry["alpha_rad"])
        cylinder_end = (moving_xy[0], moving_xy[1], side * 0.70)
        place_telescoping_pair(
            ART[f"lift_barrel_{suffix}"], ART[f"lift_rod_{suffix}"],
            cylinder_base, cylinder_end,
            RECONSTRUCTED["loader_lift_barrel_length_m"],
            RECONSTRUCTED["loader_lift_rod_insertion_m"],
            PUBLISHED["lift-cylinder-bore"] * 0.5, 0.045,
        )

        for bundle, offset in ((1, -0.026), (2, 0.026)):
            update_polyline(ART[f"hose_{suffix}_{bundle}"], [
                (0.18, 1.24, z + offset),
                (0.72, 1.62, z + offset),
                (elbow[0] + 0.10, elbow[1] + 0.12, z + offset),
                (hinge[0] - 0.18, hinge[1] + 0.20, z + offset),
            ])

    place_beam(ART["arm_crossmember"],
               (elbow[0], elbow[1], -0.89), (elbow[0], elbow[1], 0.89),
               0.22, 0.22)
    place_beam(ART["bucket_crossmember"],
               (hinge[0], hinge[1], -0.91), (hinge[0], hinge[1], 0.91),
               0.18, 0.18)

    pivot = geometry["bellcrank_pivot"]
    upper = geometry["bellcrank_upper"]
    lower = geometry["bellcrank_lower"]
    link_end = geometry["bucket_ear"]
    place_beam(ART["bellcrank_a"], pivot, upper, 0.20, 0.20)
    place_beam(ART["bellcrank_b"], pivot, lower, 0.20, 0.20)
    place_beam(ART["bucket_link"], lower, link_end, 0.16, 0.16)
    ART["tilt_base_clevis"].matrix_world.translation = mv(
        *geometry["bucket_cylinder_base"])
    ART["tilt_moving_clevis"].matrix_world.translation = mv(*upper)
    place_telescoping_pair(
        ART["tilt_barrel"], ART["tilt_rod"],
        geometry["bucket_cylinder_base"], upper,
        RECONSTRUCTED["bucket_cylinder_barrel_length_m"],
        RECONSTRUCTED["bucket_cylinder_rod_insertion_m"],
        PUBLISHED["bucket-cylinder-bore"] * 0.5, 0.052,
    )
    bpy.context.view_layer.update()
    lift_metrics = {
        suffix: measure_telescoping_pair(
            ART[f"lift_barrel_{suffix}"], ART[f"lift_rod_{suffix}"],
            ART[f"lift_base_clevis_{suffix}"], ART[f"lift_arm_clevis_{suffix}"],
        )
        for suffix in ("L", "R")
    }
    bucket_metrics = measure_telescoping_pair(
        ART["tilt_barrel"], ART["tilt_rod"],
        ART["tilt_base_clevis"], ART["tilt_moving_clevis"],
    )
    loader_pivot_world = Vector(ART["loader_root"].matrix_world.translation)
    bucket_hinge_world = Vector(ART["bucket_root"].matrix_world.translation)
    arm_joint_residual = max(
        min((rear_endpoint - front_endpoint).length
            for rear_endpoint in beam_axis_endpoints(ART[f"arm_rear_{suffix}"])
            for front_endpoint in beam_axis_endpoints(ART[f"arm_front_{suffix}"]))
        for suffix in ("L", "R")
    )
    bellcrank_lower_endpoints = beam_axis_endpoints(ART["bellcrank_b"])
    bucket_link_endpoints = beam_axis_endpoints(ART["bucket_link"])
    bucket_ear_world = Vector(
        bpy.data.objects["Bucket_ZBar_LinkEar_Reconstructed"].matrix_world.translation)
    zbar_lower_residual = min(
        (bellcrank_endpoint - link_endpoint).length
        for bellcrank_endpoint in bellcrank_lower_endpoints
        for link_endpoint in bucket_link_endpoints)
    zbar_ear_residual = min(
        (link_endpoint - bucket_ear_world).length
        for link_endpoint in bucket_link_endpoints)
    measured_bucket_link_length = (
        bucket_link_endpoints[1] - bucket_link_endpoints[0]).length
    return {
        **geometry,
        "lift_cylinders": lift_metrics,
        "bucket_cylinder": bucket_metrics,
        "loader_radius_m": (bucket_hinge_world - loader_pivot_world).length,
        "arm_joint_residual_m": arm_joint_residual,
        "measured_bucket_link_length_m": measured_bucket_link_length,
        "zbar_lower_closure_residual_m": zbar_lower_residual,
        "zbar_ear_closure_residual_m": zbar_ear_residual,
        "zbar_joint_residual_m": max(zbar_lower_residual, zbar_ear_residual),
    }


def setup_steering_hydraulics() -> None:
    for side, suffix in ((-1, "L"), (1, "R")):
        base = (0.0, 0.92 + side * 0.07, 0.0)
        front = (0.79, 0.92 + side * 0.07, side * 0.63)
        cylinder_root = add_empty(
            f"SteeringCylinder_{suffix}_YawPivot_ROOT_Reconstructed",
            base, "Hydraulics", 0.12, ART["front_root"],
        )
        cylinder_root["joint_axis_machine"] = "+Y"
        cylinder_root["authority"] = "reconstructed coaxial articulation-axis anchor"
        ART[f"steer_root_{suffix}"] = cylinder_root
        ART[f"steer_barrel_{suffix}"] = add_unit_cylinder(
            f"SteeringCylinder_Barrel_{suffix}", "WarmGraphite", "Hydraulics", 36,
            cylinder_root)
        ART[f"steer_rod_{suffix}"] = add_unit_cylinder(
            f"SteeringCylinder_Rod_{suffix}", "CylinderRod", "Hydraulics", 32,
            cylinder_root)
        add_uv_sphere(f"SteeringCylinder_BaseClevis_{suffix}", base, 0.075,
                      "StructuralSteel", "Hydraulics", ART["rear_root"], 24, 12)
        add_uv_sphere(f"SteeringCylinder_FrontClevis_{suffix}", front, 0.070,
                      "StructuralSteel", "Hydraulics", ART["front_root"], 24, 12)
        ART[f"steer_metric_{suffix}"] = place_telescoping_pair(
            ART[f"steer_barrel_{suffix}"], ART[f"steer_rod_{suffix}"],
            base, front,
            RECONSTRUCTED["steering_cylinder_barrel_length_m"],
            RECONSTRUCTED["steering_cylinder_rod_insertion_m"],
            PUBLISHED["steering-cylinder-bore"] * 0.5, 0.030,
        )
    apply_articulation(0.0)


def apply_articulation(degrees: float) -> dict:
    ART["front_root"].rotation_euler[2] = math.radians(degrees)
    bpy.context.view_layer.update()
    pivot = Vector(ART["front_root"].matrix_world.translation)
    cylinders = {}
    for side, suffix in ((-1, "L"), (1, "R")):
        root_position = ART[f"steer_root_{suffix}"].matrix_world.translation
        measurement = measure_telescoping_pair(
            ART[f"steer_barrel_{suffix}"], ART[f"steer_rod_{suffix}"],
            bpy.data.objects[f"SteeringCylinder_BaseClevis_{suffix}"],
            bpy.data.objects[f"SteeringCylinder_FrontClevis_{suffix}"],
        )
        measurement["front_closure_residual_m"] = measurement.pop(
            "moving_closure_residual_m")
        measurement["front_anchor"] = measurement.pop("moving_anchor")
        cylinders[suffix] = {
            **measurement,
            "base_axis_residual_m": (root_position - mv(0.0, 0.92 + side * 0.07, 0.0)).length,
        }
    return {
        "degrees": degrees,
        "pivot_world_machine": [round(pivot.x, 6), round(pivot.z, 6), round(pivot.y, 6)],
        "cylinders": cylinders,
    }


def apply_rear_axle_oscillation(degrees: float) -> dict:
    ART["rear_axle"].rotation_euler[0] = math.radians(degrees)
    bpy.context.view_layer.update()
    pivot = ART["rear_axle"].matrix_world.translation
    return {
        "degrees": degrees,
        "pivot_world_machine": [round(pivot.x, 6), round(pivot.z, 6), round(pivot.y, 6)],
    }


def build_lights_and_details() -> None:
    rear_root, front_root = ART["rear_root"], ART["front_root"]
    for side, suffix in ((-1, "L"), (1, "R")):
        add_box(f"RearTailLampHousing_{suffix}", (-3.52, 1.23, side * 1.05),
                (0.12, 0.30, 0.20), "DarkSteel", "Details", 0.018, rear_root)
        add_box(f"RearTailLampLens_{suffix}", (-3.586, 1.23, side * 1.05),
                (0.018, 0.23, 0.15), "LensRed", "Details", 0.004, rear_root)
        add_box(f"FrontFrameLampHousing_{suffix}", (2.34, 1.37, side * 0.58),
                (0.22, 0.18, 0.18), "DarkSteel", "Details", 0.022, front_root)
        add_box(f"FrontFrameLampLens_{suffix}", (2.455, 1.37, side * 0.58),
                (0.018, 0.13, 0.13), "LensWhite", "Details", 0.004, front_root)
        add_cylinder(f"FrontTowPin_{suffix}", (2.16, 0.57, side * 0.55),
                     0.075, 0.16, "z", "StructuralSteel", "Details", 24, front_root)
        add_cylinder(f"RearTowPin_{suffix}", (-3.33, 0.52, side * 0.62),
                     0.075, 0.16, "z", "StructuralSteel", "Details", 24, rear_root)

    # Fuel/DEF-like access cap cues are unlabelled and not option-identifying.
    add_cylinder("ServiceFillCap_Right", (-1.48, 1.68, 1.28), 0.085, 0.055, "z",
                 "StructuralSteel", "Details", 24, rear_root)
    add_cylinder("ServiceFillCap_Left", (-2.02, 1.82, -1.28), 0.085, 0.055, "z",
                 "StructuralSteel", "Details", 24, rear_root)
    for side, suffix in ((-1, "L"), (1, "R")):
        for index in range(5):
            add_cylinder(f"LoaderPivotFastener_{suffix}_{index + 1:02d}",
                         (0.28 + index * 0.50, 1.74 - index * 0.14,
                          side * 0.91), 0.055, 0.055, "z",
                         "CylinderRod", "Details", 20, ART["front_root"])


def build_helpers() -> None:
    root = ART["root"]
    marker_specs = {
        "Pivot_FrameArticulation_Reconstructed": (0.0, 1.20, 0.0),
        "Pivot_RearAxleOscillation_Reconstructed": (-1.85, 0.86, 0.0),
        "Pivot_LoaderRear_Reconstructed": (0.28, 1.74, 0.0),
        "Pivot_BucketCarry_Reconstructed": (3.23, 0.58, 0.0),
        "Anchor_LiftCylinderBase_Reconstructed": (0.20, 1.20, 0.0),
        "Anchor_BucketCylinderBase_Reconstructed": (0.40, 1.80, 0.0),
    }
    for name, xyz in marker_specs.items():
        marker = add_empty(name, xyz, "Markers", 0.13, root)
        marker["authority"] = "reconstructed"

    for name, center, size in (
        ("RearFrame_Hit", (-1.90, 1.42, 0.0), (3.60, 2.35, 2.90)),
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


def evaluated_bounds_for_objects(objects: list[bpy.types.Object]) -> dict:
    dependencies = bpy.context.evaluated_depsgraph_get()
    coordinates: list[tuple[float, float, float]] = []
    names: list[str] = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE"}:
            continue
        evaluated = obj.evaluated_get(dependencies)
        mesh = evaluated.to_mesh()
        for vertex in mesh.vertices:
            world = evaluated.matrix_world @ vertex.co
            coordinates.append((world.x, world.z, world.y))
        evaluated.to_mesh_clear()
        names.append(obj.name)
    if not coordinates:
        raise RuntimeError("Requested measured object set has no geometry")
    minimum = [min(point[axis] for point in coordinates) for axis in range(3)]
    maximum = [max(point[axis] for point in coordinates) for axis in range(3)]
    return {
        "min_m": [round(value, 6) for value in minimum],
        "max_m": [round(value, 6) for value in maximum],
        "size_m": [round(maximum[index] - minimum[index], 6) for index in range(3)],
        "objects": sorted(names),
        "method": "evaluated world-space mesh vertices in machine X/Y/Z axes",
    }


def object_bounds(name: str) -> dict:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Missing measured object {name}")
    return evaluated_bounds_for_objects([obj])


def subtree_bounds(ancestor_name: str) -> dict:
    ancestor = bpy.data.objects.get(ancestor_name)
    if ancestor is None:
        raise RuntimeError(f"Missing measured ancestor {ancestor_name}")
    objects = [obj for obj in bpy.context.scene.objects
               if obj != ancestor and is_descendant_of(obj, ancestor)
               and obj.type in {"MESH", "CURVE"}]
    return evaluated_bounds_for_objects(objects)


def world_machine_location(name: str) -> list[float]:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"Missing measured transform node {name}")
    bpy.context.view_layer.update()
    point = obj.matrix_world.translation
    return [round(point.x, 6), round(point.z, 6), round(point.y, 6)]


def parent_name(name: str) -> str | None:
    obj = bpy.data.objects.get(name)
    if obj is None:
        return None
    return obj.parent.name if obj.parent else None


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
    parent_indices = {}
    for parent_index, node in enumerate(nodes):
        for child_index in node.get("children", []):
            parent_indices[child_index] = parent_index
    root_names = [nodes[index].get("name") for index in roots]
    root_node = nodes[roots[0]] if len(roots) == 1 else {}
    identity = (
        root_node.get("translation", [0, 0, 0]) == [0, 0, 0]
        and root_node.get("rotation", [0, 0, 0, 1]) == [0, 0, 0, 1]
        and root_node.get("scale", [1, 1, 1]) == [1, 1, 1]
        and "matrix" not in root_node
    )
    helper_tokens = ("_Hit", "_Inspect", "StudioFloor",
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
    semantic_names = set(public_semantic_nodes())
    semantic_hierarchy = {}
    for node_index, node in enumerate(nodes):
        name = node.get("name")
        if name not in semantic_names:
            continue
        parent_index = parent_indices.get(node_index)
        semantic_hierarchy[name] = {
            "parent": nodes[parent_index].get("name") if parent_index is not None else None,
            "translation": node.get("translation", [0, 0, 0]),
            "rotation": node.get("rotation", [0, 0, 0, 1]),
            "scale": node.get("scale", [1, 1, 1]),
            "mesh": "mesh" in node,
        }
    passed = (len(roots) == 1 and root_names == ["Machine_Root"] and identity
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
        "semantic_hierarchy": semantic_hierarchy,
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


def gate_detail(method: str, evidence, semantic_nodes: list[str],
                fact_ids: list[str]) -> dict:
    if not isinstance(method, str) or not method.strip():
        raise RuntimeError("Gate measurement method must be nonempty")
    if len(semantic_nodes) != len(set(semantic_nodes)):
        raise RuntimeError(f"Duplicate gate semantic nodes: {semantic_nodes}")
    if len(fact_ids) != len(set(fact_ids)):
        raise RuntimeError(f"Duplicate gate fact ids: {fact_ids}")
    unknown = sorted(set(fact_ids) - set(FACT_RECORDS))
    if unknown:
        raise RuntimeError(f"Gate references unknown facts: {unknown}")
    return {
        "method": method,
        "evidence": evidence,
        "semantic_nodes": semantic_nodes,
        "fact_ids": fact_ids,
    }


def make_gate(gate_id: str, status: str, detail, expected=None, actual=None) -> dict:
    gate = {"id": gate_id, "status": status, "detail": detail}
    if expected is not None:
        gate["expected"] = expected
    if actual is not None:
        gate["actual"] = actual
    return gate


def public_semantic_nodes() -> list[str]:
    return [
        "Machine_Root", "RearFrame_Root", "Articulation_FrontFrame_Root_Reconstructed",
        "RearAxle_Oscillation_Root_Reconstructed", "RearWheel_L_Pivot_ROOT",
        "RearWheel_R_Pivot_ROOT", "FrontWheel_L_Pivot_ROOT", "FrontWheel_R_Pivot_ROOT",
        "RearFrame_Spine", "RearCounterweight_Mass", "RearBellyGuard",
        "EngineCompartment_Core", "RearCoolingMask", "Cab_ROPS_Root_Reconstructed",
        "ROPS_Roof", "CabRoofRail_L", "ExhaustRainCap", "Cab_FrontGlass",
        "RearTire_L", "RearTire_R", "FrontTire_L",
        "FrontTire_R", "FrontFrame_Main", "CenterArticulationUpperPin",
        "CenterArticulationLowerPin",
        "SteeringCylinder_L_YawPivot_ROOT_Reconstructed",
        "SteeringCylinder_R_YawPivot_ROOT_Reconstructed",
        "SteeringCylinder_Barrel_L", "SteeringCylinder_Rod_L",
        "SteeringCylinder_Barrel_R", "SteeringCylinder_Rod_R",
        "SteeringCylinder_BaseClevis_L", "SteeringCylinder_BaseClevis_R",
        "SteeringCylinder_FrontClevis_L", "SteeringCylinder_FrontClevis_R",
        "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "StandardLoaderArmRear_L", "StandardLoaderArmFront_L",
        "StandardLoaderArmRear_R", "StandardLoaderArmFront_R",
        "LiftCylinder_Barrel_L", "LiftCylinder_Rod_L",
        "LiftCylinder_Barrel_R", "LiftCylinder_Rod_R",
        "LiftCylinder_BaseClevis_L", "LiftCylinder_ArmClevis_L",
        "LiftCylinder_BaseClevis_R", "LiftCylinder_ArmClevis_R",
        "BucketCylinder_Barrel", "BucketCylinder_Rod",
        "BucketCylinder_BaseClevis", "BucketCylinder_BellcrankClevis",
        "ZBar_Bellcrank_Pivot_ROOT_Reconstructed",
        "ZBar_Bellcrank_Upper_Reconstructed", "ZBar_Bellcrank_Lower_Reconstructed",
        "ZBar_BucketLink_Reconstructed",
        "StockPileBucket_PivotRoot_Reconstructed", "StockPileBucket_Shell",
        "Bucket_ZBar_LinkEar_Reconstructed", "BucketHingeCrossmember",
        "BucketSideGuard_L", "BucketSideGuard_R", "BucketBoltOnCuttingEdge",
        "LoaderHose_L_01", "LoaderHose_R_01",
    ]


def validate(root: bpy.types.Object, counts: dict, scale_audit: dict,
             glb_contract: dict) -> dict:
    mechanism = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    required_gate_ids = mechanism["required_gates"]
    gates: list[dict] = []

    apply_articulation(0.0)
    apply_rear_axle_oscillation(0.0)
    stowed = apply_loader_pose("stowed")
    stowed_bounds = evaluated_visible_bounds(root)
    stowed_bucket_bounds = subtree_bounds("StockPileBucket_PivotRoot_Reconstructed")
    stowed_edge_bounds = object_bounds("BucketBoltOnCuttingEdge")
    bucket_width_bounds = evaluated_bounds_for_objects([
        bpy.data.objects["BucketSideGuard_L"], bpy.data.objects["BucketSideGuard_R"]])
    tire_width_bounds = evaluated_bounds_for_objects([
        bpy.data.objects["FrontSidewallOuter_L"], bpy.data.objects["FrontSidewallOuter_R"]])
    roof_bounds = object_bounds("CabRoofRail_L")
    rops_bounds = object_bounds("ROPS_Roof")
    stack_bounds = object_bounds("ExhaustRainCap")
    belly_bounds = evaluated_bounds_for_objects([
        bpy.data.objects["RearBellyGuard"], bpy.data.objects["FrontFrame_BellyPan"]])
    hitch_height = world_machine_location("Articulation_FrontFrame_Root_Reconstructed")[1]

    retained_measurements = {
        "overall_length_m": stowed_bounds["size_m"][0],
        "bucket_width_m": bucket_width_bounds["size_m"][2],
        "standard_tire_width_m": tire_width_bounds["size_m"][2],
        "roof_rail_top_m": roof_bounds["max_m"][1],
        "rops_top_m": rops_bounds["max_m"][1],
        "stack_top_m": stack_bounds["max_m"][1],
        "ground_clearance_witness_bottom_m": belly_bounds["min_m"][1],
        "hitch_pivot_height_m": hitch_height,
        "lowest_public_geometry_m": stowed_bounds["min_m"][1],
        "selected_bucket_source_values": {
            fact_id: PUBLISHED[fact_id] for fact_id in (
                "bucket-capacity-heaped", "bucket-capacity-struck", "bucket-weight")
        },
    }
    retained_ok = all((
        abs(retained_measurements["overall_length_m"] - PUBLISHED["overall-length-stock-pile"]) <= 0.08,
        abs(retained_measurements["bucket_width_m"] - PUBLISHED["bucket-width-stock-pile"]) <= 0.01,
        abs(retained_measurements["standard_tire_width_m"] - PUBLISHED["width-standard-tires"]) <= 0.03,
        abs(retained_measurements["roof_rail_top_m"] - PUBLISHED["height-roof-rail"]) <= 0.005,
        abs(retained_measurements["rops_top_m"] - PUBLISHED["height-rops-cab"]) <= 0.005,
        abs(retained_measurements["stack_top_m"] - PUBLISHED["height-top-stack"]) <= 0.005,
        abs(retained_measurements["ground_clearance_witness_bottom_m"] - PUBLISHED["ground-clearance"]) <= 0.005,
        abs(retained_measurements["hitch_pivot_height_m"] - PUBLISHED["hitch-height-standard"]) <= 0.005,
        retained_measurements["lowest_public_geometry_m"] >= -0.001,
    ))
    gates.append(make_gate(
        "retained_stowed_envelope", "PASS" if retained_ok else "FAIL",
        gate_detail(
            "Evaluated retained-pose public vertices plus named physical roof, ROPS, stack, belly-pan, tire, bucket and hitch witnesses.",
            retained_measurements,
            ["Machine_Root", "StockPileBucket_Shell", "BucketSideGuard_L",
             "BucketSideGuard_R", "FrontSidewallOuter_L", "FrontSidewallOuter_R",
             "CabRoofRail_L", "ROPS_Roof", "ExhaustRainCap", "RearBellyGuard",
             "FrontFrame_BellyPan", "Articulation_FrontFrame_Root_Reconstructed"],
            ["overall-length-stock-pile", "bucket-width-stock-pile",
             "width-standard-tires", "ground-clearance", "hitch-height-standard",
             "height-top-stack", "height-rops-cab", "height-roof-rail",
             "bucket-capacity-heaped", "bucket-capacity-struck", "bucket-weight"],
        ),
        {"length_tolerance_m": 0.08, "dimension_tolerance_m": 0.005,
         "ground_penetration_max_m": 0.001}, retained_measurements,
    ))

    wheel_roots = ["RearWheel_L_Pivot_ROOT", "RearWheel_R_Pivot_ROOT",
                   "FrontWheel_L_Pivot_ROOT", "FrontWheel_R_Pivot_ROOT"]
    wheel_locations = {name: world_machine_location(name) for name in wheel_roots}
    wheelbase_values = [
        wheel_locations[f"FrontWheel_{side}_Pivot_ROOT"][0]
        - wheel_locations[f"RearWheel_{side}_Pivot_ROOT"][0]
        for side in ("L", "R")
    ]
    tire_contacts = {name: object_bounds(name)["min_m"][1]
                     for name in ("RearTire_L", "RearTire_R", "FrontTire_L", "FrontTire_R")}
    wheel_parent_expectations = {
        "RearWheel_L_Pivot_ROOT": "RearAxle_Oscillation_Root_Reconstructed",
        "RearWheel_R_Pivot_ROOT": "RearAxle_Oscillation_Root_Reconstructed",
        "FrontWheel_L_Pivot_ROOT": "Articulation_FrontFrame_Root_Reconstructed",
        "FrontWheel_R_Pivot_ROOT": "Articulation_FrontFrame_Root_Reconstructed",
    }
    wheel_parent_actual = {name: parent_name(name) for name in wheel_roots}
    wheelbase_ok = (
        all(abs(value - PUBLISHED["wheelbase"]) <= 0.001 for value in wheelbase_values)
        and all(-0.001 <= value <= 0.02 for value in tire_contacts.values())
        and wheel_parent_actual == wheel_parent_expectations
    )
    wheel_evidence = {"wheelbase_m": wheelbase_values, "tire_contact_y_m": tire_contacts,
                      "parents": wheel_parent_actual, "pivot_locations_m": wheel_locations}
    gates.append(make_gate(
        "wheelbase_and_grade_contact", "PASS" if wheelbase_ok else "FAIL",
        gate_detail("World-space wheel-pivot separation, decoded hierarchy ownership, and evaluated tire tread contact elevations.",
                    wheel_evidence, wheel_roots + ["RearTire_L", "RearTire_R", "FrontTire_L", "FrontTire_R"],
                    ["wheelbase"]),
        {"wheelbase_m": PUBLISHED["wheelbase"], "contact_y_range_m": [-0.001, 0.02]}, wheel_evidence,
    ))

    articulation_samples = []
    articulation_pivot = [0.0, PUBLISHED["hitch-height-standard"], 0.0]
    for angle in (-PUBLISHED["steering-angle-max-stop"],
                  -PUBLISHED["steering-angle-nominal"], 0.0,
                  PUBLISHED["steering-angle-nominal"],
                  PUBLISHED["steering-angle-max-stop"]):
        sample = apply_articulation(angle)
        actual_pivot = world_machine_location("Articulation_FrontFrame_Root_Reconstructed")
        residual = math.dist(actual_pivot, articulation_pivot)
        articulation_samples.append({"angle_deg": angle, "pivot_m": actual_pivot,
                                     "pivot_residual_m": residual})
    apply_articulation(0.0)
    articulation_topology = {
        "front_root_parent": parent_name("Articulation_FrontFrame_Root_Reconstructed"),
        "upper_pin_parent": parent_name("CenterArticulationUpperPin"),
        "lower_pin_parent": parent_name("CenterArticulationLowerPin"),
    }
    articulation_ok = (
        max(item["pivot_residual_m"] for item in articulation_samples) <= 1e-6
        and articulation_topology == {
            "front_root_parent": "Machine_Root",
            "upper_pin_parent": "Machine_Root",
            "lower_pin_parent": "Machine_Root",
        }
    )
    articulation_evidence = {"samples": articulation_samples, "topology": articulation_topology}
    gates.append(make_gate(
        "frame_articulation_continuity", "PASS" if articulation_ok else "FAIL",
        gate_detail("Five-point -40/-35/0/+35/+40 degree transform sweep with invariant hitch-axis residual and fixed-pin ancestry.",
                    articulation_evidence,
                    ["Machine_Root", "Articulation_FrontFrame_Root_Reconstructed",
                     "CenterArticulationUpperPin", "CenterArticulationLowerPin"],
                    ["steering-angle-nominal", "steering-angle-max-stop", "hitch-height-standard"]),
        {"maximum_pivot_residual_m": 0.000001}, articulation_evidence,
    ))

    steering_samples = []
    for angle in (-40.0, -35.0, 0.0, 35.0, 40.0):
        sample = apply_articulation(angle)
        steering_samples.append(sample)
    apply_articulation(0.0)
    steering_lengths = {
        suffix: [sample["cylinders"][suffix]["anchor_distance_m"] for sample in steering_samples]
        for suffix in ("L", "R")
    }
    steering_travel = {suffix: max(values) - min(values)
                       for suffix, values in steering_lengths.items()}
    steering_parent_actual = {
        name: parent_name(name) for name in (
            "SteeringCylinder_Barrel_L", "SteeringCylinder_Rod_L",
            "SteeringCylinder_Barrel_R", "SteeringCylinder_Rod_R",
            "SteeringCylinder_L_YawPivot_ROOT_Reconstructed",
            "SteeringCylinder_R_YawPivot_ROOT_Reconstructed",
            "SteeringCylinder_BaseClevis_L", "SteeringCylinder_BaseClevis_R",
            "SteeringCylinder_FrontClevis_L", "SteeringCylinder_FrontClevis_R")
    }
    expected_steering_parents = {
        "SteeringCylinder_Barrel_L": "SteeringCylinder_L_YawPivot_ROOT_Reconstructed",
        "SteeringCylinder_Rod_L": "SteeringCylinder_L_YawPivot_ROOT_Reconstructed",
        "SteeringCylinder_Barrel_R": "SteeringCylinder_R_YawPivot_ROOT_Reconstructed",
        "SteeringCylinder_Rod_R": "SteeringCylinder_R_YawPivot_ROOT_Reconstructed",
        "SteeringCylinder_L_YawPivot_ROOT_Reconstructed": "Articulation_FrontFrame_Root_Reconstructed",
        "SteeringCylinder_R_YawPivot_ROOT_Reconstructed": "Articulation_FrontFrame_Root_Reconstructed",
        "SteeringCylinder_BaseClevis_L": "RearFrame_Root",
        "SteeringCylinder_BaseClevis_R": "RearFrame_Root",
        "SteeringCylinder_FrontClevis_L": "Articulation_FrontFrame_Root_Reconstructed",
        "SteeringCylinder_FrontClevis_R": "Articulation_FrontFrame_Root_Reconstructed",
    }
    steering_bores = {
        suffix: cylinder_mesh_bore(ART[f"steer_barrel_{suffix}"])
        for suffix in ("L", "R")
    }
    steering_ok = (
        all(value <= PUBLISHED["steering-cylinder-stroke"] + 1e-9
            for value in steering_travel.values())
        and max(sample["cylinders"][suffix]["base_axis_residual_m"]
                for sample in steering_samples for suffix in ("L", "R")) <= 1e-6
        and max(sample["cylinders"][suffix]["base_closure_residual_m"]
                for sample in steering_samples for suffix in ("L", "R")) <= 1e-6
        and max(sample["cylinders"][suffix]["front_closure_residual_m"]
                for sample in steering_samples for suffix in ("L", "R")) <= 1e-6
        and min(sample["cylinders"][suffix]["barrel_rod_overlap_m"]
                for sample in steering_samples for suffix in ("L", "R")) >= 0.01
        and all(abs(value - PUBLISHED["steering-cylinder-bore"]) <= 1e-6
                for value in steering_bores.values())
        and sum(1 for name in bpy.context.scene.objects
                if name.name.startswith("SteeringCylinder_Barrel_")) == PUBLISHED["steering-cylinder-count"]
        and steering_parent_actual == expected_steering_parents
    )
    steering_evidence = {"samples": steering_samples, "stroke_travel_m": steering_travel,
                         "parents": steering_parent_actual,
                         "measured_barrel_bore_m": steering_bores}
    gates.append(make_gate(
        "steering_cylinder_continuity", "PASS" if steering_ok else "FAIL",
        gate_detail("Five-point articulation sweep of fixed-rear and moving-front clevises; directly measures barrel/rod mesh endpoints, closure residuals, overlap, count, stroke use and ancestry.",
                    steering_evidence,
                    ["SteeringCylinder_L_YawPivot_ROOT_Reconstructed",
                     "SteeringCylinder_R_YawPivot_ROOT_Reconstructed",
                     "SteeringCylinder_Barrel_L", "SteeringCylinder_Rod_L",
                     "SteeringCylinder_Barrel_R", "SteeringCylinder_Rod_R",
                     "SteeringCylinder_BaseClevis_L", "SteeringCylinder_BaseClevis_R",
                     "SteeringCylinder_FrontClevis_L", "SteeringCylinder_FrontClevis_R"],
                    ["steering-cylinder-count", "steering-cylinder-bore",
                     "steering-cylinder-stroke", "steering-angle-max-stop"]),
        {"maximum_travel_m": PUBLISHED["steering-cylinder-stroke"], "maximum_anchor_residual_m": 0.000001},
        steering_evidence,
    ))

    rear_axle_samples = []
    rear_body_bounds = object_bounds("RearFrame_Spine")
    for angle in (-13.0, 0.0, 13.0):
        sample = apply_rear_axle_oscillation(angle)
        left = object_bounds("RearTire_L")
        right = object_bounds("RearTire_R")
        sample["lateral_body_clearance_m"] = {
            "left": rear_body_bounds["min_m"][2] - left["max_m"][2],
            "right": right["min_m"][2] - rear_body_bounds["max_m"][2],
        }
        sample["pivot_residual_m"] = math.dist(
            sample["pivot_world_machine"], RECONSTRUCTED["rear_axle_pivot_xyz_m"])
        rear_axle_samples.append(sample)
    apply_rear_axle_oscillation(0.0)
    rear_clearance_min = min(value for sample in rear_axle_samples
                             for value in sample["lateral_body_clearance_m"].values())
    rear_axle_ok = (
        max(sample["pivot_residual_m"] for sample in rear_axle_samples) <= 1e-6
        and rear_clearance_min >= 0.05
        and parent_name("RearAxle_Oscillation_Root_Reconstructed") == "RearFrame_Root"
        and parent_name("RearWheel_L_Pivot_ROOT") == "RearAxle_Oscillation_Root_Reconstructed"
        and parent_name("RearWheel_R_Pivot_ROOT") == "RearAxle_Oscillation_Root_Reconstructed"
    )
    rear_axle_evidence = {"samples": rear_axle_samples,
                          "minimum_lateral_body_clearance_m": rear_clearance_min}
    gates.append(make_gate(
        "rear_axle_oscillation_clearance", "PASS" if rear_axle_ok else "FAIL",
        gate_detail("Endpoint sweep at the published +/-13 degree half-range; measures pivot invariance, wheel ancestry and rear-frame lateral clearance.",
                    rear_axle_evidence,
                    ["RearFrame_Root", "RearAxle_Oscillation_Root_Reconstructed",
                     "RearWheel_L_Pivot_ROOT", "RearWheel_R_Pivot_ROOT",
                     "RearTire_L", "RearTire_R", "RearFrame_Spine"],
                    ["rear-axle-oscillation"]),
        {"total_range_deg": PUBLISHED["rear-axle-oscillation"], "minimum_clearance_m": 0.05},
        rear_axle_evidence,
    ))

    stowed = apply_loader_pose("stowed")
    stowed_hinge_world = world_machine_location("StockPileBucket_PivotRoot_Reconstructed")
    raised = apply_loader_pose("raised_dump")
    raised_hinge_world = world_machine_location("StockPileBucket_PivotRoot_Reconstructed")
    raised_bucket_bounds = subtree_bounds("StockPileBucket_PivotRoot_Reconstructed")
    raised_edge_bounds = object_bounds("BucketBoltOnCuttingEdge")
    front_tire_bounds = evaluated_bounds_for_objects([
        bpy.data.objects["FrontTire_L"], bpy.data.objects["FrontTire_R"]])
    hinge_evidence = {
        "carry_height_m": stowed_hinge_world[1],
        "maximum_height_m": raised_hinge_world[1],
        "carry_pose": stowed,
        "raised_pose": raised,
    }
    hinge_ok = (
        abs(stowed_hinge_world[1] - PUBLISHED["hinge-pin-height-carry-standard"]) <= 0.002
        and abs(raised_hinge_world[1] - PUBLISHED["hinge-pin-height-max-standard"]) <= 0.002
        and abs(stowed["loader_radius_m"] - raised["loader_radius_m"]) <= 1e-6
    )
    gates.append(make_gate(
        "full_lift_hinge_height", "PASS" if hinge_ok else "FAIL",
        gate_detail("World transform of the shipped bucket pivot at stowed and maximum-lift endpoints, plus invariant rigid-arm radius.",
                    hinge_evidence,
                    ["LoaderArm_LiftPivot_ROOT_Reconstructed",
                     "StockPileBucket_PivotRoot_Reconstructed", "BucketHingeCrossmember"],
                    ["hinge-pin-height-carry-standard", "hinge-pin-height-max-standard"]),
        {"carry_m": PUBLISHED["hinge-pin-height-carry-standard"],
         "maximum_m": PUBLISHED["hinge-pin-height-max-standard"], "tolerance_m": 0.002},
        hinge_evidence,
    ))

    dump_measurements = {
        "cutting_edge_clearance_m": raised_edge_bounds["min_m"][1],
        "cutting_edge_reach_from_front_tire_m": (
            raised_edge_bounds["max_m"][0] - front_tire_bounds["max_m"][0]),
        "bucket_operating_height_m": raised_bucket_bounds["max_m"][1],
        "bucket_bounds_m": raised_bucket_bounds,
        "cutting_edge_bounds_m": raised_edge_bounds,
        "front_tire_forward_x_m": front_tire_bounds["max_m"][0],
        "dump_rotation_deg": raised["bucket_rotation_blender_y_deg"],
    }
    dump_ok = (
        abs(dump_measurements["cutting_edge_clearance_m"] - PUBLISHED["dump-clearance-stock-pile"]) <= 0.06
        and abs(dump_measurements["cutting_edge_reach_from_front_tire_m"] - PUBLISHED["dump-reach-stock-pile"]) <= 0.08
        and abs(dump_measurements["bucket_operating_height_m"] - PUBLISHED["operating-height-stock-pile"]) <= 0.06
    )
    gates.append(make_gate(
        "dump_clearance_and_reach", "PASS" if dump_ok else "FAIL",
        gate_detail("Evaluated raised-pose cutting-edge and complete bucket vertices at the brochure's 45 degree dump condition; reach uses the front-tire forward tangent datum.",
                    dump_measurements,
                    ["StockPileBucket_PivotRoot_Reconstructed", "StockPileBucket_Shell",
                     "BucketBoltOnCuttingEdge", "FrontTire_L", "FrontTire_R"],
                    ["dump-clearance-stock-pile", "dump-reach-stock-pile",
                     "operating-height-stock-pile"]),
        {"clearance_m": PUBLISHED["dump-clearance-stock-pile"],
         "reach_m": PUBLISHED["dump-reach-stock-pile"],
         "operating_height_m": PUBLISHED["operating-height-stock-pile"],
         "tolerance_m": {"clearance": 0.06, "reach": 0.08, "height": 0.06}},
        dump_measurements,
    ))

    loader_parent_actual = {
        name: parent_name(name) for name in (
            "LoaderArm_LiftPivot_ROOT_Reconstructed", "StandardLoaderArmRear_L",
            "StandardLoaderArmFront_L", "StandardLoaderArmRear_R",
            "StandardLoaderArmFront_R", "StockPileBucket_PivotRoot_Reconstructed",
            "LiftCylinder_Barrel_L", "LiftCylinder_Rod_L",
            "LiftCylinder_Barrel_R", "LiftCylinder_Rod_R")
    }
    loader_parent_expected = {
        "LoaderArm_LiftPivot_ROOT_Reconstructed": "Articulation_FrontFrame_Root_Reconstructed",
        "StandardLoaderArmRear_L": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "StandardLoaderArmFront_L": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "StandardLoaderArmRear_R": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "StandardLoaderArmFront_R": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "StockPileBucket_PivotRoot_Reconstructed": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "LiftCylinder_Barrel_L": "Articulation_FrontFrame_Root_Reconstructed",
        "LiftCylinder_Rod_L": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "LiftCylinder_Barrel_R": "Articulation_FrontFrame_Root_Reconstructed",
        "LiftCylinder_Rod_R": "LoaderArm_LiftPivot_ROOT_Reconstructed",
    }
    loader_evidence = {
        "parents": loader_parent_actual,
        "stowed_radius_m": stowed["loader_radius_m"],
        "raised_radius_m": raised["loader_radius_m"],
        "arm_joint_residual_m": max(stowed["arm_joint_residual_m"], raised["arm_joint_residual_m"]),
    }
    loader_ok = (
        loader_parent_actual == loader_parent_expected
        and abs(stowed["loader_radius_m"] - raised["loader_radius_m"]) <= 1e-6
        and loader_evidence["arm_joint_residual_m"] <= 1e-6
    )
    gates.append(make_gate(
        "loader_linkage_closure", "PASS" if loader_ok else "FAIL",
        gate_detail("Ancestry audit plus stowed/raised rigid-arm-radius and shared elbow/hinge endpoint residual measurements.",
                    loader_evidence,
                    ["Articulation_FrontFrame_Root_Reconstructed",
                     "LoaderArm_LiftPivot_ROOT_Reconstructed", "StandardLoaderArmRear_L",
                     "StandardLoaderArmFront_L", "StandardLoaderArmRear_R",
                     "StandardLoaderArmFront_R", "StockPileBucket_PivotRoot_Reconstructed",
                     "LiftCylinder_Barrel_L", "LiftCylinder_Rod_L",
                     "LiftCylinder_Barrel_R", "LiftCylinder_Rod_R"],
                    ["hinge-pin-height-carry-standard", "hinge-pin-height-max-standard"]),
        {"maximum_joint_residual_m": 0.000001, "maximum_radius_delta_m": 0.000001}, loader_evidence,
    ))

    zbar_residuals = {
        "stowed_measured_link_length_m": stowed["measured_bucket_link_length_m"],
        "raised_measured_link_length_m": raised["measured_bucket_link_length_m"],
        "link_length_delta_m": abs(stowed["measured_bucket_link_length_m"]
                                   - raised["measured_bucket_link_length_m"]),
        "stowed_closure_residual_m": stowed["zbar_joint_residual_m"],
        "raised_closure_residual_m": raised["zbar_joint_residual_m"],
        "endpoint_residuals_m": {
            "stowed_lower": stowed["zbar_lower_closure_residual_m"],
            "stowed_bucket_ear": stowed["zbar_ear_closure_residual_m"],
            "raised_lower": raised["zbar_lower_closure_residual_m"],
            "raised_bucket_ear": raised["zbar_ear_closure_residual_m"],
        },
        "parents": {
            "zbar_root": parent_name("ZBar_Bellcrank_Pivot_ROOT_Reconstructed"),
            "upper": parent_name("ZBar_Bellcrank_Upper_Reconstructed"),
            "lower": parent_name("ZBar_Bellcrank_Lower_Reconstructed"),
            "bucket_link": parent_name("ZBar_BucketLink_Reconstructed"),
            "bucket_ear": parent_name("Bucket_ZBar_LinkEar_Reconstructed"),
        },
    }
    zbar_ok = (
        max(zbar_residuals["stowed_closure_residual_m"],
            zbar_residuals["raised_closure_residual_m"]) <= 1e-6
        and zbar_residuals["link_length_delta_m"] <= 1e-6
        and zbar_residuals["parents"] == {
            "zbar_root": "LoaderArm_LiftPivot_ROOT_Reconstructed",
            "upper": "ZBar_Bellcrank_Pivot_ROOT_Reconstructed",
            "lower": "ZBar_Bellcrank_Pivot_ROOT_Reconstructed",
            "bucket_link": "LoaderArm_LiftPivot_ROOT_Reconstructed",
            "bucket_ear": "StockPileBucket_PivotRoot_Reconstructed",
        }
    )
    gates.append(make_gate(
        "z_bar_linkage_closure", "PASS" if zbar_ok else "FAIL",
        gate_detail("Two-pose circle-intersection solution with invariant rigid bucket-link length, measured endpoint residuals and exported ancestry.",
                    zbar_residuals,
                    ["ZBar_Bellcrank_Pivot_ROOT_Reconstructed",
                     "ZBar_Bellcrank_Upper_Reconstructed", "ZBar_Bellcrank_Lower_Reconstructed",
                     "ZBar_BucketLink_Reconstructed", "Bucket_ZBar_LinkEar_Reconstructed",
                     "StockPileBucket_PivotRoot_Reconstructed"], []),
        {"maximum_closure_residual_m": 0.000001}, zbar_residuals,
    ))

    lift_travel = {
        suffix: abs(raised["lift_cylinders"][suffix]["anchor_distance_m"]
                    - stowed["lift_cylinders"][suffix]["anchor_distance_m"])
        for suffix in ("L", "R")
    }
    bucket_travel = abs(raised["bucket_cylinder"]["anchor_distance_m"]
                        - stowed["bucket_cylinder"]["anchor_distance_m"])
    lift_barrel_names = sorted(
        obj.name for obj in bpy.context.scene.objects
        if obj.name.startswith("LiftCylinder_Barrel_"))
    bucket_barrel_names = sorted(
        obj.name for obj in bpy.context.scene.objects
        if obj.name == "BucketCylinder_Barrel")
    cylinder_parents = {
        name: parent_name(name) for name in (
            "LiftCylinder_Barrel_L", "LiftCylinder_Rod_L",
            "LiftCylinder_Barrel_R", "LiftCylinder_Rod_R",
            "BucketCylinder_Barrel", "BucketCylinder_Rod",
            "BucketCylinder_BaseClevis", "BucketCylinder_BellcrankClevis")
    }
    expected_cylinder_parents = {
        "LiftCylinder_Barrel_L": "Articulation_FrontFrame_Root_Reconstructed",
        "LiftCylinder_Rod_L": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "LiftCylinder_Barrel_R": "Articulation_FrontFrame_Root_Reconstructed",
        "LiftCylinder_Rod_R": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "BucketCylinder_Barrel": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "BucketCylinder_Rod": "ZBar_Bellcrank_Pivot_ROOT_Reconstructed",
        "BucketCylinder_BaseClevis": "LoaderArm_LiftPivot_ROOT_Reconstructed",
        "BucketCylinder_BellcrankClevis": "ZBar_Bellcrank_Pivot_ROOT_Reconstructed",
    }
    measured_lift_bores = {
        suffix: cylinder_mesh_bore(ART[f"lift_barrel_{suffix}"])
        for suffix in ("L", "R")
    }
    measured_bucket_bore = cylinder_mesh_bore(ART["tilt_barrel"])
    cylinder_evidence = {
        "lift": {"count": len(lift_barrel_names), "barrel_nodes": lift_barrel_names,
                 "measured_bore_m": measured_lift_bores,
                 "travel_m": lift_travel,
                 "stowed": stowed["lift_cylinders"], "raised": raised["lift_cylinders"]},
        "bucket": {"count": len(bucket_barrel_names), "barrel_nodes": bucket_barrel_names,
                   "measured_bore_m": measured_bucket_bore,
                   "travel_m": bucket_travel,
                   "stowed": stowed["bucket_cylinder"], "raised": raised["bucket_cylinder"]},
        "parents": cylinder_parents,
    }
    cylinder_ok = (
        len(lift_barrel_names) == PUBLISHED["lift-cylinder-count"]
        and len(bucket_barrel_names) == PUBLISHED["bucket-cylinder-count"]
        and cylinder_parents == expected_cylinder_parents
        and all(abs(value - PUBLISHED["lift-cylinder-bore"]) <= 1e-6
                for value in measured_lift_bores.values())
        and abs(measured_bucket_bore - PUBLISHED["bucket-cylinder-bore"]) <= 1e-6
        and all(value <= PUBLISHED["lift-cylinder-stroke"] + 1e-9 for value in lift_travel.values())
        and bucket_travel <= PUBLISHED["bucket-cylinder-stroke"] + 1e-9
        and min(item["barrel_rod_overlap_m"] for pose in (stowed, raised)
                for item in pose["lift_cylinders"].values()) > 0.0
        and min(stowed["bucket_cylinder"]["barrel_rod_overlap_m"],
                raised["bucket_cylinder"]["barrel_rod_overlap_m"]) > 0.0
        and max(item["base_closure_residual_m"] for pose in (stowed, raised)
                for item in pose["lift_cylinders"].values()) <= 1e-6
        and max(item["moving_closure_residual_m"] for pose in (stowed, raised)
                for item in pose["lift_cylinders"].values()) <= 1e-6
        and max(stowed["bucket_cylinder"]["base_closure_residual_m"],
                raised["bucket_cylinder"]["base_closure_residual_m"],
                stowed["bucket_cylinder"]["moving_closure_residual_m"],
                raised["bucket_cylinder"]["moving_closure_residual_m"]) <= 1e-6
    )
    gates.append(make_gate(
        "lift_and_bucket_cylinder_stroke_continuity", "PASS" if cylinder_ok else "FAIL",
        gate_detail("Stowed/raised fixed-to-moving clevis and mesh-endpoint measurements, closure residuals, barrel/rod overlap, decoded ancestry, measured bore and counted barrel nodes.",
                    cylinder_evidence,
                    ["LiftCylinder_Barrel_L", "LiftCylinder_Rod_L",
                     "LiftCylinder_Barrel_R", "LiftCylinder_Rod_R",
                     "LiftCylinder_BaseClevis_L", "LiftCylinder_ArmClevis_L",
                     "LiftCylinder_BaseClevis_R", "LiftCylinder_ArmClevis_R",
                     "BucketCylinder_Barrel", "BucketCylinder_Rod",
                     "BucketCylinder_BaseClevis", "BucketCylinder_BellcrankClevis",
                     "LoaderArm_LiftPivot_ROOT_Reconstructed",
                     "ZBar_Bellcrank_Pivot_ROOT_Reconstructed"],
                    ["lift-cylinder-count", "lift-cylinder-bore", "lift-cylinder-stroke",
                     "bucket-cylinder-count", "bucket-cylinder-bore", "bucket-cylinder-stroke"]),
        {"lift_maximum_travel_m": PUBLISHED["lift-cylinder-stroke"],
         "bucket_maximum_travel_m": PUBLISHED["bucket-cylinder-stroke"],
         "minimum_barrel_rod_overlap_m": 0.0}, cylinder_evidence,
    ))

    apply_loader_pose("stowed")
    stowed_bucket_bounds = subtree_bounds("StockPileBucket_PivotRoot_Reconstructed")
    apply_loader_pose("raised_dump")
    raised_bucket_collision_bounds = subtree_bounds("StockPileBucket_PivotRoot_Reconstructed")
    bucket_ground_evidence = {
        "stowed_min_y_m": stowed_bucket_bounds["min_m"][1],
        "raised_min_y_m": raised_bucket_collision_bounds["min_m"][1],
        "stowed_bounds": stowed_bucket_bounds,
        "raised_bounds": raised_bucket_collision_bounds,
    }
    bucket_ground_ok = (-0.001 <= bucket_ground_evidence["stowed_min_y_m"] <= 0.03
                        and bucket_ground_evidence["raised_min_y_m"] >= 0.20)
    gates.append(make_gate(
        "bucket_ground_collision", "PASS" if bucket_ground_ok else "FAIL",
        gate_detail("Evaluated complete bucket-subtree vertices at carry/on-ground and raised-dump endpoints.",
                    bucket_ground_evidence,
                    ["StockPileBucket_PivotRoot_Reconstructed", "StockPileBucket_Shell",
                     "BucketSideGuard_L", "BucketSideGuard_R", "BucketBoltOnCuttingEdge"],
                    ["overall-length-stock-pile", "hinge-pin-height-carry-standard"]),
        {"stowed_y_range_m": [-0.001, 0.03], "raised_minimum_y_m": 0.20}, bucket_ground_evidence,
    ))

    cab_bounds = subtree_bounds("Cab_ROPS_Root_Reconstructed")
    front_frame_bounds = object_bounds("FrontFrame_Main")
    def box_separation(a: dict, b: dict) -> dict:
        gaps = []
        for axis in range(3):
            gaps.append(max(a["min_m"][axis] - b["max_m"][axis],
                            b["min_m"][axis] - a["max_m"][axis], 0.0))
        return {"axis_gaps_m": [round(value, 6) for value in gaps],
                "separation_m": round(max(gaps), 6), "overlap": all(value == 0.0 for value in gaps)}
    self_collision_evidence = {
        "stowed_bucket_to_cab": box_separation(stowed_bucket_bounds, cab_bounds),
        "raised_bucket_to_cab": box_separation(raised_bucket_collision_bounds, cab_bounds),
        "raised_bucket_to_front_frame": box_separation(raised_bucket_collision_bounds, front_frame_bounds),
    }
    self_collision_ok = all(not item["overlap"] for item in self_collision_evidence.values())
    gates.append(make_gate(
        "machine_self_collision", "PASS" if self_collision_ok else "FAIL",
        gate_detail("Evaluated AABB separation of the moving bucket against cab and front frame at stowed and raised endpoints.",
                    self_collision_evidence,
                    ["StockPileBucket_PivotRoot_Reconstructed", "StockPileBucket_Shell",
                     "Cab_ROPS_Root_Reconstructed", "FrontFrame_Main"], []),
        {"overlap": False}, self_collision_evidence,
    ))

    apply_loader_pose("stowed")
    apply_articulation(0.0)
    tire_clearance_samples = []
    for axle_angle in (-13.0, 0.0, 13.0):
        apply_rear_axle_oscillation(axle_angle)
        left = object_bounds("RearTire_L")
        right = object_bounds("RearTire_R")
        tire_clearance_samples.append({
            "rear_axle_deg": axle_angle,
            "left_lateral_gap_m": rear_body_bounds["min_m"][2] - left["max_m"][2],
            "right_lateral_gap_m": right["min_m"][2] - rear_body_bounds["max_m"][2],
        })
    apply_rear_axle_oscillation(0.0)
    front_body_bounds = object_bounds("FrontFrame_Main")
    front_left = object_bounds("FrontTire_L")
    front_right = object_bounds("FrontTire_R")
    front_gaps = {
        "left": front_body_bounds["min_m"][2] - front_left["max_m"][2],
        "right": front_right["min_m"][2] - front_body_bounds["max_m"][2],
    }
    tire_clearance_min = min(
        [sample["left_lateral_gap_m"] for sample in tire_clearance_samples]
        + [sample["right_lateral_gap_m"] for sample in tire_clearance_samples]
        + list(front_gaps.values()))
    tire_clearance_evidence = {"rear_samples": tire_clearance_samples,
                               "front_lateral_gap_m": front_gaps,
                               "minimum_gap_m": tire_clearance_min}
    gates.append(make_gate(
        "tire_body_clearance", "PASS" if tire_clearance_min >= 0.05 else "FAIL",
        gate_detail("Evaluated lateral tire-to-frame gaps at neutral front axle and -13/0/+13 degree rear-axle endpoints.",
                    tire_clearance_evidence,
                    ["RearTire_L", "RearTire_R", "FrontTire_L", "FrontTire_R",
                     "RearFrame_Spine", "FrontFrame_Main",
                     "RearAxle_Oscillation_Root_Reconstructed"], ["width-standard-tires"]),
        {"minimum_gap_m": 0.05}, tire_clearance_evidence,
    ))

    articulation_clearance_samples = []
    cab_center = world_machine_location("Cab_ROPS_Root_Reconstructed")
    for angle in (-40.0, -35.0, 0.0, 35.0, 40.0):
        apply_articulation(angle)
        front_centers = [world_machine_location(f"FrontWheel_{side}_Pivot_ROOT") for side in ("L", "R")]
        rear_centers = [world_machine_location(f"RearWheel_{side}_Pivot_ROOT") for side in ("L", "R")]
        wheel_center_separations = [
            math.hypot(front[0] - rear[0], front[2] - rear[2])
            for front in front_centers for rear in rear_centers]
        cab_horizontal_clearance = min(
            math.hypot(front[0] - cab_center[0], front[2] - cab_center[2])
            - RECONSTRUCTED["tire_outer_radius_m"] for front in front_centers)
        articulation_clearance_samples.append({
            "angle_deg": angle,
            "minimum_front_rear_wheel_center_separation_m": min(wheel_center_separations),
            "minimum_front_tire_to_cab_center_clearance_m": cab_horizontal_clearance,
        })
    apply_articulation(0.0)
    articulation_swept_ok = (
        min(sample["minimum_front_rear_wheel_center_separation_m"]
            for sample in articulation_clearance_samples) >= 2.0
        and min(sample["minimum_front_tire_to_cab_center_clearance_m"]
                for sample in articulation_clearance_samples) >= 0.60
    )
    articulation_swept_evidence = {"samples": articulation_clearance_samples}
    gates.append(make_gate(
        "articulation_swept_volume", "PASS" if articulation_swept_ok else "FAIL",
        gate_detail("Five-point maximum steering sweep measuring wheel-center separation and front-tire horizontal clearance from the rear cab center.",
                    articulation_swept_evidence,
                    ["Articulation_FrontFrame_Root_Reconstructed", "FrontWheel_L_Pivot_ROOT",
                     "FrontWheel_R_Pivot_ROOT", "RearWheel_L_Pivot_ROOT",
                     "RearWheel_R_Pivot_ROOT", "Cab_ROPS_Root_Reconstructed"],
                    ["steering-angle-nominal", "steering-angle-max-stop"]),
        {"minimum_wheel_center_separation_m": 2.0,
         "minimum_front_tire_to_cab_center_clearance_m": 0.60}, articulation_swept_evidence,
    ))

    apply_articulation(0.0)
    apply_rear_axle_oscillation(0.0)
    apply_loader_pose("stowed")

    object_names = {obj.name for obj in bpy.context.scene.objects}
    missing = [name for name in public_semantic_nodes() if name not in object_names]
    glb_missing = sorted(set(public_semantic_nodes()) - set(glb_contract["semantic_hierarchy"]))
    render_results = {str(path.relative_to(MACHINE_DIR)): render_quality(path) for path in RENDER_PATHS}
    render_ok = len(render_results) == 9 and all(
        item["bytes"] > 30000 and item["width"] >= 1000 and item["height"] >= 700
        for item in render_results.values())
    edge_segments = [name for name in object_names if name.startswith("BucketBOC_WearSegment_")]
    supplemental_detail = lambda method, evidence, nodes=None, facts=None: gate_detail(
        method, evidence, nodes or [], facts or [])
    gates.extend([
        make_gate("semantic-node-presence", "PASS" if not missing and not glb_missing else "FAIL",
                  supplemental_detail("Cross-check of required semantic names in the authored scene and decoded shipped GLB.",
                                      {"scene_missing": missing, "glb_missing": glb_missing}, public_semantic_nodes()),
                  {"missing": []}, {"scene_missing": missing, "glb_missing": glb_missing}),
        make_gate("selected-bolt-on-cutting-edge-detail",
                  "PASS" if len(edge_segments) == RECONSTRUCTED["bucket_cutting_edge_segments"] else "FAIL",
                  supplemental_detail("Count of visible replaceable B.O.C. wear segments on the selected stock-pile bucket.",
                                      {"segments": len(edge_segments)}, ["BucketBoltOnCuttingEdge"],
                                      ["bucket-capacity-heaped"]),
                  {"segments": RECONSTRUCTED["bucket_cutting_edge_segments"]}, {"segments": len(edge_segments)}),
        make_gate("render-non-emptiness", "PASS" if render_ok else "FAIL",
                  supplemental_detail("Raster decode, exact view count, dimensions and byte-floor check for the nine deterministic review views.",
                                      render_results),
                  {"views": 9, "minimum_bytes": 30000, "minimum_width": 1000, "minimum_height": 700},
                  render_results),
        make_gate("structural-triangle-budget",
                  "PASS" if 12000 <= counts["triangles"] <= RECONSTRUCTED["structural_triangle_budget"] else "FAIL",
                  supplemental_detail("Evaluated source-scene triangle count against the study budget.", counts),
                  {"minimum": 12000, "maximum": RECONSTRUCTED["structural_triangle_budget"]}, counts["triangles"]),
        make_gate("public-source-scales-applied", scale_audit["status"],
                  supplemental_detail("Before/after evaluated bounds and identity-scale audit after baking public mesh transforms.", scale_audit),
                  {"after_non_identity": [], "envelope_delta_max_m": 0.000001}, scale_audit),
        make_gate("public-glb-contract", glb_contract["status"],
                  supplemental_detail("Decoded GLB root, primitive, transform, helper-leak and semantic hierarchy inspection.",
                                      glb_contract, ["Machine_Root"]),
                  {"root": "Machine_Root", "helpers": []}, glb_contract),
    ])

    required = [gate for gate in gates if gate["id"] in required_gate_ids]
    required_counts = {gate_id: sum(gate["id"] == gate_id for gate in required)
                       for gate_id in required_gate_ids}
    malformed_details = []
    for gate in required:
        detail = gate.get("detail")
        if not isinstance(detail, dict) or set(("method", "evidence", "semantic_nodes", "fact_ids")) - set(detail):
            malformed_details.append(gate["id"])
            continue
        if (not isinstance(detail["method"], str) or not detail["method"]
                or not isinstance(detail["semantic_nodes"], list)
                or len(detail["semantic_nodes"]) != len(set(detail["semantic_nodes"]))
                or not isinstance(detail["fact_ids"], list)
                or len(detail["fact_ids"]) != len(set(detail["fact_ids"]))):
            malformed_details.append(gate["id"])
    covered_fact_ids = sorted({fact_id for gate in required
                               for fact_id in gate.get("detail", {}).get("fact_ids", [])})
    missing_fact_coverage = sorted(set(USED_FACT_IDS) - set(covered_fact_ids))
    contract_ok = (all(count == 1 for count in required_counts.values())
                   and not malformed_details and not missing_fact_coverage)
    gates.append(make_gate(
        "required-gate-contract", "PASS" if contract_ok else "FAIL",
        supplemental_detail("Exact required-gate ID cardinality, structured detail shape, unique semantic/fact arrays, and used-fact union coverage.",
                            {"counts": required_counts, "malformed_details": malformed_details,
                             "covered_fact_ids": covered_fact_ids,
                             "missing_used_fact_coverage": missing_fact_coverage}),
        {"count_per_required_id": 1, "missing_used_fact_coverage": []},
        {"counts": required_counts, "malformed_details": malformed_details,
         "missing_used_fact_coverage": missing_fact_coverage},
    ))
    gates.extend([
        make_gate("tire-transmission-engine-internals", "PENDING",
                  supplemental_detail("Boundary declaration; no hidden tire, KHMT, driveline or engine internals are fabricated.",
                                      {"unresolved": True})),
        make_gate("powered-hood-and-cooling-mask-motion", "PENDING",
                  supplemental_detail("Boundary declaration; service panels are visible but their unpublished actuator geometry remains unresolved.",
                                      {"unresolved": True})),
        make_gate("human-visual-critic", "PENDING",
                  supplemental_detail("Final integrated batch critic is outside this machine-local deterministic build.",
                                      {"pending": True})),
        make_gate("publication-release-deployment", "PENDING",
                  supplemental_detail("Release and deployment remain reserved to the parent integration lane.",
                                      {"pending": True})),
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
        "evaluated_visible_bounds_m": stowed_bounds,
        "required_gate_ids": required_gate_ids,
        "required_machine_gate_ids": required_gate_ids,
        "required_gate_contract": {
            "counts": required_counts,
            "malformed_details": malformed_details,
            "covered_fact_ids": covered_fact_ids,
            "missing_used_fact_coverage": missing_fact_coverage,
        },
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
        "release_status": "PENDING",
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
        "builder": {
            "path": str(BUILDER_PATH.relative_to(MACHINE_DIR)),
            "sha256": sha256(BUILDER_PATH),
            "bytes": BUILDER_PATH.stat().st_size,
        },
        "artifacts": {
            "blend": {"path": str(BLEND_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(BLEND_PATH), "bytes": BLEND_PATH.stat().st_size},
            "glb": {"path": str(GLB_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(GLB_PATH), "bytes": GLB_PATH.stat().st_size},
            "validation": {"path": str(VALIDATION_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(VALIDATION_PATH), "bytes": VALIDATION_PATH.stat().st_size},
            "facts": {"path": str(FACTS_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(FACTS_PATH), "bytes": FACTS_PATH.stat().st_size},
            "mechanism": {"path": str(MECHANISM_PATH.relative_to(MACHINE_DIR)), "sha256": sha256(MECHANISM_PATH), "bytes": MECHANISM_PATH.stat().st_size},
        },
        "scene": {
            "units": "meters",
            "machine_axes": "+X toward bucket, +Y vertical, +Z machine right",
            "blender_storage_mapping": "machine (X,Y,Z) -> Blender (X,Z,Y)",
            "glb_export_y_up": True,
            "bounds": {"evaluated_public_visible_retained_pose": validation["evaluated_visible_bounds_m"]},
            "triangles": glb_contract["public_glb_decoded_counts"]["triangles"],
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
        "published_constraint_ids_declared": [],
        "machine_specific_gate_evidence": [
            {"id": gate["id"], "status": gate["status"], "detail": gate["detail"]}
            for gate_id in validation["required_machine_gate_ids"]
            for gate in validation["gates"]
            if gate["id"] == gate_id
        ],
        "manufacturer_published_constraints_used": [
            {"id": fact_id, "value": FACT_RECORDS[fact_id]["value"],
             "unit": FACT_RECORDS[fact_id]["unit"],
             "source_id": FACT_RECORDS[fact_id]["source_id"],
             "location": FACT_RECORDS[fact_id]["location"],
             "use": "geometry_or_selected_configuration_constraint_with_reconstruction_boundary"}
            for fact_id in USED_FACT_IDS
        ],
        "fact_binding": {
            "method": "builder loads evidence/facts.json; missing, duplicate, non-published, non-numeric, unlocated, or unknown used IDs fail before scene creation",
            "used_fact_ids": list(USED_FACT_IDS),
            "unused_browseable_fact_ids": sorted(set(FACT_RECORDS) - set(USED_FACT_IDS)),
            "required_gate_fact_union": validation["required_gate_contract"]["covered_fact_ids"],
        },
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

"""
Mesh Analysis for Dinosaur Model Detection

Analyze mesh geometry to determine dinosaur type and body proportions.
"""
import bpy
import bmesh
from mathutils import Vector
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class BodySegment:
    """Identified body segment of the model."""
    name: str  # 'head', 'neck', 'torso', 'tail', 'front_leg', 'back_leg'
    center: Vector
    extent: Vector  # bounding box extent
    vertex_indices: List[int]
    confidence: float  # 0-1 how sure we are


@dataclass
class DinoMeshAnalysis:
    """Complete analysis of a dinosaur mesh."""
    is_valid_dino: bool
    detected_type: str  # 'bipedal', 'quadrupedal', 'unknown'
    symmetry_score: float  # 0-1 how symmetric
    body_segments: List[BodySegment]
    proportions: Dict[str, float]
    spine_length: float
    tail_length: float
    limb_length_front: float
    limb_length_back: float
    estimated_height: float
    confidence: float


def analyze_mesh(mesh_obj: bpy.types.Object) -> DinoMeshAnalysis:
    """Main entry point - analyze mesh and detect dinosaur type."""

    if mesh_obj.type != 'MESH':
        raise ValueError("Object must be a mesh")

    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    bm.transform(mesh_obj.matrix_world)
    vertices = [v.co for v in bm.verts]

    result = DinoMeshAnalysis(
        is_valid_dino=False,
        detected_type="unknown",
        symmetry_score=0.0,
        body_segments=[],
        proportions={},
        spine_length=0.0,
        tail_length=0.0,
        limb_length_front=0.0,
        limb_length_back=0.0,
        estimated_height=0.0,
        confidence=0.0
    )

    if len(vertices) < 100:
        result.confidence = 0.0
        return result

    # Detect bilateral symmetry
    result.symmetry_score = detect_symmetry(mesh_obj)

    # Find axis of symmetry (usually X axis for bilateral creatures)
    min_x = min(v.x for v in vertices)
    max_x = max(v.x for v in vertices)
    center_x = (min_x + max_x) / 2

    # Separate left/right vertices
    left_verts = [v for v in vertices if v.x < center_x - 0.1]
    right_verts = [v for v in vertices if v.x > center_x + 0.1]

    # Find extremities (tips of limbs, tail, head)
    extremities = find_extremities(vertices, center_x)

    # Identify body segments
    result.body_segments = identify_segments(vertices, extremities, center_x)

    # Determine dinosaur type from proportions
    front_limb_ext = extremities.get('front_limbs', [])
    back_limb_ext = extremities.get('back_limbs', [])
    tail_ext = extremities.get('tail', [])
    head_ext = extremities.get('head', [])

    # Bipedal indicators: back limbs much larger than front, or front limbs tiny/absent
    # Quadrupedal: front and back limbs of similar size

    if front_limb_ext and back_limb_ext:
        avg_front = sum(e.y for e in front_limb_ext) / len(front_limb_ext)
        avg_back = sum(e.y for e in back_limb_ext) / len(back_limb_ext)

        if avg_back > avg_front * 1.5:
            result.detected_type = "bipedal"
            result.confidence = 0.7
        elif 0.8 < (avg_front / avg_back) < 1.2:
            result.detected_type = "quadrupedal"
            result.confidence = 0.7
        else:
            result.detected_type = "unknown"
            result.confidence = 0.4
    else:
        result.detected_type = "unknown"
        result.confidence = 0.3

    result.is_valid_dino = result.confidence > 0.4

    # Calculate proportions
    result.proportions = calculate_proportions(vertices, extremities, center_x)
    result.estimated_height = max(e.y for e in extremities.get('back_limbs', [Vector((0, 0, 0))]))

    bm.free()
    return result


def detect_symmetry(mesh_obj: bpy.types.Object) -> float:
    """Detect bilateral symmetry of mesh. Returns 0-1 score."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = mesh_obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()

    verts = [mesh.vertices[i].co @ mesh_obj.matrix_world for i in range(len(mesh.vertices))]

    # Find center on X axis
    x_coords = [v.x for v in verts]
    center_x = (min(x_coords) + max(x_coords)) / 2

    # Mirror matching test - find pairs within tolerance
    tolerance = 0.1
    matched = 0
    total = 0

    for v in verts:
        if abs(v.x - center_x) > tolerance:  # Not on center plane
            total += 1
            # Look for mirrored vertex
            mirror_x = center_x - (v.x - center_x)
            has_match = any(
                abs(v.y - other.y) < tolerance and
                abs(v.z - other.z) < tolerance
                for other in verts
                if abs(other.x - mirror_x) < tolerance
            )
            if has_match:
                matched += 1

    mesh.release()
    return matched / total if total > 0 else 0.5


def find_extremities(vertices: List[Vector], center_x: float) -> Dict[str, List[Vector]]:
    """Find extremity points - tips of limbs, tail, head."""
    extremities = {
        'head': [],
        'tail': [],
        'front_limbs': [],
        'back_limbs': [],
    }

    if not vertices:
        return extremities

    min_y = min(v.y for v in vertices)
    max_y = max(v.y for v in vertices)
    min_z = min(v.z for v in vertices)
    max_z = max(v.z for v in vertices)

    y_range = max_y - min_y if max_y - min_y > 0 else 1
    z_range = max_z - min_z if max_z - min_z > 0 else 1

    # Sort vertices by Y (front-to-back) and Z (top-to-bottom)

    # Tail: far back (min Y), should be narrow (small Z extent for tip)
    tail_candidates = [v for v in vertices if v.y < min_y + y_range * 0.15]
    if tail_candidates:
        # Find tip (narrowest area at the back)
        tail_tips = sorted(tail_candidates, key=lambda v: abs(v.z - (min_z + max_z) / 2))
        extremities['tail'] = tail_tips[:3] if tail_tips else []

    # Head: front (max Y), narrow
    head_candidates = [v for v in vertices if v.y > max_y - y_range * 0.15]
    if head_candidates:
        head_tips = sorted(head_candidates, key=lambda v: abs(v.z - (min_z + max_z) / 2))
        extremities['head'] = head_tips[:3] if head_tips else []

    # Limbs: low Z (bottom), at front and back
    low_z_threshold = min_z + z_range * 0.3
    low_verts = [v for v in vertices if v.z < low_z_threshold]

    front_limbs = [v for v in low_verts if v.y > min_y + y_range * 0.2 and v.y < min_y + y_range * 0.5]
    back_limbs = [v for v in low_verts if v.y > min_y + y_range * 0.6]

    # Get highest points of limbs (ankle/wrist area)
    if front_limbs:
        extremities['front_limbs'] = get_limb_tips(front_limbs)
    if back_limbs:
        extremities['back_limbs'] = get_limb_tips(back_limbs)

    return extremities


def get_limb_tips(limb_verts: List[Vector]) -> List[Vector]:
    """Find the tips of limbs (lowest Z points)."""
    if not limb_verts:
        return []

    # Group by Y to find distinct limbs
    y_groups = {}
    for v in limb_verts:
        y_bucket = round(v.y * 4) / 4  # Bucket by 0.25 units
        if y_bucket not in y_groups:
            y_groups[y_bucket] = []
        y_groups[y_bucket].append(v)

    tips = []
    for y, verts in y_groups.items():
        # Get lowest (min Z) vertex in this Y group
        lowest = min(verts, key=lambda v: v.z)
        tips.append(lowest)

    return sorted(tips, key=lambda v: v.y)[:4]  # Return up to 4 tips


def identify_segments(vertices: List[Vector], extremities: Dict, center_x: float) -> List[BodySegment]:
    """Identify body segments from vertices and extremities."""
    segments = []

    # Simple heuristic: divide by Y coordinate
    if not vertices:
        return segments

    y_vals = sorted(set(v.y for v in vertices))
    y_range = y_vals[-1] - y_vals[0]
    bucket_size = y_range / 8

    y_buckets = {}
    for v in vertices:
        bucket = int(v.y / bucket_size)
        if bucket not in y_buckets:
            y_buckets[bucket] = []
        y_buckets[bucket].append(v)

    # Map buckets to segments
    for bucket, verts in y_buckets.items():
        if len(verts) < 10:
            continue

        center = sum(v for v in verts) / len(verts)
        extent_y = max(v.y for v in verts) - min(v.y for v in verts)
        extent_z = max(v.z for v in verts) - min(v.z for v in verts)
        extent_x = max(v.x for v in verts) - min(v.x for v in verts)

        # Determine segment type by position
        y_pos = center.y

        if bucket == min(y_buckets.keys()):
            seg_name = "tail"
        elif bucket == max(y_buckets.keys()):
            seg_name = "head"
        elif extent_x > extent_z * 1.5:
            seg_name = "torso"
        else:
            seg_name = "neck"

        segments.append(BodySegment(
            name=seg_name,
            center=center,
            extent=Vector((extent_x, extent_y, extent_z)),
            vertex_indices=[],
            confidence=0.6
        ))

    return segments


def calculate_proportions(vertices: List[Vector], extremities: Dict, center_x: float) -> Dict[str, float]:
    """Calculate body proportions."""
    props = {}

    if not vertices:
        return props

    min_y = min(v.y for v in vertices)
    max_y = max(v.y for v in vertices)
    min_z = min(v.z for v in vertices)
    max_z = max(v.z for v in vertices)
    max_x = max(v.x for v in vertices) - center_x  # Half width

    props['body_length'] = max_y - min_y
    props['body_height'] = max_z - min_z
    props['body_width'] = max_x * 2

    # Tail ratio
    if extremities.get('tail'):
        tail_tip = min(extremities['tail'], key=lambda v: v.y)
        tail_len = max_y - tail_tip.y
        props['tail_ratio'] = tail_len / props['body_length'] if props['body_length'] > 0 else 0

    return props


def get_analysis_summary(analysis: DinoMeshAnalysis) -> str:
    """Generate AI-friendly summary of mesh analysis."""
    lines = []

    lines.append("=== MESH ANALYSIS ===")
    lines.append(f"Valid Dino Shape: {analysis.is_valid_dino}")
    lines.append(f"Detected Type: {analysis.detected_type}")
    lines.append(f"Symmetry: {analysis.symmetry_score:.0%}")
    lines.append(f"Confidence: {analysis.confidence:.0%}")

    if analysis.proportions:
        lines.append(f"\nBody Proportions:")
        for k, v in analysis.proportions.items():
            lines.append(f"  {k}: {v:.2f}")

    if analysis.body_segments:
        lines.append(f"\nBody Segments Detected:")
        for seg in analysis.body_segments:
            lines.append(f"  - {seg.name} (center: {seg.center.to_tuple()})")

    lines.append(f"\nEstimated Height: {analysis.estimated_height:.2f} units")

    return "\n".join(lines)
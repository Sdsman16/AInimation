"""
Weight Painting Pipeline for Rigged Meshes

Expert weight painting capabilities for preparing meshes for animation.
Includes auto-weight generation, weight cleaning, mirroring, and optimization.
"""
import bpy
import bmesh
from mathutils import Vector, Matrix
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class WeightPaintResult:
    """Result of a weight painting operation."""
    success: bool
    message: str
    bones_modified: List[str] = None
    vertices_painted: int = 0
    max_weight: float = 1.0
    errors: List[str] = None


class WeightPainter:
    """Expert weight painting tools for character rigs."""

    def __init__(self, mesh_obj: bpy.types.Object, armature_obj: bpy.types.Object):
        if mesh_obj.type != 'MESH':
            raise ValueError(f"'{mesh_obj.name}' is not a mesh")
        if armature_obj.type != 'ARMATURE':
            raise ValueError(f"'{armature_obj.name}' is not an armature")

        self.mesh = mesh_obj
        self.armature = armature_obj
        self.armature_modifier = None
        self._setup_armature_modifier()

    def _setup_armature_modifier(self):
        """Ensure mesh has armature modifier with correct settings."""
        # Find existing modifier or create new
        for mod in self.mesh.modifiers:
            if mod.type == 'ARMATURE':
                self.armature_modifier = mod
                mod.object = self.armature
                return

        # Create new modifier
        self.armature_modifier = self.mesh.modifiers.new(name="Armature", type='ARMATURE')
        self.armature_modifier.object = self.armature
        self.armature_modifier.use_vertex_groups = True
        self.armature_modifier.use_bone_envelopes = False

    def auto_weight_from_closest_bone(self, falloff: float = 2.0) -> WeightPaintResult:
        """
        Automatic weight painting based on closest bone distance.
        Uses mesh-to-bone distance with falloff for smooth weights.

        Args:
            falloff: Distance falloff factor (higher = sharper falloff)

        Returns:
            WeightPaintResult with operation details
        """
        if self.mesh.data.is_editmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get mesh vertex positions in world space
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_mesh = self.mesh.evaluated_get(depsgraph)
        world_matrix = self.mesh.matrix_world

        verts = [(v.index, world_matrix @ v.co) for v in eval_mesh.data.vertices]
        bone_positions = self._get_bone_world_positions()

        if not bone_positions:
            return WeightPaintResult(False, "No bones found in armature")

        # Ensure vertex groups exist
        self._ensure_vertex_groups(bone_positions.keys())

        # Calculate weights for each vertex
        painted_verts = 0
        bones_modified = []

        for idx, vert_co in verts:
            # Find closest bone(s)
            closest = self._find_closest_bones(vert_co, bone_positions, max_count=4)

            if not closest:
                continue

            total_weight = 0
            weights = {}

            for bone_name, distance in closest:
                # Calculate weight based on distance (inverse square falloff)
                weight = 1.0 / (1.0 + (distance * falloff) ** 2)

                # Normalize across all contributing bones
                total_weight += weight
                weights[bone_name] = weight

            # Normalize and apply
            if total_weight > 0:
                for bone_name in weights:
                    normalized_weight = weights[bone_name] / total_weight
                    self._set_vert_weight(idx, bone_name, normalized_weight)
                    if bone_name not in bones_modified:
                        bones_modified.append(bone_name)
                painted_verts += 1

        return WeightPaintResult(
            success=True,
            message=f"Auto-weighted {painted_verts} vertices",
            vertices_painted=painted_verts,
            bones_modified=bones_modified
        )

    def _get_bone_world_positions(self) -> Dict[str, Vector]:
        """Get world positions of all bones (head and tail)."""
        positions = {}

        if self.armature.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bone_data = self.armature.data.bones
        world_inv = self.armature.matrix_world.inverted()

        for bone in bone_data:
            # Use bone head as position
            head_local = bone.head_local
            head_world = self.armature.matrix_world @ head_local
            positions[bone.name] = head_world

        return positions

    def _ensure_vertex_groups(self, bone_names: List[str]):
        """Ensure vertex groups exist for all bones."""
        existing = set(vg.name for vg in self.mesh.vertex_groups)
        for bone_name in bone_names:
            if bone_name not in existing:
                self.mesh.vertex_groups.new(name=bone_name)

    def _find_closest_bones(self, point: Vector, bone_positions: Dict[str, Vector],
                           max_count: int = 4) -> List[Tuple[str, float]]:
        """Find closest bones to a point, returning (bone_name, distance) tuples."""
        distances = []
        for bone_name, bone_pos in bone_positions.items():
            dist = (point - bone_pos).length
            distances.append((bone_name, dist))

        distances.sort(key=lambda x: x[1])
        return distances[:max_count]

    def _set_vert_weight(self, vert_idx: int, bone_name: str, weight: float):
        """Set weight for a single vertex in a vertex group."""
        vg = self.mesh.vertex_groups.get(bone_name)
        if vg:
            try:
                vg.add([vert_idx], weight, 'ADD')
            except:
                pass

    def weight_from_mesh_surface(self, bone_name: str, falloff: float = 1.5,
                                  invert: bool = False) -> WeightPaintResult:
        """
        Calculate weights based on mesh surface proximity to bone.
        Useful for muscle groups or complex surface deformations.

        Args:
            bone_name: Target bone
            falloff: Distance falloff
            invert: If True, closer = lower weight

        Returns:
            WeightPaintResult
        """
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_mesh = self.mesh.evaluated_get(depsgraph)

        # Get bone position
        if bone_name not in self.armature.data.bones:
            return WeightPaintResult(False, f"Bone '{bone_name}' not found")

        bone = self.armature.data.bones[bone_name]
        bone_center = self.armature.matrix_world @ bone.center

        # Get vertex positions
        world_matrix = self.mesh.matrix_world
        verts = [(v.index, (world_matrix @ v.co) - bone_center) for v in eval_mesh.data.vertices]

        # Ensure vertex group exists
        self._ensure_vertex_groups([bone_name])
        vg = self.mesh.vertex_groups[bone_name]

        # Calculate distance-based weights
        max_dist = 0
        for idx, vec in verts:
            dist = vec.length
            max_dist = max(max_dist, dist)

        # Apply weights with falloff
        painted = 0
        for idx, vec in verts:
            dist = vec.length
            normalized_dist = dist / max_dist if max_dist > 0 else 0

            if invert:
                weight = normalized_dist ** falloff
            else:
                weight = (1 - normalized_dist) ** falloff

            if weight > 0.001:
                vg.add([idx], weight, 'ADD')
                painted += 1

        return WeightPaintResult(
            success=True,
            message=f"Applied surface weights to {painted} vertices for '{bone_name}'",
            vertices_painted=painted,
            bones_modified=[bone_name]
        )

    @staticmethod
    def mirror_weights(axis: str = 'X', threshold: float = 0.001) -> WeightPaintResult:
        """
        Mirror weights across an axis.

        Args:
            axis: Axis to mirror across ('X', 'Y', 'Z')
            threshold: Distance threshold for matching vertices

        Returns:
            WeightPaintResult
        """
        mesh = bpy.context.active_object
        if not mesh or mesh.type != 'MESH':
            return WeightPaintResult(False, "No active mesh")

        if mesh.data.is_editmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get vertex positions
        verts = list(mesh.data.vertices)
        vg_names = [vg.name for vg in mesh.vertex_groups]

        mirror_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = mirror_map.get(axis.upper(), 0)

        mirrored = 0
        for v in verts:
            pos = v.co

            # Find mirrored vertex (flip the specified axis)
            mirrored_pos = list(pos)
            mirrored_pos[axis_idx] = -mirrored_pos[axis_idx]
            mirrored_vec = Vector(mirrored_pos)

            # Find closest vertex
            closest_v = None
            closest_dist = threshold
            for other_v in verts:
                if other_v.index == v.index:
                    continue
                dist = (other_v.co - mirrored_vec).length
                if dist < closest_dist:
                    closest_v = other_v
                    closest_dist = dist

            # Mirror weights
            if closest_v:
                for vg in mesh.vertex_groups:
                    try:
                        w1 = vg.weight(v.index)
                    except:
                        w1 = 0

                    try:
                        w2 = vg.weight(closest_v.index)
                    except:
                        w2 = 0

                    # Average or copy based on preference
                    avg_weight = (w1 + w2) / 2
                    vg.add([v.index], avg_weight, 'REPLACE')
                    vg.add([closest_v.index], avg_weight, 'REPLACE')
                    mirrored += 1
            else:
                # No mirror found, just copy if counterpart exists
                counterpart_name = vg.name.replace('.L', '.R').replace('.R', '.L').replace('_L', '_R').replace('_R', '_L')
                if counterpart_name in vg_names:
                    counterpart_vg = mesh.vertex_groups[counterpart_name]
                    try:
                        w = vg.weight(v.index)
                        counterpart_vg.add([v.index], w, 'REPLACE')
                    except:
                        pass

        return WeightPaintResult(
            success=True,
            message=f"Mirrored weights for {mirrored} vertices"
        )

    @staticmethod
    def clean_weights(threshold: float = 0.01, limit: float = 1.0) -> WeightPaintResult:
        """
        Clean weight painting by removing tiny weights and normalizing.

        Args:
            threshold: Minimum weight to keep
            limit: Maximum weight per vertex (1.0 = normalize)

        Returns:
            WeightPaintResult
        """
        mesh = bpy.context.active_object
        if not mesh or mesh.type != 'MESH':
            return WeightPaintResult(False, "No active mesh")

        if mesh.data.is_editmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        cleaned_verts = 0
        bones_affected = set()

        for v in mesh.data.vertices:
            total_weight = 0
            new_weights = {}

            # Collect and filter weights
            for vg in mesh.vertex_groups:
                try:
                    w = vg.weight(v.index)
                    if w >= threshold:
                        new_weights[vg.name] = w
                        total_weight += w
                except:
                    pass

            # Normalize if total > limit
            if total_weight > limit and total_weight > 0:
                for vg_name in new_weights:
                    new_weights[vg_name] = new_weights[vg_name] / total_weight
                    bones_affected.add(vg_name)

            # Apply cleaned weights
            for vg_name, w in new_weights.items():
                vg = mesh.vertex_groups.get(vg_name)
                if vg:
                    vg.add([v.index], w, 'REPLACE')

            if new_weights:
                cleaned_verts += 1

        return WeightPaintResult(
            success=True,
            message=f"Cleaned weights for {cleaned_verts} vertices",
            vertices_painted=cleaned_verts,
            bones_modified=list(bones_affected)
        )

    @staticmethod
    def normalize_all_verts(bone_names: List[str] = None) -> WeightPaintResult:
        """
        Normalize all vertex weights so they sum to 1.0.

        Args:
            bone_names: Specific bones to normalize, or None for all

        Returns:
            WeightPaintResult
        """
        mesh = bpy.context.active_object
        if not mesh or mesh.type != 'MESH':
            return WeightPaintResult(False, "No active mesh")

        if mesh.data.is_editmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        vgs = mesh.vertex_groups
        if bone_names:
            vgs = [vg for vg in vgs if vg.name in bone_names]

        normalized_verts = 0

        for v in mesh.data.vertices:
            total = 0
            weights = {}

            for vg in vgs:
                try:
                    w = vg.weight(v.index)
                    if w > 0:
                        weights[vg.name] = w
                        total += w
                except:
                    pass

            if total > 0 and len(weights) > 1:
                for vg_name, w in weights.items():
                    vg = mesh.vertex_groups.get(vg_name)
                    normalized = w / total
                    vg.add([v.index], normalized, 'REPLACE')

                normalized_verts += 1

        return WeightPaintResult(
            success=True,
            message=f"Normalized {normalized_verts} vertices",
            vertices_painted=normalized_verts
        )

    def create_envelope_weights(radius: float = 0.5, falloff: float = 2.0) -> WeightPaintResult:
        """
        Create weights based on bone envelopes (distance from bone).

        Args:
            radius: Bone envelope radius
            falloff: Weight falloff power

        Returns:
            WeightPaintResult
        """
        if self.mesh.data.is_editmode:
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get bone positions with envelope radii
        bone_envelopes = {}
        for bone in self.armature.data.bones:
            if bone.parent:
                length = bone.length
            else:
                length = radius * 2
            bone_envelopes[bone.name] = {
                'head': self.armature.matrix_world @ bone.head_local,
                'tail': self.armature.matrix_world @ bone.tail_local,
                'radius': radius
            }

        self._ensure_vertex_groups(bone_envelopes.keys())

        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_mesh = self.mesh.evaluated_get(depsgraph)
        world_matrix = self.mesh.matrix_world

        verts = [(v.index, world_matrix @ v.co) for v in eval_mesh.data.vertices]

        painted = 0
        bones_modified = []

        for idx, vert_co in verts:
            contributions = {}

            for bone_name, env in bone_envelopes.items():
                # Calculate distance to bone line segment
                dist = point_to_segment_distance(vert_co, env['head'], env['tail'])

                if dist < env['radius']:
                    weight = ((env['radius'] - dist) / env['radius']) ** falloff
                    contributions[bone_name] = weight

            if contributions:
                total = sum(contributions.values())
                for bone_name, w in contributions.items():
                    normalized = w / total if total > 0 else 0
                    self._set_vert_weight(idx, bone_name, normalized)
                    if bone_name not in bones_modified:
                        bones_modified.append(bone_name)
                painted += 1

        return WeightPaintResult(
            success=True,
            message=f"Created envelope weights for {painted} vertices",
            vertices_painted=painted,
            bones_modified=bones_modified
        )


def point_to_segment_distance(point: Vector, seg_start: Vector, seg_end: Vector) -> float:
    """Calculate distance from a point to a line segment."""
    segment = seg_end - seg_start
    length_sq = segment.length_squared

    if length_sq == 0:
        return (point - seg_start).length

    t = max(0, min(1, (point - seg_start).dot(segment) / length_sq))
    projection = seg_start + t * segment

    return (point - projection).length


def transfer_weights_from_source(source_mesh: bpy.types.Object,
                                  target_mesh: bpy.types.Object,
                                  source_armature: bpy.types.Object,
                                  target_armature: bpy.types.Object,
                                  method: str = 'AUTO') -> WeightPaintResult:
    """
    Transfer weights from one rigged mesh to another with different rig.

    Args:
        source_mesh: Mesh with existing weights
        target_mesh: Mesh to receive weights
        source_armature: Source armature
        target_armature: Target armature
        method: Transfer method ('AUTO', 'VERTICES', 'BONES')

    Returns:
        WeightPaintResult
    """
    if source_mesh.type != 'MESH' or target_mesh.type != 'MESH':
        return WeightPaintResult(False, "Both objects must be meshes")

    # Use data transfer if available
    if hasattr(bpy.ops.object, 'data_transfer'):
        bpy.context.view_layer.objects.active = target_mesh
        target_mesh.select_set(True)

        try:
            bpy.ops.object.data_transfer(
                data_type='VGROUP_WEIGHTS',
                use_reverse=False,
                map_method='Nearest Vertices',
                source_object=source_mesh,
                use_source_selection=False,
                use_subsurf_dist=True
            )
            return WeightPaintResult(True, "Weights transferred successfully")
        except:
            pass

    return WeightPaintResult(False, "Data transfer failed - manual weight painting required")


class BoneEnvelopeEditor:
    """Edit bone envelope settings for automatic weighting."""

    @staticmethod
    def set_envelope_radius(bone_name: str, radius: float, head_scale: float = 1.0, tail_scale: float = 1.0):
        """Set bone envelope radius and scale factors."""
        armature = bpy.context.active_object
        if not armature or armature.type != 'ARMATURE':
            return False

        if armature.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bone = armature.data.bones.get(bone_name)
        if not bone:
            return False

        bone.envelope_distance = radius
        bone.envelope_scale = 1.0

        return True

    @staticmethod
    def show_envelopes(visible: bool = True):
        """Toggle bone envelope display."""
        armature = bpy.context.active_object
        if not armature or armature.type != 'ARMATURE':
            return

        if armature.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        armature.data.show_envelopes = visible


class WeightGradientTool:
    """Tools for painting weight gradients between bones."""

    @staticmethod
    def paint_gradient(start_bone: str, end_bone: str, samples: int = 10, decay: str = 'linear'):
        """
        Paint a gradient of weights between two bones.

        Args:
            start_bone: Starting bone (full weight)
            end_bone: Ending bone (zero weight)
            samples: Number of gradient steps
            decay: 'linear', 'smooth', or 'sharp'
        """
        mesh = bpy.context.active_object
        if not mesh or mesh.type != 'MESH':
            return

        # Get vertex positions and start/end bone positions
        armature = bpy.context.object
        if not armature or armature.type != 'ARMATURE':
            return

        # This would require more complex implementation
        pass


def optimize_for_game_engine(target_fps: int = 60, max_bones_per_vert: int = 4) -> WeightPaintResult:
    """
    Optimize weights for real-time game engine use.

    Args:
        target_fps: Target frame rate
        max_bones_per_vert: Maximum bone influences per vertex

    Returns:
        WeightPaintResult
    """
    mesh = bpy.context.active_object
    if not mesh or mesh.type != 'MESH':
        return WeightPaintResult(False, "No active mesh")

    optimized_verts = 0

    for v in mesh.data.vertices:
        weights = []
        for vg in mesh.vertex_groups:
            try:
                w = vg.weight(v.index)
                if w > 0:
                    weights.append((vg.name, w))
            except:
                pass

        # Sort by weight descending
        weights.sort(key=lambda x: x[1], reverse=True)

        # Keep only top influences
        if len(weights) > max_bones_per_vert:
            # Normalize kept weights
            total = sum(w for _, w in weights[:max_bones_per_vert])
            for i, (vg_name, w) in enumerate(weights[:max_bones_per_vert]):
                if total > 0:
                    normalized = w / total
                    vg = mesh.vertex_groups.get(vg_name)
                    if vg:
                        vg.add([v.index], normalized, 'REPLACE')

            # Zero out removed weights
            for vg_name, _ in weights[max_bones_per_vert:]:
                vg = mesh.vertex_groups.get(vg_name)
                if vg:
                    vg.add([v.index], 0, 'REPLACE')

            optimized_verts += 1
        elif len(weights) > 1:
            # Normalize all weights
            total = sum(w for _, w in weights)
            if total > 0 and abs(total - 1.0) > 0.01:
                for vg_name, w in weights:
                    vg = mesh.vertex_groups.get(vg_name)
                    if vg:
                        normalized = w / total
                        vg.add([v.index], normalized, 'REPLACE')
                optimized_verts += 1

    return WeightPaintResult(
        success=True,
        message=f"Optimized {optimized_verts} vertices for game engine use (max {max_bones_per_vert} influences)"
    )


def get_weight_summary() -> Dict:
    """Get a summary of current weight painting state."""
    mesh = bpy.context.active_object
    if not mesh or mesh.type != 'MESH':
        return {}

    summary = {
        'total_verts': len(mesh.data.vertices),
        'vertex_groups': [],
        'unpainted_verts': 0,
        'fully_painted_verts': 0,
        'avg_influences': 0,
    }

    influences_per_vert = []
    unpainted = 0
    fully_painted = 0

    for v in mesh.data.vertices:
        weights = []
        for vg in mesh.vertex_groups:
            try:
                w = vg.weight(v.index)
                if w > 0:
                    weights.append((vg.name, w))
            except:
                pass

        count = len(weights)
        influences_per_vert.append(count)

        if count == 0:
            unpainted += 1
        elif count >= 4:
            fully_painted += 1

    summary['unpainted_verts'] = unpainted
    summary['fully_painted_verts'] = fully_painted
    summary['avg_influences'] = sum(influences_per_vert) / len(influences_per_vert) if influences_per_vert else 0

    for vg in mesh.vertex_groups:
        vg_summary = {'name': vg.name, 'vert_count': 0, 'total_weight': 0}
        for v in mesh.data.vertices:
            try:
                w = vg.weight(v.index)
                if w > 0:
                    vg_summary['vert_count'] += 1
                    vg_summary['total_weight'] += w
            except:
                pass
        summary['vertex_groups'].append(vg_summary)

    return summary
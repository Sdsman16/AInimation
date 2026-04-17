"""
Build Blender context snapshot for AI
"""
import bpy


def build_blender_context(context) -> dict:
    """Build a dictionary representing current Blender state for AI."""

    result = {
        'current_frame': context.scene.frame_current,
        'scene_name': context.scene.name,
        'selected_objects': [],
        'active_object': None,
        'active_action': None,
        'collections': [],
    }

    # Selected objects
    for obj in context.selected_objects:
        obj_info = {
            'name': obj.name,
            'type': obj.type,
            'location': list(obj.location),
            'rotation': list(obj.rotation_euler),
            'scale': list(obj.scale),
        }

        # Add vertex/face/edge count for meshes
        if obj.type == 'MESH' and obj.data:
            obj_info['vertex_count'] = len(obj.data.vertices)
            obj_info['face_count'] = len(obj.data.polygons)
            obj_info['edge_count'] = len(obj.data.edges)

        # Add bone count for armatures
        if obj.type == 'ARMATURE' and obj.data:
            obj_info['bone_count'] = len(obj.data.bones)

        result['selected_objects'].append(obj_info)

    # Active object
    active = context.active_object
    if active:
        result['active_object'] = {
            'name': active.name,
            'type': active.type,
            'location': list(active.location),
            'rotation': list(active.rotation_euler),
            'scale': list(active.scale),
        }

    # Active action
    if active and active.animation_data and active.animation_data.action:
        action = active.animation_data.action
        result['active_action'] = {
            'name': action.name,
            'frame_start': action.frame_start,
            'frame_end': action.frame_end,
            'use_cyclic': action.use_cyclic,
            'fcurve_count': len(action.fcurves),
        }

    # Collections
    for col in bpy.data.collections:
        result['collections'].append(col.name)

    return result


def get_animation_context(context) -> dict:
    """Get animation-specific context."""
    result = {'actions': [], 'armatures': []}

    for action in bpy.data.actions:
        action_info = {
            'name': action.name,
            'frame_start': action.frame_start,
            'frame_end': action.frame_end,
            'use_cyclic': action.use_cyclic,
            'fcurve_count': len(action.fcurves),
        }
        result['actions'].append(action_info)

    # Include armature info for rigs
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.data:
            arm_info = {
                'name': obj.name,
                'bone_count': len(obj.data.bones),
                'bones': [b.name for b in obj.data.bones[:50]],  # First 50 bones
            }
            # Categorize bones for recognition
            bone_names_lower = [b.name.lower() for b in obj.data.bones]
            arm_info['likely_type'] = _detect_dino_type(bone_names_lower)
            arm_info['likely_type'] = _detect_rig_type(bone_names_lower)
            result['armatures'].append(arm_info)

    return result


def _detect_rig_type(bone_names: list) -> str:
    """Detect if rig is human, dinosaur, or other."""
    # First check human
    human_result = detect_human_rig(bone_names)
    if human_result != "unknown":
        return human_result

    # Then check dinosaur
    dino_result = _detect_dino_type(bone_names)
    if dino_result != "unknown":
        return dino_result

    return "generic"


def _detect_dino_type(bone_names: list) -> str:
    """Detect likely dinosaur type from bone names."""
    lower_names = [n.lower() for n in bone_names]

    # Bipedal indicators - prominent leg bones with thigh/shin naming
    bipedal_score = sum(1 for n in lower_names if any(x in n for x in ['thigh', 'shin', 'foot']))
    # Quadrupedal indicators - front and back leg pairs
    quad_score = sum(1 for n in lower_names if any(x in n for x in ['front_leg', 'back_leg', 'foreleg', 'hindleg']))

    if bipedal_score >= 2 and quad_score < 2:
        return "bipedal (raptor/theropod style)"
    elif quad_score >= 2:
        return "quadrupedal (sauropod/stegosaur style)"
    else:
        return "unknown"


def detect_human_rig(bone_names: list) -> str:
    """Detect if armature appears to be a human rig."""
    lower_names = [n.lower() for n in bone_names]

    # Human indicators - spine chain + bilateral limbs
    has_pelvis = any('pelvis' in n or 'hip' in n for n in lower_names)
    has_spine = any('spine' in n for n in lower_names)
    has_thigh = any('thigh' in n or 'femur' in n for n in lower_names)
    has_shin = any('shin' in n or 'tibia' in n for n in lower_names)
    has_foot = any('foot' in n for n in lower_names)
    has_arm = any('arm' in n or 'humerus' in n or 'radius' in n for n in lower_names)
    has_hand = any('hand' in n or 'wrist' in n for n in lower_names)
    has_head = any('head' in n or 'skull' in n for n in lower_names)

    human_score = sum([has_pelvis, has_spine, has_thigh, has_shin, has_foot, has_arm, has_hand, has_head])

    if human_score >= 5:
        return "human (bipedal)"
    elif has_pelvis and has_spine and has_thigh:
        return "human-like (bipedal)"
    else:
        return "unknown"
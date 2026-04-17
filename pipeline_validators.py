"""
Animation Pipeline Validators

Verify Blender operations happen in correct order.
"""
import bpy
from typing import List, Tuple, Optional


def validate_mode_for_bone_creation() -> Tuple[bool, str]:
    """
    Validate we're in the correct mode to create bones.

    Returns:
        (is_valid, message)
    """
    if bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE':
        if bpy.context.mode == 'EDIT':
            return True, "Correct mode: EDIT mode for bone creation"
        else:
            return False, f"Wrong mode '{bpy.context.mode}' - must enter EDIT mode"

    return False, "No armature selected or active"


def validate_animation_context() -> Tuple[bool, str]:
    """
    Validate context for animation keyframe insertion.

    Returns:
        (is_valid, message)
    """
    obj = bpy.context.active_object

    if not obj:
        return False, "No active object"

    if obj.type != 'ARMATURE':
        return False, f"Object '{obj.name}' is not an armature"

    if obj.mode != 'POSE':
        return False, f"Wrong mode '{obj.mode}' - must be in POSE mode to insert keyframes"

    if not obj.animation_data:
        return False, "Armature has no animation_data"

    if not obj.animation_data.action:
        return False, "No active action - create one first with bpy.data.actions.new()"

    return True, "Ready for keyframe insertion"


def validate_armature_for_animation(armature_name: str) -> Tuple[bool, str]:
    """
    Validate armature is ready for animation operations.

    Returns:
        (is_valid, message)
    """
    armature = bpy.data.objects.get(armature_name)

    if not armature:
        return False, f"Armature '{armature_name}' not found"

    if armature.type != 'ARMATURE':
        return False, f"Object '{armature_name}' is type '{armature.type}', not ARMATURE"

    if not armature.data or not armature.data.bones:
        return False, f"Armature '{armature_name}' has no bones"

    if not armature.pose:
        return False, f"Armature '{armature_name}' has no pose"

    return True, f"Armature '{armature_name}' is valid for animation"


def get_required_mode_for_operation(operation: str) -> str:
    """
    Get required Blender mode for a given operation.

    Args:
        operation: 'create_bones', 'insert_keyframe', 'create_nla', 'modify_fcurve'

    Returns:
        Required mode string
    """
    modes = {
        'create_bones': 'EDIT',
        'insert_keyframe': 'POSE',
        'create_nla': 'OBJECT',
        'modify_fcurve': 'OBJECT',
        'add_driver': 'OBJECT',
        'create_constraint': 'POSE',
    }
    return modes.get(operation.lower(), 'OBJECT')


def ensure_correct_mode(operation: str) -> bool:
    """
    Switch to correct mode for operation if needed.

    Args:
        operation: Type of operation being performed

    Returns:
        True if mode was correct or successfully switched
    """
    required = get_required_mode_for_operation(operation)
    current = bpy.context.mode

    if current == required:
        return True

    # Can't switch modes if in certain states
    if 'EDIT' in current and required != 'OBJECT':
        return False

    try:
        if required == 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        elif required == 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        else:
            bpy.ops.object.mode_set(mode='OBJECT')
        return True
    except:
        return False


class PipelineValidator:
    """Validate pipeline operations in correct order."""

    def __init__(self, armature_name: str):
        self.armature_name = armature_name
        self.armature = bpy.data.objects.get(armature_name)
        self.errors = []
        self.warnings = []

    def validate_full_pipeline(self) -> Tuple[bool, List[str]]:
        """
        Validate entire pipeline readiness.

        Returns:
            (is_valid, messages)
        """
        messages = []

        # Check armature exists
        valid, msg = validate_armature_for_animation(self.armature_name)
        if not valid:
            messages.append(f"ERROR: {msg}")
            return False, messages
        messages.append(f"OK: {msg}")

        # Check bone creation readiness
        if bpy.context.active_object != self.armature:
            messages.append("WARNING: Armature not active - may need to set active")
        else:
            messages.append("OK: Armature is active")

        # Check we're in correct mode
        valid, msg = validate_mode_for_bone_creation()
        if valid:
            messages.append(f"OK: {msg}")
        else:
            messages.append(f"WARNING: {msg}")

        return len(self.errors) == 0, messages

    def get_pipeline_status(self) -> dict:
        """Get comprehensive pipeline status."""
        status = {
            'armature_exists': False,
            'has_pose_bones': False,
            'has_animation_data': False,
            'active_action': None,
            'nla_tracks': [],
            'current_mode': bpy.context.mode,
            'ready_for_bone_creation': False,
            'ready_for_keyframing': False,
        }

        if self.armature:
            status['armature_exists'] = True
            status['has_pose_bones'] = len(self.armature.pose.bones) > 0 if self.armature.pose else False

            if self.armature.animation_data:
                status['has_animation_data'] = True
                if self.armature.animation_data.action:
                    status['active_action'] = self.armature.animation_data.action.name
                status['nla_tracks'] = [t.name for t in self.armature.animation_data.nla_tracks]

        # Check mode readiness
        if status['current_mode'] == 'EDIT':
            status['ready_for_bone_creation'] = True
        if status['current_mode'] == 'POSE' and status['active_action']:
            status['ready_for_keyframing'] = True

        return status


def print_pipeline_status(armature_name: str):
    """Print readable pipeline status."""
    validator = PipelineValidator(armature_name)
    status = validator.get_pipeline_status()

    print(f"\n=== Pipeline Status for '{armature_name}' ===")
    print(f"Current Mode: {status['current_mode']}")
    print(f"Armature Exists: {status['armature_exists']}")
    print(f"Has Pose Bones: {status['has_pose_bones']}")
    print(f"Has Animation Data: {status['has_animation_data']}")
    print(f"Active Action: {status['active_action'] or 'None'}")
    print(f"NLA Tracks: {status['nla_tracks'] or 'None'}")
    print(f"Ready for Bone Creation: {status['ready_for_bone_creation']}")
    print(f"Ready for Keyframing: {status['ready_for_keyframing']}")
    print("=" * 50)
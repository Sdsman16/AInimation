"""
Blender AI Assistant - Claude Integration (using requests)
"""
import bpy
import json
from typing import Dict, List
from .context_builder import build_blender_context, get_animation_context
from .animation_analyzer import get_action_summary, detect_seamless_loop, get_loop_suggestions

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


class AIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def send_message(self, user_message: str, context: dict, model: str = "claude-sonnet-4-7") -> str:
        """Send message to Claude with Blender context."""

        system_prompt = self._build_system_prompt(context)
        system_prompt += self._build_command_prompt()

        # Add dinosaur context if relevant
        anim_context = get_animation_context(bpy.context)
        if anim_context.get('armatures'):
            system_prompt += "\n\n" + self._build_armature_prompt(anim_context['armatures'])

        # Use requests directly to call Anthropic API
        try:
            import requests
        except ImportError:
            return "Error: requests module not available in Blender's Python environment."

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }

        payload = {
            "model": model,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }

        try:
            response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Handle both newer API response format and legacy
            if "content" in data:
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        return block.get("text", "")
            elif "completion" in data:
                return data["completion"]

            return str(data)

        except requests.exceptions.Timeout:
            return "Error: Request timed out. Please try again."
        except requests.exceptions.HTTPError as e:
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error: {str(e)}"

    def validate_key(self) -> tuple:
        """Validate API key by making a simple request. Returns (success, message)."""
        try:
            import requests
        except ImportError:
            return False, "requests module not available"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }

        payload = {
            "model": "claude-haiku-4-5",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "hi"}]
        }

        try:
            response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                return True, "API key is valid"
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "API key forbidden - check permissions"
            else:
                return False, f"Error: HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "Request timed out"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return False, "Invalid API key"
            return False, f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def _build_system_prompt(self, context: dict) -> str:
        """Build system prompt with current Blender state."""

        blender_info = []

        # Scene info
        blender_info.append("=== BLENDER SCENE ===")
        blender_info.append(f"Current Frame: {context.get('current_frame', 1)}")
        blender_info.append(f"Scene: {context.get('scene_name', 'Unknown')}")

        # Selected objects
        selected = context.get('selected_objects', [])
        if selected:
            blender_info.append("\n=== SELECTED OBJECTS ===")
            for obj in selected:
                blender_info.append(f"- {obj['name']} ({obj['type']})")
                blender_info.append(f"  Location: {obj['location']}")
                if obj.get('vertex_count'):
                    blender_info.append(f"  Vertices: {obj['vertex_count']}")

        # Active object
        active = context.get('active_object')
        if active:
            blender_info.append("\n=== ACTIVE OBJECT ===")
            blender_info.append(f"Name: {active['name']}")
            blender_info.append(f"Type: {active['type']}")
            blender_info.append(f"Location: {active['location']}")
            blender_info.append(f"Rotation: {active['rotation']}")
            blender_info.append(f"Scale: {active['scale']}")

        # Active animation action
        action = context.get('active_action')
        if action:
            blender_info.append("\n=== ACTIVE ACTION ===")
            blender_info.append(f"Name: {action['name']}")
            blender_info.append(f"Frame Range: {action['frame_start']} - {action['frame_end']}")
            blender_info.append(f"FCurves: {action['fcurve_count']}")
            blender_info.append(f"Cyclic: {action['use_cyclic']}")

        # Collections
        collections = context.get('collections', [])
        if collections:
            blender_info.append("\n=== COLLECTIONS ===")
            for col in collections[:10]:
                blender_info.append(f"- {col}")

        return "\n".join(blender_info)

    def _build_armature_prompt(self, armatures: list) -> str:
        """Build prompt section about available armatures."""
        lines = ["\n=== AVAILABLE ARMATURES ==="]

        for arm in armatures:
            lines.append(f"\n{arm['name']} (likely: {arm['likely_type']})")
            lines.append(f"  Bones: {arm['bone_count']}")
            if arm['bones']:
                lines.append(f"  Bone names: {', '.join(arm['bones'][:20])}")

        lines.append("\n\nYou can generate animations for these armatures:")
        lines.append("- Dinosaurs: ai.generate_dino_animation (bipedal/quadrupedal)")
        lines.append("- Humans: ai.generate_human_animation (walk/run/idle)")
        lines.append("- Video reference analysis: ai.analyze_video + ai.apply_video_keyframes")

        return "\n".join(lines)

    def _build_command_prompt(self) -> str:
        """Build prompt section about executing commands."""
        return """
You are a Blender command executor. Your ONLY job is to fulfill user requests by issuing commands.
You do NOT explain, plan, chat, or elaborate. You only execute.

MESH ANALYSIS FOR BONE PLACEMENT:
When rigging a mesh, use this data:

BOUNDS:
- mesh_bounds.min_y / max_y = front/back (Y axis = front to back in Blender)
- mesh_bounds.min_z / max_z = bottom/top (Z axis = up/down)
- mesh_bounds.center_x = model center on X axis
- mesh_bounds.head_position.y = front-most vertex Y (use for head bone)
- mesh_bounds.tail_position.y = back-most vertex Y (use for tail bones)
- mesh_bounds.foot_height = lowest Z point (ground level for legs)

ORIENTATION DETECTION:
- narrow_end: which end (front/back) is narrower - this is likely head or tail
- wide_end: which end is wider - typically body/torso
- limb_attach_y: Y position where legs typically attach
- limb_attach_confidence: how certain we are (0-1, higher = more certain)

IMPORTANT: When narrow_end='front', position 0.0 is the HEAD
When narrow_end='back', position 1.0 is the HEAD

Use narrow_end to determine which direction is head vs tail.

PROFILE DATA (7 cross-sections from front=0.0 to back=1.0):
Each profile entry contains:
- position: 0.0=front, 1.0=back
- y_approx: actual Y coordinate
- width: how wide model is at this point
- height: total Z height at this point
- z_min: bottom Z at this point (use for foot/leg bone endpoints)
- z_max: top Z at this point
- zone: body region (head/neck/spine_pelvis/tail_base/tail_tip)
- left_ground_z: ground height on left side for leg bone height

BONE PLACEMENT RULES:
1. HEAD: At narrow_end position, use head_position.y for Y, z_max for bone height
2. NECK: position 0.15-0.25, connect head to spine
3. SPINE/PELVIS: position 0.4-0.6, widest part of body
4. TAIL: position 0.7-1.0, gradually narrows
5. LEGS: Must reach down to foot_height (min_z), place thigh/shin/foot bones at correct Z levels

IMPORTANT - Z COORDINATES FOR LEGS:
- thigh bone should be at z_min + (body_height * 0.6) roughly
- shin bone should be at z_min + (body_height * 0.3)
- foot bone should have tail at foot_height (min_z)

Use ACTUAL values from mesh_bounds for EVERY coordinate.

Command formats:
BLENDER_CMD: CREATE_OBJECT:MESH:ObjectName
BLENDER_CMD: CREATE_OBJECT:ARMATURE:ArmatureName
BLENDER_CMD: CREATE_BONE:armature:bone_name:head_x,y,z:tail_x,y,z
BLENDER_CMD: SET_PARENT:armature:child_bone:parent_bone
BLENDER_CMD: SET_FRAME:frame_number
BLENDER_CMD: ADD_KEYFRAME:ObjectName:property:frame

No text before, no text after. Only the command.
"""


def create_client(api_key: str) -> AIClient:
    return AIClient(api_key)

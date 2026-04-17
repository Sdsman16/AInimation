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

IMPORTANT: When building rigs or placing bones, you MUST analyze the provided mesh context first.
Use the mesh vertex positions to determine correct bone placement - do NOT use generic coordinates.

For example, to rig a dinosaur:
1. Look at the Y/Z bounds to find head (front), tail (back), top, bottom
2. Place bones at actual mesh extremities - head at max Y, tail at min Y, feet at min Z
3. Use the mesh center X for spine bones

When creating bones for a selected mesh:
- Pelvis/spine should be along center X, between min_y and max_y of mesh
- Head should be at max Y vertex positions
- Tail should be at min Y vertex positions
- Legs should extend down to min Z of mesh
- Match Y positions to actual mesh features

Command formats:
BLENDER_CMD: CREATE_OBJECT:MESH:ObjectName
BLENDER_CMD: CREATE_OBJECT:ARMATURE:ArmatureName
BLENDER_CMD: CREATE_BONE:armature:bone_name:head_x,y,z:tail_x,y,z
BLENDER_CMD: SET_PARENT:armature:child_bone:parent_bone
BLENDER_CMD: SET_FRAME:frame_number
BLENDER_CMD: ADD_KEYFRAME:ObjectName:property:frame

No text before, no text after. Only the command. Always analyze mesh context before placing bones.
"""


def create_client(api_key: str) -> AIClient:
    return AIClient(api_key)

"""
Blender AI Assistant - Claude Integration
"""
import bpy
import anthropic
from .context_builder import build_blender_context, get_animation_context
from .animation_analyzer import get_action_summary, detect_seamless_loop, get_loop_suggestions


class AIClient:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def send_message(self, user_message: str, context: dict, model: str = "claude-opus-4-7") -> str:
        """Send message to Claude with Blender context."""

        system_prompt = self._build_system_prompt(context)

        # Add dinosaur context if relevant
        anim_context = get_animation_context(bpy.context)
        if anim_context.get('armatures'):
            system_prompt += "\n\n" + self._build_armature_prompt(anim_context['armatures'])

        message = self.client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        return message.content[0].text

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
            for col in collections[:10]:  # Limit to 10
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
        lines.append("\nAvailable knowledge bases:")
        lines.append("- Dinosaur locomotion: bipedal (raptor/T-Rex style), quadrupedal (sauropod style)")
        lines.append("- Human locomotion: walk cycles, run cycles, idle variations")
        lines.append("- Video reference analysis: ai.analyze_video + ai.apply_video_keyframes")

        return "\n".join(lines)


def create_client(api_key: str) -> AIClient:
    return AIClient(api_key)
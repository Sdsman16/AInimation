"""
UI Panel for AI Assistant
"""
import bpy
from bpy.types import Panel


class AI_OT_send_message(bpy.types.Operator):
    """Send message to AI"""
    bl_idname = "ai.send_message"
    bl_label = "Send"
    bl_options = {'REGISTER'}

    def execute(self, context):
        prefs = bpy.context.preferences.addons.get("ai_assistant_blender")
        if not prefs:
            self.report({'ERROR'}, "Addon not configured")
            return {'FINISHED'}

        api_key = prefs.preferences.api_key
        if not api_key:
            self.report({'ERROR'}, "Please set API key in addon preferences")
            return {'FINISHED'}

        from .ai_client import create_client
        from .context_builder import build_blender_context
        from .response_executor import ResponseExecutor

        message = context.scene.ai_input_message
        if not message.strip():
            return {'FINISHED'}

        blender_context = build_blender_context(context)

        try:
            client = create_client(api_key)
            model = prefs.preferences.model
            response = client.send_message(message, blender_context, model)

            # Store in history
            history = context.scene.ai_chat_history
            entry = history.add()
            entry.role = "user"
            entry.content = message

            entry = history.add()
            entry.role = "assistant"
            entry.content = response

            # Clear input
            context.scene.ai_input_message = ""

            # Try to execute commands
            executor = ResponseExecutor()
            success, failures = executor.parse_and_execute(response)
            if failures > 0:
                self.report({'WARNING'}, f"Executed {success} commands, {failures} failed")

        except Exception as e:
            self.report({'ERROR'}, f"AI Error: {str(e)}")

        return {'FINISHED'}


class AI_PT_assistant_panel(Panel):
    """AI Assistant sidebar panel"""
    bl_label = "AI Assistant"
    bl_idname = "AI_PT_assistant_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AI Assistant"

    def draw(self, context):
        layout = self.layout

        # Check API key
        prefs = bpy.context.preferences.addons.get("ai_assistant_blender")
        if not prefs or not prefs.preferences.api_key:
            layout.label(text="Configure API key in addon preferences", icon='ERROR')
            return

        # AI Chat Section
        box = layout.box()
        box.label(text="AI Chat", icon='TEXT')

        # Input field - multi-line text box
        box.prop(context.scene, "ai_input_message", text="Ask the AI...", icon='GREASEPENCIL')

        # Send button
        row = box.row()
        row.operator("ai.send_message", text="Send", icon='PLAY')
        row.operator("ai.clear_history", text="Clear", icon='X')

        # Chat history display
        if hasattr(context.scene, 'ai_chat_history') and len(context.scene.ai_chat_history) > 0:
            history_box = box.box()
            history_box.label(text="History:", icon='COLLAPSEMENU')
            for msg in context.scene.ai_chat_history:
                if msg.role == "user":
                    for line in msg.content.split('\n')[:3]:
                        history_box.label(text=f"You: {line[:50]}", icon='USER')
                else:
                    for line in msg.content.split('\n')[:3]:
                        history_box.label(text=f"AI: {line[:50]}", icon='ROBOT')
                    if len(msg.content.split('\n')) > 3:
                        history_box.label(text="  ... (more)", icon='INFO')

        # Animation tools
        layout.separator()
        layout.label(text="Animation Tools:", icon='ACTION')
        row = layout.row(align=True)
        row.operator("ai.analyze_animation", text="Analyze Loop", icon='PLAY')
        row.operator("ai.list_actions", text="List Actions", icon='LIST')

        # Dinosaur animation tools
        layout.separator()
        layout.label(text="Dinosaur Animations:", icon='PREVIEW_RANGE')

        # Auto Rig section
        box = layout.box()
        box.label(text="Auto Rig:", icon='ARMATURE_DATA')
        box.operator("ai.analyze_mesh", text="Analyze Mesh", icon='VIEWZOOM')
        box.operator("ai.auto_rig", text="Build Rig", icon='PLUS')

        # Bipedal animations
        box = layout.box()
        box.label(text="Bipedal (Raptor/T-Rex):", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.operator("ai.generate_dino_animation", text="Walk").dino_type = "bipedal"
        row.operator("ai.generate_dino_animation", text="Run").dino_type = "bipedal"
        row = box.row(align=True)
        row.operator("ai.generate_dino_animation", text="Idle").dino_type = "bipedal"
        row.operator("ai.dino_knowledge", text="Info").dino_type = "bipedal"

        # Quadrupedal animations
        box = layout.box()
        box.label(text="Quadrupedal (Sauropod):", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.operator("ai.generate_dino_animation", text="Walk").dino_type = "quadrupedal"
        row.operator("ai.generate_dino_animation", text="Run").dino_type = "quadrupedal"
        row = box.row(align=True)
        row.operator("ai.generate_dino_animation", text="Idle").dino_type = "quadrupedal"
        row.operator("ai.dino_knowledge", text="Info").dino_type = "quadrupedal"

        # Human animations
        layout.separator()
        layout.label(text="Human Animations:", icon='ARMATURE_DATA')
        box = layout.box()
        box.label(text="Bipedal Human:", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.operator("ai.generate_human_animation", text="Walk").anim_type = "walk"
        row.operator("ai.generate_human_animation", text="Run").anim_type = "run"
        row = box.row(align=True)
        row.operator("ai.generate_human_animation", text="Idle").anim_type = "idle"
        row.operator("ai.human_knowledge", text="Info")
        box.operator("ai.auto_rig_human", text="Build Human Rig", icon='PLUS')

        # Video Reference Analyzer
        layout.separator()
        layout.label(text="Video Reference:", icon='MOVIE')
        box = layout.box()
        box.operator("ai.analyze_video", text="Analyze Video", icon='FILE_MOVIE')
        box.operator("ai.apply_video_keyframes", text="Apply to Armature", icon='ANIM')
        box.label(text="Upload video for AI to analyze poses", icon='INFO')

        # Blend Space / Pipeline Tools
        layout.separator()
        layout.label(text="Blend Space & FPS:", icon='ARROW_LEFTRIGHT')
        box = layout.box()
        row = box.row(align=True)
        row.operator("ai.create_blend_space", text="Walk Blend").anim_type = 'walk'
        row.operator("ai.create_blend_space", text="Run Blend").anim_type = 'run'
        row = box.row(align=True)
        row.operator("ai.resample_animation", text="Resample 60 FPS", icon='TIME')
        row.operator("ai.extend_animation", text="Extend Frames", icon='PLUS')

        # Weight Painting Tools
        layout.separator()
        layout.label(text="Weight Painting:", icon='BRUSH_WEIGHT')
        box = layout.box()
        box.label(text="Auto Weight:", icon='AUTOMATIC')
        box.operator("ai.auto_weight", text="Auto from Distance", icon='AUTOMATIC')
        box.operator("ai.envelope_weights", text="Bone Envelope", icon='SPHERE')

        box = layout.box()
        box.label(text="Clean & Optimize:", icon='WINDOW')
        row = box.row(align=True)
        row.operator("ai.clean_weights", text="Clean", icon='X')
        row.operator("ai.normalize_weights", text="Normalize", icon='ARROW_LEFTRIGHT')
        row = box.row(align=True)
        row.operator("ai.mirror_weights", text="Mirror X", icon='ARROW_LEFTRIGHT')
        row.operator("ai.optimize_game_weights", text="Game Opt", icon='SETTINGS')

        box = layout.box()
        box.operator("ai.weight_summary", text="Weight Summary", icon='INFO')

        # Game Engine Export
        layout.separator()
        layout.label(text="Game Engine Export:", icon='GAME')
        box = layout.box()
        box.label(text="Skeleton Validation:", icon='VIEWZOOM')
        row = box.row(align=True)
        row.operator("ai.validate_skeleton", text="Unity").engine = 'unity'
        row.operator("ai.validate_skeleton", text="Unreal").engine = 'unreal'
        box.operator("ai.engine_requirements", text="Engine Requirements", icon='QUESTION')

        box = layout.box()
        box.label(text="Export FBX:", icon='EXPORT')
        row = box.row(align=True)
        row.operator("ai.export_unity", text="Unity", icon='IMPORT')
        row.operator("ai.export_unreal", text="Unreal", icon='IMPORT')
        box.operator("ai.batch_export_animations", text="Batch Export All", icon='FILE')

        box = layout.box()
        box.label(text="Animation Optimization:", icon='DECORATE')
        row = box.row(align=True)
        row.operator("ai.simplify_animation", text="Simplify", icon='LONGDISPLAY')
        row.operator("ai.compress_animation", text="Compress", icon='STRING')
        row = box.row(align=True)
        if hasattr(context.scene, "ai_anim_fps"):
            row.prop(context.scene, "ai_anim_fps", text="FPS")
        row.operator("ai.resample_animation", text="Resample", icon='TIME')

        # Advanced Help
        layout.separator()
        layout.label(text="Engine Setup Help:", icon='QUESTION')
        box = layout.box()
        box.label(text="Unity Setup:", icon='GAME')
        box.label(text="• Root bone needed for Humanoid", icon='INFO')
        box.label(text="• FBX: Y-forward, Z-up", icon='INFO')
        box.label(text="• Animation: Bake every frame", icon='INFO')
        box.label(text="• Scale: 100x for UE to Unity", icon='INFO')

        box = layout.box()
        box.label(text="Unreal Setup:", icon='GAME')
        box.label(text="• Pelvis as root (no extra root)", icon='INFO')
        box.label(text="• FBX: X-forward, Z-up", icon='INFO')
        box.label(text="• Animation: Disable const tracks", icon='INFO')
        box.label(text="• Import: Use Animation Asset", icon='INFO')

        # Context info
        layout.separator()
        if context.active_object:
            obj = context.active_object
            layout.label(text=f"Active: {obj.name}", icon='OBJECT_DATA')
        if context.selected_objects:
            layout.label(text=f"Selected: {len(context.selected_objects)} objects", icon='SELECT_SET')


def register():
    bpy.utils.register_class(AI_OT_send_message)
    bpy.utils.register_class(AI_PT_assistant_panel)


def unregister():
    bpy.utils.unregister_class(AI_PT_assistant_panel)
    bpy.utils.unregister_class(AI_OT_send_message)
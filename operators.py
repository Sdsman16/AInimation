"""
Operators for AI Assistant
"""
import bpy
from bpy.types import Operator
from .ai_client import create_client
from .context_builder import build_blender_context
from .animation_analyzer import get_loop_suggestions, get_action_summary, get_available_actions
from .response_executor import ResponseExecutor
from .dino_generator import generate_animation
from .dino_knowledge import get_animation_summary
from .mesh_analyzer import analyze_mesh, get_analysis_summary
from .rig_builder import auto_rig_from_mesh
from .human_generator import generate_human_animation, apply_video_reference
from .human_knowledge import get_human_animation_summary
from .video_analyzer import analyze_video_reference
from .blend_space import (
    create_standard_walk_blend_space,
    create_standard_run_blend_space,
    resample_animation_for_game,
    extend_animation_for_smoothness,
    BlendSpaceGenerator
)
from .weight_painting import (
    WeightPainter,
    clean_weights,
    mirror_weights,
    normalize_all_verts,
    optimize_for_game_engine,
    get_weight_summary,
    transfer_weights_from_source
)
from .game_engine_export import (
    EngineTarget,
    ExportSettings,
    SkeletonValidator,
    AnimationExporter,
    AnimationOptimizer,
    quick_export_unreal,
    quick_export_unity,
    batch_export_animations,
    get_engine_requirements
)


class AI_OT_chat(Operator):
    """Send message to AI assistant"""
    bl_idname = "ai.chat"
    bl_label = "Send to AI"
    bl_options = {'REGISTER'}

    message: bpy.props.StringProperty(name="Message", default="")

    def execute(self, context):
        prefs = bpy.context.preferences.addons.get("ai_assistant_blender")
        if not prefs:
            self.report({'ERROR'}, "Addon not configured")
            return {'FINISHED'}

        api_key = prefs.preferences.api_key
        if not api_key:
            self.report({'ERROR'}, "Please set API key in addon preferences")
            return {'FINISHED'}

        # Build context
        blender_context = build_blender_context(context)

        # Create AI client
        try:
            client = create_client(api_key)
            model = prefs.preferences.model

            # Send message
            response = client.send_message(self.message, blender_context, model)

            # Store in chat history
            self._store_message(context, "user", self.message)
            self._store_message(context, "assistant", response)

            # Try to execute any commands in response
            executor = ResponseExecutor()
            success, failures = executor.parse_and_execute(response)
            if failures > 0:
                self.report({'WARNING'}, f"Executed {success} commands, {failures} failed")

        except Exception as e:
            self.report({'ERROR'}, f"AI Error: {str(e)}")

        return {'FINISHED'}

    def _store_message(self, context, role: str, content: str):
        """Store message in chat history."""
        if not hasattr(context.scene, 'ai_chat_history'):
            return

        history = context.scene.ai_chat_history
        entry = history.add()
        entry.role = role
        entry.content = content


class AI_OT_analyze_animation(Operator):
    """Analyze active animation for loop quality"""
    bl_idname = "ai.analyze_animation"
    bl_label = "Analyze Animation"
    bl_options = {'REGISTER'}

    def execute(self, context):
        active = context.active_object
        if not active or not active.animation_data or not active.animation_data.action:
            self.report({'INFO'}, "No active animation")
            return {'FINISHED'}

        action = active.animation_data.action
        analysis = get_loop_suggestions(action)
        summary = get_action_summary(action)

        # Store in chat history
        if hasattr(context.scene, 'ai_chat_history'):
            entry = context.scene.ai_chat_history.add()
            entry.role = "assistant"
            entry.content = f"Animation Analysis:\n{analysis}\n\nDetails:\n{summary}"

        self.report({'INFO'}, f"Analyzed: {action.name}")
        return {'FINISHED'}


class AI_OT_clear_history(Operator):
    """Clear chat history"""
    bl_idname = "ai.clear_history"
    bl_label = "Clear Chat"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if hasattr(context.scene, 'ai_chat_history'):
            context.scene.ai_chat_history.clear()
        return {'FINISHED'}


class AI_OT_list_actions(Operator):
    """List all available actions"""
    bl_idname = "ai.list_actions"
    bl_label = "List Actions"
    bl_options = {'REGISTER'}

    def execute(self, context):
        actions = get_available_actions()
        if not actions:
            self.report({'INFO'}, "No actions found")
            return {'FINISHED'}

        action_list = "\n".join([f"- {a['name']} ({a['frame_range'][0]}-{a['frame_range'][1]})" for a in actions])

        if hasattr(context.scene, 'ai_chat_history'):
            entry = context.scene.ai_chat_history.add()
            entry.role = "assistant"
            entry.content = f"Available Actions:\n{action_list}"

        self.report({'INFO'}, f"Found {len(actions)} actions")
        return {'FINISHED'}


class AI_OT_generate_dino_animation(Operator):
    """Generate dinosaur animation"""
    bl_idname = "ai.generate_dino_animation"
    bl_label = "Generate Dino Animation"
    bl_options = {'REGISTER'}

    dino_type: bpy.props.StringProperty(name="Dino Type", default="bipedal")
    anim_type: bpy.props.StringProperty(name="Animation Type", default="walk")
    speed: bpy.props.StringProperty(name="Speed", default="walk")
    duration: bpy.props.FloatProperty(name="Duration (seconds)", default=2.0, min=0.5, max=10.0)

    def execute(self, context):
        active = context.active_object

        if not active or active.type != 'ARMATURE':
            # Try to find an armature in selected
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        try:
            result = generate_animation(
                armature_name=active.name,
                dino_type=self.dino_type,
                anim_type=self.anim_type,
                speed=self.speed,
                duration=self.duration
            )

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = f"Generated animation: {result}"

            self.report({'INFO'}, f"Generated: {result}")

        except Exception as e:
            self.report({'ERROR'}, f"Generation failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_dino_knowledge(Operator):
    """Get dinosaur animation knowledge"""
    bl_idname = "ai.dino_knowledge"
    bl_label = "Dino Animation Help"
    bl_options = {'REGISTER'}

    dino_type: bpy.props.StringProperty(name="Dino Type", default="bipedal")

    def execute(self, context):
        summary = get_animation_summary(self.dino_type)

        if hasattr(context.scene, 'ai_chat_history'):
            entry = context.scene.ai_chat_history.add()
            entry.role = "assistant"
            entry.content = f"Dinosaur Animation Reference ({self.dino_type}):\n\n{summary}"

        self.report({'INFO'}, f"Displayed {self.dino_type} knowledge")
        return {'FINISHED'}


class AI_OT_analyze_mesh(Operator):
    """Analyze selected mesh for dinosaur type"""
    bl_idname = "ai.analyze_mesh"
    bl_label = "Analyze Mesh"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not context.active_object or context.active_object.type != 'MESH':
            # Try selected
            meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not meshes:
                self.report({'ERROR'}, "Select a mesh first")
                return {'FINISHED'}
            mesh_obj = meshes[0]
        else:
            mesh_obj = context.active_object

        try:
            analysis = analyze_mesh(mesh_obj)
            summary = get_analysis_summary(analysis)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = summary

            if analysis.is_valid_dino:
                self.report({'INFO'}, f"Detected: {analysis.detected_type} (confidence: {analysis.confidence:.0%})")
            else:
                self.report({'WARNING'}, "Mesh does not appear to be a dinosaur")

        except Exception as e:
            self.report({'ERROR'}, f"Analysis failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_auto_rig(Operator):
    """Auto-rig selected dinosaur mesh"""
    bl_idname = "ai.auto_rig"
    bl_label = "Auto Rig Mesh"
    bl_options = {'REGISTER'}

    rig_name: bpy.props.StringProperty(name="Rig Name", default="")

    def execute(self, context):
        if not context.active_object or context.active_object.type != 'MESH':
            meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not meshes:
                self.report({'ERROR'}, "Select a mesh first")
                return {'FINISHED'}
            mesh_obj = meshes[0]
        else:
            mesh_obj = context.active_object

        try:
            rig_name = self.rig_name if self.rig_name else f"{mesh_obj.name}_Rig"
            armature, summary = auto_rig_from_mesh(mesh_obj.name, rig_name)

            if armature:
                # Select and activate the new armature
                bpy.context.view_layer.objects.active = armature
                armature.select_set(True)

                if hasattr(context.scene, 'ai_chat_history'):
                    entry = context.scene.ai_chat_history.add()
                    entry.role = "assistant"
                    entry.content = summary + "\n\nRig has been created and selected."

                self.report({'INFO'}, f"Created rig: {armature.name}")
            else:
                self.report({'ERROR'}, summary)

        except Exception as e:
            self.report({'ERROR'}, f"Rig build failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_generate_human_animation(Operator):
    """Generate human animation (walk/run/idle)"""
    bl_idname = "ai.generate_human_animation"
    bl_label = "Generate Human Animation"
    bl_options = {'REGISTER'}

    anim_type: bpy.props.StringProperty(name="Animation Type", default="walk")
    speed: bpy.props.FloatProperty(name="Speed (m/s)", default=1.4, min=0.5, max=12.0)
    duration: bpy.props.FloatProperty(name="Duration (sec)", default=2.0, min=0.5, max=10.0)

    def execute(self, context):
        active = context.active_object

        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        try:
            result = generate_human_animation(
                armature_name=active.name,
                anim_type=self.anim_type,
                speed=self.speed,
                duration=self.duration
            )

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = f"Generated human animation: {result}"

            self.report({'INFO'}, f"Generated: {result}")

        except Exception as e:
            self.report({'ERROR'}, f"Generation failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_human_knowledge(Operator):
    """Get human animation knowledge"""
    bl_idname = "ai.human_knowledge"
    bl_label = "Human Animation Help"
    bl_options = {'REGISTER'}

    def execute(self, context):
        summary = get_human_animation_summary()

        if hasattr(context.scene, 'ai_chat_history'):
            entry = context.scene.ai_chat_history.add()
            entry.role = "assistant"
            entry.content = f"Human Animation Reference:\n\n{summary}"

        self.report({'INFO'}, "Displayed human animation knowledge")
        return {'FINISHED'}


class AI_OT_analyze_video(Operator):
    """Analyze video reference for animation"""
    bl_idname = "ai.analyze_video"
    bl_label = "Analyze Video Reference"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(name="Video File", subtype='FILE_PATH')

    def execute(self, context):
        prefs = bpy.context.preferences.addons.get("ai_assistant_blender")
        if not prefs or not prefs.preferences.api_key:
            self.report({'ERROR'}, "Set API key in addon preferences first")
            return {'FINISHED'}

        if not self.filepath:
            self.report({'ERROR'}, "No video file selected")
            return {'FINISHED'}

        try:
            analysis = analyze_video_reference(
                video_path=self.filepath,
                api_key=prefs.preferences.api_key,
                interval=0.5,
                max_frames=20
            )

            summary = f"""Video Analysis Complete:
File: {analysis.video_path}
Duration: {analysis.duration:.1f}s
FPS: {analysis.fps:.1f}
Resolution: {analysis.resolution[0]}x{analysis.resolution[1]}
Detected Motion: {analysis.motion_type}
Frames Analyzed: {analysis.frame_count}
Confidence: {analysis.confidence:.0%}"""

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = summary

            self.report({'INFO'}, f"Analyzed: {analysis.motion_type}")

        except Exception as e:
            self.report({'ERROR'}, f"Video analysis failed: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AI_OT_apply_video_animation(Operator):
    """Apply video-derived keyframes to selected armature"""
    bl_idname = "ai.apply_video_keyframes"
    bl_label = "Apply Video Keyframes"
    bl_options = {'REGISTER'}

    video_path: bpy.props.StringProperty(name="Video Path", default="")

    def execute(self, context):
        prefs = bpy.context.preferences.addons.get("ai_assistant_blender")
        if not prefs or not prefs.preferences.api_key:
            self.report({'ERROR'}, "Set API key in addon preferences first")
            return {'FINISHED'}

        if not self.video_path:
            self.report({'ERROR'}, "No video path set")
            return {'FINISHED'}

        active = context.active_object
        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        try:
            # First analyze video
            analysis = analyze_video_reference(
                video_path=self.video_path,
                api_key=prefs.preferences.api_key
            )

            if analysis.detected_poses:
                from .video_pose_extractor import create_animation_from_poses
                keyframes = create_animation_from_poses(analysis.detected_poses)
                result = apply_video_reference(active.name, keyframes)

                if hasattr(context.scene, 'ai_chat_history'):
                    entry = context.scene.ai_chat_history.add()
                    entry.role = "assistant"
                    entry.content = f"Applied {len(keyframes)} keyframes from video reference as '{result}'"

                self.report({'INFO'}, f"Applied {len(keyframes)} keyframes")
            else:
                self.report({'ERROR'}, "No poses detected in video")

        except Exception as e:
            self.report({'ERROR'}, f"Failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_auto_rig_human(Operator):
    """Auto-rig selected human mesh"""
    bl_idname = "ai.auto_rig_human"
    bl_label = "Build Human Rig"
    bl_options = {'REGISTER'}

    rig_name: bpy.props.StringProperty(name="Rig Name", default="")

    def execute(self, context):
        if not context.active_object or context.active_object.type != 'MESH':
            meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not meshes:
                self.report({'ERROR'}, "Select a mesh first")
                return {'FINISHED'}
            mesh_obj = meshes[0]
        else:
            mesh_obj = context.active_object

        try:
            rig_name = self.rig_name if self.rig_name else f"{mesh_obj.name}_HumanRig"

            # Use existing rig builder but with human bone structure
            from .rig_builder import DinoRigBuilder, DinoMeshAnalysis

            # Create a human-type analysis
            analysis = DinoMeshAnalysis(
                is_valid_dino=True,  # Treat as valid to trigger rig building
                detected_type="human",
                symmetry_score=0.9,
                body_segments=[],
                proportions={},
                spine_length=0,
                tail_length=0,
                limb_length_front=0,
                limb_length_back=0,
                estimated_height=1.0,
                confidence=0.9
            )

            # Build human rig using existing builder with modifications
            from .rig_builder import DinoRigBuilder
            builder = DinoRigBuilder(mesh_obj, analysis)

            # Override the rig building for human
            bpy.ops.object.mode_set(mode='OBJECT')

            arm_data = bpy.data.armatures.new(name=rig_name)
            armature = bpy.data.objects.new(name=rig_name, object_data=arm_data)
            bpy.context.scene.collection.objects.link(armature)

            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')

            builder.armature = armature
            builder.bone_positions = {}
            builder.created_bones = []

            bounds = builder._get_mesh_bounds()

            # Human spine chain
            for i in range(4):
                y_pos = bounds['front'] * 0.3 + i * (bounds['back'] - bounds['front']) * 0.15
                z_pos = bounds['center_z'] + bounds['height'] * 0.5
                builder._create_bone(f"spine_{i:02d}" if i > 0 else "spine_01",
                                     (bounds['center_x'], y_pos, z_pos),
                                     length=bounds['length'] * 0.1)

            # Pelvis
            builder._create_bone("pelvis",
                                 (bounds['center_x'], bounds['front'] * 0.2, bounds['center_z'] + bounds['height'] * 0.45),
                                 length=bounds['height'] * 0.15)

            # Legs
            leg_z = bounds['bottom'] + bounds['height'] * 0.5
            for side, x_offset in [('.R', bounds['width']), ('.L', -bounds['width'])]:
                builder._create_bone(f"thigh{side}",
                                     (bounds['center_x'] + x_offset, bounds['front'] * 0.2, leg_z),
                                     length=bounds['height'] * 0.35)
                builder._create_bone(f"shin{side}",
                                     (bounds['center_x'] + x_offset, bounds['front'] * 0.2 - 0.05, leg_z - bounds['height'] * 0.35),
                                     length=bounds['height'] * 0.32)
                builder._create_bone(f"foot{side}",
                                     (bounds['center_x'] + x_offset * 1.1, bounds['front'] * 0.15 + bounds['height'] * 0.1, bounds['bottom']),
                                     length=bounds['height'] * 0.12)

            # Arms
            arm_z = bounds['center_z'] + bounds['height'] * 0.55
            arm_y = bounds['front'] * 0.25
            for side, x_offset in [('.R', bounds['width'] * 0.7), ('.L', -bounds['width'] * 0.7)]:
                builder._create_bone(f"shoulder{side}",
                                     (bounds['center_x'] + x_offset, arm_y, arm_z),
                                     length=bounds['height'] * 0.1)
                builder._create_bone(f"upper_arm{side}",
                                     (bounds['center_x'] + x_offset * 1.1, arm_y - 0.1, arm_z),
                                     length=bounds['height'] * 0.25)
                builder._create_bone(f"forearm{side}",
                                     (bounds['center_x'] + x_offset * 1.2, arm_y - 0.2, arm_z - 0.05),
                                     length=bounds['height'] * 0.22)
                builder._create_bone(f"hand{side}",
                                     (bounds['center_x'] + x_offset * 1.3, arm_y - 0.3, arm_z - 0.05),
                                     length=bounds['height'] * 0.08)

            # Neck and head
            builder._create_bone("neck_01",
                                 (bounds['center_x'], bounds['front'] * 0.35, bounds['center_z'] + bounds['height'] * 0.6),
                                 length=bounds['height'] * 0.12)
            builder._create_bone("head",
                                 (bounds['center_x'], bounds['front'] * 0.4, bounds['center_z'] + bounds['height'] * 0.7),
                                 length=bounds['height'] * 0.25)

            # Parent bones
            builder._create_parenting()

            bpy.ops.object.mode_set(mode='OBJECT')

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = f"Human rig created with {len(builder.created_bones)} bones: {', '.join(builder.created_bones[:10])}..."

            self.report({'INFO'}, f"Created human rig: {armature.name}")

        except Exception as e:
            self.report({'ERROR'}, f"Human rig failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_create_blend_space(Operator):
    """Create animation blend space for smooth transitions"""
    bl_idname = "ai.create_blend_space"
    bl_label = "Create Blend Space"
    bl_options = {'REGISTER'}

    anim_type: bpy.props.EnumProperty(
        name="Animation Type",
        items=[('walk', 'Walk', 'Walk blend space'), ('run', 'Run', 'Run blend space')],
        default='walk'
    )

    def execute(self, context):
        active = context.active_object

        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        try:
            if self.anim_type == 'walk':
                result = create_standard_walk_blend_space(active.name)
            else:
                result = create_standard_run_blend_space(active.name)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = f"Created blend space: {result}"

            self.report({'INFO'}, f"Created: {result}")

        except Exception as e:
            self.report({'ERROR'}, f"Blend space failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_resample_animation(Operator):
    """Resample animation to different FPS (game-ready)"""
    bl_idname = "ai.resample_animation"
    bl_label = "Resample to 60 FPS"
    bl_options = {'REGISTER'}

    target_fps: bpy.props.IntProperty(name="Target FPS", default=60, min=24, max=120)

    def execute(self, context):
        active = context.active_object

        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        if not active.animation_data or not active.animation_data.action:
            self.report({'ERROR'}, "No active action to resample")
            return {'FINISHED'}

        action_name = active.animation_data.action.name

        try:
            result = resample_animation_for_game(active.name, action_name, self.target_fps)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = f"Resampled '{action_name}' to {self.target_fps} FPS: {result}"

            self.report({'INFO'}, f"Resampled: {result}")

        except Exception as e:
            self.report({'ERROR'}, f"Resample failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_extend_animation(Operator):
    """Extend animation with interpolated frames for smoother playback"""
    bl_idname = "ai.extend_animation"
    bl_label = "Extend Animation Frames"
    bl_options = {'REGISTER'}

    quality: bpy.props.IntProperty(name="Quality (multiplier)", default=4, min=2, max=8)

    def execute(self, context):
        active = context.active_object

        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        if not active.animation_data or not active.animation_data.action:
            self.report({'ERROR'}, "No active action to extend")
            return {'FINISHED'}

        action_name = active.animation_data.action.name

        try:
            result = extend_animation_for_smoothness(active.name, action_name, self.quality)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = f"Extended '{action_name}' by {self.quality}x: {result}"

            self.report({'INFO'}, f"Extended: {result}")

        except Exception as e:
            self.report({'ERROR'}, f"Extend failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_auto_weight(Operator):
    """Auto-generate weights from mesh proximity to bones"""
    bl_idname = "ai.auto_weight"
    bl_label = "Auto Weight Paint"
    bl_options = {'REGISTER'}

    falloff: bpy.props.FloatProperty(name="Falloff", default=2.0, min=0.5, max=10.0)

    def execute(self, context):
        mesh = context.active_object
        if not mesh or mesh.type != 'MESH':
            meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not meshes:
                self.report({'ERROR'}, "Select a mesh first")
                return {'FINISHED'}
            mesh = meshes[0]

        # Find armature
        armature = None
        for mod in mesh.modifiers:
            if mod.type == 'ARMATURE':
                armature = mod.object
                break

        if not armature:
            armatures = [obj for obj in context.scene.objects if obj.type == 'ARMATURE']
            if armatures:
                armature = armatures[0]

        if not armature:
            self.report({'ERROR'}, "No armature found")
            return {'FINISHED'}

        try:
            painter = WeightPainter(mesh, armature)
            result = painter.auto_weight_from_closest_bone(falloff=self.falloff)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = result.message

            self.report({'INFO'}, result.message)

        except Exception as e:
            self.report({'ERROR'}, f"Weight painting failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_clean_weights(Operator):
    """Clean small weights and normalize"""
    bl_idname = "ai.clean_weights"
    bl_label = "Clean Weights"
    bl_options = {'REGISTER'}

    threshold: bpy.props.FloatProperty(name="Threshold", default=0.01, min=0.001, max=0.1)

    def execute(self, context):
        try:
            result = clean_weights(threshold=self.threshold)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = result.message

            self.report({'INFO'}, result.message)

        except Exception as e:
            self.report({'ERROR'}, f"Clean failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_mirror_weights(Operator):
    """Mirror weights across X axis"""
    bl_idname = "ai.mirror_weights"
    bl_label = "Mirror Weights"
    bl_options = {'REGISTER'}

    axis: bpy.props.EnumProperty(
        name="Axis",
        items=[('X', 'X Axis', 'Mirror across X'), ('Y', 'Y Axis', 'Mirror across Y'), ('Z', 'Z Axis', 'Mirror across Z')],
        default='X'
    )

    def execute(self, context):
        try:
            result = mirror_weights(axis=self.axis)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = result.message

            self.report({'INFO'}, result.message)

        except Exception as e:
            self.report({'ERROR'}, f"Mirror failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_normalize_weights(Operator):
    """Normalize all vertex weights to sum to 1.0"""
    bl_idname = "ai.normalize_weights"
    bl_label = "Normalize Weights"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            result = normalize_all_verts()

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = result.message

            self.report({'INFO'}, result.message)

        except Exception as e:
            self.report({'ERROR'}, f"Normalize failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_optimize_game_weights(Operator):
    """Optimize weights for game engine (max 4 influences per vert)"""
    bl_idname = "ai.optimize_game_weights"
    bl_label = "Optimize for Game"
    bl_options = {'REGISTER'}

    max_influences: bpy.props.IntProperty(name="Max Influences", default=4, min=1, max=8)

    def execute(self, context):
        try:
            result = optimize_for_game_engine(max_bones_per_vert=self.max_influences)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = result.message

            self.report({'INFO'}, result.message)

        except Exception as e:
            self.report({'ERROR'}, f"Optimize failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_weight_summary(Operator):
    """Show weight painting summary"""
    bl_idname = "ai.weight_summary"
    bl_label = "Weight Summary"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            summary = get_weight_summary()

            if not summary:
                self.report({'INFO'}, "No mesh selected")
                return {'FINISHED'}

            report = f"""Weight Painting Summary:
Total Vertices: {summary.get('total_verts', 0)}
Unpainted: {summary.get('unpainted_verts', 0)}
Fully Painted (4+): {summary.get('fully_painted_verts', 0)}
Avg Influences: {summary.get('avg_influences', 0):.2f}

Vertex Groups:"""
            for vg in summary.get('vertex_groups', []):
                report += f"\n  {vg['name']}: {vg['vert_count']} verts"

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = report

            self.report({'INFO'}, "Weight summary displayed")

        except Exception as e:
            self.report({'ERROR'}, f"Summary failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_envelope_weights(Operator):
    """Generate weights based on bone envelopes"""
    bl_idname = "ai.envelope_weights"
    bl_label = "Bone Envelope Weights"
    bl_options = {'REGISTER'}

    radius: bpy.props.FloatProperty(name="Radius", default=0.5, min=0.1, max=2.0)
    falloff: bpy.props.FloatProperty(name="Falloff", default=2.0, min=0.5, max=5.0)

    def execute(self, context):
        mesh = context.active_object
        if not mesh or mesh.type != 'MESH':
            meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not meshes:
                self.report({'ERROR'}, "Select a mesh first")
                return {'FINISHED'}
            mesh = meshes[0]

        # Find armature
        armature = None
        for mod in mesh.modifiers:
            if mod.type == 'ARMATURE':
                armature = mod.object
                break

        if not armature:
            armatures = [obj for obj in context.scene.objects if obj.type == 'ARMATURE']
            if armatures:
                armature = armatures[0]

        if not armature:
            self.report({'ERROR'}, "No armature found")
            return {'FINISHED'}

        try:
            painter = WeightPainter(mesh, armature)
            result = painter.create_envelope_weights(radius=self.radius, falloff=self.falloff)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = result.message

            self.report({'INFO'}, result.message)

        except Exception as e:
            self.report({'ERROR'}, f"Envelope weights failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_validate_skeleton(Operator):
    """Validate skeleton for Unity/Unreal compatibility"""
    bl_idname = "ai.validate_skeleton"
    bl_label = "Validate Skeleton"
    bl_options = {'REGISTER'}

    engine: bpy.props.EnumProperty(
        name="Engine",
        items=[('unity', 'Unity', 'Unity Engine'), ('unreal', 'Unreal', 'Unreal Engine')],
        default='unity'
    )

    def execute(self, context):
        active = context.active_object
        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        engine = EngineTarget.UNITY if self.engine == 'unity' else EngineTarget.UNREAL

        try:
            validator = SkeletonValidator(active.name)
            is_valid, issues = validator.validate_for_engine(engine)

            report = validator.get_bone_mapping_report(engine)

            if hasattr(context.scene, 'ai_chat_history'):
                entry = context.scene.ai_chat_history.add()
                entry.role = "assistant"
                entry.content = f"Validation for {engine.value.upper()}:\n\n{report}\n\nIssues: {issues if issues else 'None'}"

            status = "Valid" if is_valid else "Has issues"
            self.report({'INFO'}, f"Skeleton {status}")

        except Exception as e:
            self.report({'ERROR'}, f"Validation failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_export_unreal(Operator):
    """Export armature to Unreal Engine FBX"""
    bl_idname = "ai.export_unreal"
    bl_label = "Export for Unreal"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(name="Output Path", subtype='FILE_PATH')

    def execute(self, context):
        active = context.active_object
        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        if not self.filepath:
            self.report({'ERROR'}, "No output path specified")
            return {'FINISHED'}

        try:
            result = quick_export_unreal(active.name, self.filepath)

            if result.success:
                if hasattr(context.scene, 'ai_chat_history'):
                    entry = context.scene.ai_chat_history.add()
                    entry.role = "assistant"
                    content = f"Exported to Unreal: {result.file_path}"
                    if result.warnings:
                        content += f"\nWarnings: {result.warnings}"
                    entry.content = content

                self.report({'INFO'}, f"Exported: {result.file_path}")
            else:
                self.report({'ERROR'}, result.message)

        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AI_OT_export_unity(Operator):
    """Export armature to Unity FBX"""
    bl_idname = "ai.export_unity"
    bl_label = "Export for Unity"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(name="Output Path", subtype='FILE_PATH')

    def execute(self, context):
        active = context.active_object
        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        if not self.filepath:
            self.report({'ERROR'}, "No output path specified")
            return {'FINISHED'}

        try:
            result = quick_export_unity(active.name, self.filepath)

            if result.success:
                if hasattr(context.scene, 'ai_chat_history'):
                    entry = context.scene.ai_chat_history.add()
                    entry.role = "assistant"
                    content = f"Exported to Unity: {result.file_path}"
                    if result.warnings:
                        content += f"\nWarnings: {result.warnings}"
                    entry.content = content

                self.report({'INFO'}, f"Exported: {result.file_path}")
            else:
                self.report({'ERROR'}, result.message)

        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AI_OT_batch_export_animations(Operator):
    """Export all animations for armature"""
    bl_idname = "ai.batch_export_animations"
    bl_label = "Batch Export Animations"
    bl_options = {'REGISTER'}

    directory: bpy.props.StringProperty(name="Output Directory", subtype='DIR_PATH')
    engine: bpy.props.EnumProperty(
        name="Engine",
        items=[('unity', 'Unity', 'Unity'), ('unreal', 'Unreal', 'Unreal')],
        default='unity'
    )

    def execute(self, context):
        active = context.active_object
        if not active or active.type != 'ARMATURE':
            armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
            if not armatures:
                self.report({'ERROR'}, "Select an armature first")
                return {'FINISHED'}
            active = armatures[0]

        if not self.directory:
            self.report({'ERROR'}, "No directory specified")
            return {'FINISHED'}

        engine = EngineTarget.UNITY if self.engine == 'unity' else EngineTarget.UNREAL

        try:
            results = batch_export_animations(active.name, self.directory, engine)

            success_count = sum(1 for r in results if r.success)
            self.report({'INFO'}, f"Exported {success_count}/{len(results)} animations")

            if hasattr(context.scene, 'ai_chat_history'):
                for r in results:
                    if r.success:
                        entry = context.scene.ai_chat_history.add()
                        entry.role = "assistant"
                        entry.content = f"Exported: {r.file_path}"

        except Exception as e:
            self.report({'ERROR'}, f"Batch export failed: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AI_OT_simplify_animation(Operator):
    """Simplify animation to reduce keyframes"""
    bl_idname = "ai.simplify_animation"
    bl_label = "Simplify Animation"
    bl_options = {'REGISTER'}

    tolerance: bpy.props.FloatProperty(name="Tolerance", default=0.001, min=0.0001, max=0.1)

    def execute(self, context):
        active = context.active_object
        if not active or active.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature first")
            return {'FINISHED'}

        if not active.animation_data or not active.animation_data.action:
            self.report({'ERROR'}, "No active animation")
            return {'FINISHED'}

        action_name = active.animation_data.action.name

        try:
            new_name = AnimationOptimizer.simplify_animation(action_name, self.tolerance)

            if new_name:
                if hasattr(context.scene, 'ai_chat_history'):
                    entry = context.scene.ai_chat_history.add()
                    entry.role = "assistant"
                    entry.content = f"Simplified animation: {new_name}"

                self.report({'INFO'}, f"Created: {new_name}")
            else:
                self.report({'ERROR'}, "Simplification failed")

        except Exception as e:
            self.report({'ERROR'}, f"Simplify failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_compress_animation(Operator):
    """Compress animation for Unreal (reduce precision)"""
    bl_idname = "ai.compress_animation"
    bl_label = "Compress for Unreal"
    bl_options = {'REGISTER'}

    precision: bpy.props.IntProperty(name="Precision", default=3, min=1, max=6)

    def execute(self, context):
        active = context.active_object
        if not active or active.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature first")
            return {'FINISHED'}

        if not active.animation_data or not active.animation_data.action:
            self.report({'ERROR'}, "No active animation")
            return {'FINISHED'}

        action_name = active.animation_data.action.name

        try:
            new_name = AnimationOptimizer.compress_for_unreal(action_name, self.precision)

            if new_name:
                if hasattr(context.scene, 'ai_chat_history'):
                    entry = context.scene.ai_chat_history.add()
                    entry.role = "assistant"
                    entry.content = f"Compressed animation: {new_name}"

                self.report({'INFO'}, f"Created: {new_name}")
            else:
                self.report({'ERROR'}, "Compression failed")

        except Exception as e:
            self.report({'ERROR'}, f"Compress failed: {str(e)}")

        return {'FINISHED'}


class AI_OT_engine_requirements(Operator):
    """Show game engine requirements"""
    bl_idname = "ai.engine_requirements"
    bl_label = "Engine Requirements"
    bl_options = {'REGISTER'}

    engine: bpy.props.EnumProperty(
        name="Engine",
        items=[('unity', 'Unity', 'Unity requirements'), ('unreal', 'Unreal', 'Unreal requirements')],
        default='unity'
    )

    def execute(self, context):
        engine = EngineTarget.UNITY if self.engine == 'unity' else EngineTarget.UNREAL
        requirements = get_engine_requirements(engine)

        if hasattr(context.scene, 'ai_chat_history'):
            entry = context.scene.ai_chat_history.add()
            entry.role = "assistant"
            entry.content = requirements

        self.report({'INFO'}, f"Displayed {engine.value} requirements")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(AI_OT_chat)
    bpy.utils.register_class(AI_OT_analyze_animation)
    bpy.utils.register_class(AI_OT_clear_history)
    bpy.utils.register_class(AI_OT_list_actions)
    bpy.utils.register_class(AI_OT_generate_dino_animation)
    bpy.utils.register_class(AI_OT_dino_knowledge)
    bpy.utils.register_class(AI_OT_analyze_mesh)
    bpy.utils.register_class(AI_OT_auto_rig)
    bpy.utils.register_class(AI_OT_generate_human_animation)
    bpy.utils.register_class(AI_OT_human_knowledge)
    bpy.utils.register_class(AI_OT_analyze_video)
    bpy.utils.register_class(AI_OT_apply_video_animation)
    bpy.utils.register_class(AI_OT_auto_rig_human)
    bpy.utils.register_class(AI_OT_create_blend_space)
    bpy.utils.register_class(AI_OT_resample_animation)
    bpy.utils.register_class(AI_OT_extend_animation)
    bpy.utils.register_class(AI_OT_auto_weight)
    bpy.utils.register_class(AI_OT_clean_weights)
    bpy.utils.register_class(AI_OT_mirror_weights)
    bpy.utils.register_class(AI_OT_normalize_weights)
    bpy.utils.register_class(AI_OT_optimize_game_weights)
    bpy.utils.register_class(AI_OT_weight_summary)
    bpy.utils.register_class(AI_OT_envelope_weights)
    bpy.utils.register_class(AI_OT_validate_skeleton)
    bpy.utils.register_class(AI_OT_export_unreal)
    bpy.utils.register_class(AI_OT_export_unity)
    bpy.utils.register_class(AI_OT_batch_export_animations)
    bpy.utils.register_class(AI_OT_simplify_animation)
    bpy.utils.register_class(AI_OT_compress_animation)
    bpy.utils.register_class(AI_OT_engine_requirements)


def unregister():
    bpy.utils.unregister_class(AI_OT_engine_requirements)
    bpy.utils.unregister_class(AI_OT_compress_animation)
    bpy.utils.unregister_class(AI_OT_simplify_animation)
    bpy.utils.unregister_class(AI_OT_batch_export_animations)
    bpy.utils.unregister_class(AI_OT_export_unity)
    bpy.utils.unregister_class(AI_OT_export_unreal)
    bpy.utils.unregister_class(AI_OT_validate_skeleton)
    bpy.utils.unregister_class(AI_OT_envelope_weights)
    bpy.utils.unregister_class(AI_OT_weight_summary)
    bpy.utils.unregister_class(AI_OT_optimize_game_weights)
    bpy.utils.unregister_class(AI_OT_normalize_weights)
    bpy.utils.unregister_class(AI_OT_mirror_weights)
    bpy.utils.unregister_class(AI_OT_clean_weights)
    bpy.utils.unregister_class(AI_OT_auto_weight)
    bpy.utils.unregister_class(AI_OT_extend_animation)
    bpy.utils.unregister_class(AI_OT_resample_animation)
    bpy.utils.unregister_class(AI_OT_create_blend_space)
    bpy.utils.unregister_class(AI_OT_auto_rig_human)
    bpy.utils.unregister_class(AI_OT_apply_video_animation)
    bpy.utils.unregister_class(AI_OT_analyze_video)
    bpy.utils.unregister_class(AI_OT_human_knowledge)
    bpy.utils.unregister_class(AI_OT_generate_human_animation)
    bpy.utils.unregister_class(AI_OT_auto_rig)
    bpy.utils.unregister_class(AI_OT_analyze_mesh)
    bpy.utils.unregister_class(AI_OT_dino_knowledge)
    bpy.utils.unregister_class(AI_OT_generate_dino_animation)
    bpy.utils.unregister_class(AI_OT_list_actions)
    bpy.utils.unregister_class(AI_OT_clear_history)
    bpy.utils.unregister_class(AI_OT_analyze_animation)
    bpy.utils.unregister_class(AI_OT_chat)
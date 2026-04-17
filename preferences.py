"""
User preferences for AI Assistant addon
"""
import bpy

ADDON_MODULE = "AInimation"


class AI_OT_validate_api_key(bpy.types.Operator):
    """Validate the API key"""
    bl_idname = "ai.validate_api_key"
    bl_label = "Validate API Key"
    bl_options = {'REGISTER'}

    def execute(self, context):
        prefs = bpy.context.preferences.addons.get(ADDON_MODULE)
        if not prefs:
            self.report({'ERROR'}, "Addon not found")
            return {'FINISHED'}

        api_key = prefs.preferences.api_key
        if not api_key:
            self.report({'ERROR'}, "Please enter an API key first")
            return {'FINISHED'}

        from .ai_client import AIClient
        client = AIClient(api_key)
        success, message = client.validate_key()

        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)

        return {'FINISHED'}


class AIAssistantPreferences(bpy.types.AddonPreferences):
    """API key and settings for AI Assistant."""
    bl_idname = ADDON_MODULE

    api_key: bpy.props.StringProperty(
        name="Anthropic API Key",
        description="Your Anthropic API key for Claude",
        subtype='PASSWORD',
        default="",
    )

    model: bpy.props.EnumProperty(
        name="Model",
        description="Claude model to use",
        items=[
            ('claude-opus-4-7', 'Opus 4.7', 'Most capable'),
            ('claude-sonnet-4-6', 'Sonnet 4.6', 'Balanced'),
            ('claude-haiku-4-5', 'Haiku 4.5', 'Fastest'),
        ],
        default='claude-opus-4-7',
    )

    def draw(self, context):
        layout = self.layout

        layout.label(text="AI Assistant Settings:")
        layout.prop(self, "api_key")

        row = layout.row()
        row.operator("ai.validate_api_key", text="Apply & Validate", icon='CHECKMARK')
        row.prop(self, "model")


def get_preferences():
    """Get addon preferences."""
    return bpy.context.preferences.addons.get(ADDON_MODULE)


def register():
    bpy.utils.register_class(AIAssistantPreferences)
    bpy.utils.register_class(AI_OT_validate_api_key)


def unregister():
    bpy.utils.unregister_class(AI_OT_validate_api_key)
    bpy.utils.unregister_class(AIAssistantPreferences)
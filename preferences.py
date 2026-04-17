"""
User preferences for AI Assistant addon
"""
import bpy


class AIAssistantPreferences(bpy.types.AddonPreferences):
    """API key and settings for AI Assistant."""
    bl_idname = __name__.split(".")[0]

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
        layout = context.layout
        layout.label(text="AI Assistant Settings:")
        layout.prop(self, "api_key")
        layout.prop(self, "model")


def get_preferences():
    """Get addon preferences."""
    return bpy.context.preferences.addons.get(__name__.split(".")[0])


def register():
    bpy.utils.register_class(AIAssistantPreferences)


def unregister():
    bpy.utils.unregister_class(AIAssistantPreferences)
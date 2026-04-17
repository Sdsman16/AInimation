"""
Blender AI Assistant - Claude Integration Addon

An AI assistant plugin for Blender that can help with scene queries,
modifications, and animation analysis using Claude models.
"""
bl_info = {
    "name": "AI Assistant",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > AI Assistant",
    "description": "Chat with Claude AI to query and modify your Blender scene",
    "category": "AI",
}

import bpy
from . import preferences, operators, ui


class ChatMessageItem(bpy.types.PropertyGroup):
    role: bpy.props.StringProperty()
    content: bpy.props.StringProperty()


def register():
    """Register all addon classes and properties."""
    # Preferences
    preferences.register()

    # Properties (must register before operators/ui)
    bpy.types.Scene.ai_input_message = bpy.props.StringProperty(
        name="AI Message",
        description="Message to send to AI assistant",
        default="",
    )

    bpy.types.Scene.ai_chat_history = bpy.props.CollectionProperty(
        type=ChatMessageItem,
        name="Chat History",
        description="Conversation history",
    )

    # Operators
    operators.register()

    # UI Panel
    ui.register()


def unregister():
    """Unregister all addon classes and properties."""
    # UI Panel
    ui.unregister()

    # Operators
    operators.unregister()

    # Properties
    if hasattr(bpy.types.Scene, "ai_chat_history"):
        del bpy.types.Scene.ai_chat_history
    if hasattr(bpy.types.Scene, "ai_input_message"):
        del bpy.types.Scene.ai_input_message

    # Preferences
    preferences.unregister()


if __name__ == "__main__":
    register()
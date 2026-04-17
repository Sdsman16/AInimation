# AInimation

AI-powered Blender addon for animation, game engine export, and automated skeletal rigging.

## Features

### AI Chat
- Chat with Claude AI directly in Blender's sidebar
- Query and modify your scene using natural language

### Animation Tools
- Analyze animations for loop quality
- List all available actions
- Generate walk/run/idle animations for human and dinosaur rigs

### Dinosaur Animation
- Auto-rig dinosaur meshes (bipedal & quadrupedal)
- Generate locomotion animations (walk, run, idle)
- Built-in dinosaur anatomy knowledge base

### Human Animation
- Human skeleton auto-rigging
- Procedural walk/run/idle animation generation
- Video reference pose extraction and animation transfer

### Video Reference
- Analyze video files for pose detection
- Apply extracted poses as keyframes to armatures

### Blend Space & FPS
- Create standard blend spaces (walk/run)
- Resample animations to game-ready FPS
- Extend animations with interpolated frames

### Weight Painting
- Auto-weight from mesh proximity
- Bone envelope weights
- Clean, normalize, mirror, and optimize weights

### Game Engine Export
- **Unity**: Skeleton validation, root bone setup, FBX export
- **Unreal**: Skeleton validation, pelvis-root export, FBX export
- Skeleton validation for both engines
- Batch animation export
- Animation simplification and compression

## Installation

**Direct Download:** [AInimation.zip](https://github.com/Sdsman16/AInimation/archive/refs/heads/main.zip)

1. Download the zip above
2. Open Blender and go to `Edit > Preferences > Add-ons`
3. Click `Install` and select the `ai_assistant_blender` folder
4. Enable the addon
5. Go to `Edit > Preferences > Add-ons > AI Assistant` and enter your Claude API key

## Requirements

- Blender 4.0+
- Anthropic Claude API key

## Usage

1. Open the **AI Assistant** panel in Blender's sidebar (View3D > Sidebar)
2. Configure your API key in addon preferences
3. Select an armature or mesh and use the various tools

## License

MIT

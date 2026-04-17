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

**Direct Download:** [AInimation.zip](https://github.com/Sdsman16/AInimation/releases/download/v1.0.5/AInimation.zip)

1. Download the zip above
2. Open Blender and go to `Edit > Preferences > Add-ons`
3. Click `Install` and select the downloaded zip
4. Enable the addon
5. Go to `Edit > Preferences > Add-ons > AI Assistant` and enter your Claude API key

## Requirements

- Blender 4.0+ (tested on Blender 5.1)
- Anthropic Claude API key

## How to Use

### Getting Started

1. Open Blender and find the **AI Assistant** panel in the right-hand sidebar (View3D > Sidebar)
2. Enter your Anthropic API key in the addon preferences
3. You're ready to start using the tools

### AI Chat

The AI Chat panel lets you query your Blender scene using natural language.

- Type any question about your scene (e.g., "What objects are selected?", "Give me a summary of the active armature")
- The AI has context about your current scene, selected objects, and animations
- Responses can include executable commands that modify your scene

### Rigging a Dinosaur

1. **Import or select your dinosaur mesh**
2. Click **Analyze Mesh** — the addon detects whether it's bipedal or quadrupedal
3. Click **Build Rig** — an armature is generated and attached to your mesh
4. Click **Auto Weight** to generate initial weights automatically

### Generating Animations

1. **Select your rigged armature** in the viewport
2. Choose your animation type:
   - **Walk / Run / Idle** buttons for quick generation
   - **Bipedal** for raptor/T-Rex style dinosaurs
   - **Quadrupedal** for sauropod-style dinosaurs
3. The animation is applied directly to the selected armature

### Exporting for Game Engines

#### Unity
1. Select your animated armature
2. Click **Validate Skeleton > Unity** — checks for root bone and naming conventions
3. Click **Unity** in the Export FBX section
4. In Unity: set FBX import to **Humanoid**, Y-forward, Z-up

#### Unreal Engine
1. Select your animated armature
2. Click **Validate Skeleton > Unreal** — checks for pelvis-root structure
3. Click **Unreal** in the Export FBX section
4. In Unreal: use **Animation Asset** import, X-forward, Z-up

### Weight Painting

- **Auto Weight** — generates weights based on bone proximity to mesh surface
- **Clean** — removes small weights below threshold and normalizes
- **Mirror X** — mirrors weights across the X axis
- **Normalize** — ensures all vertex weights sum to 1.0
- **Game Opt** — limits bone influences per vertex to 4 (game engine standard)

### Animation Tools

- **Analyze Loop** — checks if the current animation loops cleanly
- **List Actions** — shows all animations in the scene
- **Resample 60 FPS** — converts animation to 60 frames per second
- **Simplify** — reduces keyframe count while preserving motion
- **Compress** — reduces decimal precision for smaller file size

### Video Reference (AI Vision)

1. Click **Analyze Video** and select a video file
2. The addon extracts poses using Claude Vision AI
3. Click **Apply to Armature** to transfer keyframes to your rig

### Blend Spaces

- **Walk Blend** / **Run Blend** — creates 1D blend space assets for smooth locomotion transitions

### AI Knowledge Bases

- **Dino Info** — built-in reference for dinosaur anatomy and locomotion patterns
- **Human Info** — reference for human walk/run cycle proportions

## Quick Reference

| Task | Steps |
|------|-------|
| Rig a dinosaur | Import mesh → Analyze Mesh → Build Rig → Auto Weight |
| Animate for Unity | Build rig → Generate animation → Export FBX → Unity Humanoid |
| Animate for Unreal | Build rig → Generate animation → Export FBX → UE Animation Asset |
| Clean up weights | Select mesh → Clean → Normalize → Game Opt |
| Loop an animation | Select armature → Analyze Loop → Simplify (if needed) |

## License

MIT

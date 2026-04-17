"""
Parse and execute AI-proposed changes to Blender
"""
import bpy


class ResponseExecutor:
    """Execute AI-proposed changes to Blender scene."""

    def __init__(self):
        self.errors = []

    def execute_command(self, command: str) -> bool:
        """Execute a single Blender command."""
        print(f"Executing command: '{command}'")
        try:
            # Parse command type and execute
            if command.startswith("CREATE_OBJECT"):
                return self._create_object(command)
            elif command.startswith("MODIFY_PROPERTY"):
                return self._modify_property(command)
            elif command.startswith("SET_FRAME"):
                return self._set_frame(command)
            elif command.startswith("ADD_KEYFRAME"):
                return self._add_keyframe(command)
            elif command.startswith("ADD_BONE"):
                return self._add_bone(command)
            elif command.startswith("CREATE_BONE"):
                return self._add_bone(command)  # Alias for ADD_BONE
            elif command.startswith("SET_BONE_PARENT"):
                return self._set_bone_parent(command)
            elif command.startswith("SET_PARENT"):
                return self._set_bone_parent(command)  # Alias
            else:
                self.errors.append(f"Unknown command: {command}")
                return False
        except Exception as e:
            self.errors.append(str(e))
            print(f"Exception: {e}")
            return False

    def _create_object(self, command: str) -> bool:
        """Create a new object. Format: CREATE_OBJECT:type:name or CREATE_OBJECT:MESH:name"""
        parts = command.split(":")
        print(f"CREATE_OBJECT parts: {parts}")
        if len(parts) < 3:
            self.errors.append("Invalid CREATE_OBJECT format")
            return False

        # Handle case where it's just CREATE_OBJECT:MESH:name
        obj_type = parts[1]
        obj_name = parts[2]

        if obj_type == "MESH":
            mesh = bpy.data.meshes.new(obj_name)
            obj = bpy.data.objects.new(obj_name, mesh)
            bpy.context.scene.collection.objects.link(obj)
            return True
        elif obj_type == "LIGHT":
            light = bpy.data.lights.new(obj_name, type='POINT')
            obj = bpy.data.objects.new(obj_name, light)
            bpy.context.scene.collection.objects.link(obj)
            return True
        elif obj_type == "ARMATURE":
            arm_data = bpy.data.armatures.new(obj_name)
            obj = bpy.data.objects.new(obj_name, arm_data)
            bpy.context.scene.collection.objects.link(obj)
            return True

        self.errors.append(f"Unknown object type: {obj_type}")
        return False

    def _add_bone(self, command: str) -> bool:
        """Add bone to armature. Format: ADD_BONE:armature_name:bone_name:head_x,y,z:tail_x,y,z"""
        parts = command.split(":")
        if len(parts) < 4:
            self.errors.append("Invalid ADD_BONE format")
            return False

        arm_name = parts[1]
        bone_name = parts[2]
        head_str = parts[3].strip()
        tail_str = parts[4].strip() if len(parts) > 4 else head_str  # Default tail to head if not provided

        # Parse head and tail positions (handle spaces after commas)
        try:
            head = [float(x.strip()) for x in head_str.strip("[]").split(",")]
            tail = [float(x.strip()) for x in tail_str.strip("[]").split(",")]
        except:
            self.errors.append(f"Invalid bone coordinates: {head_str}, {tail_str}")
            return False

        arm_obj = bpy.data.objects.get(arm_name)
        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.errors.append(f"Armature not found: {arm_name}")
            return False

        # Enter edit mode to add bone
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')

        try:
            edit_bones = arm_obj.data.edit_bones
            bone = edit_bones.new(bone_name)
            bone.head = head
            bone.tail = tail
            return True
        except Exception as e:
            self.errors.append(f"Failed to add bone: {str(e)}")
            return False
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')

    def _set_bone_parent(self, command: str) -> bool:
        """Set bone parent. Format: SET_BONE_PARENT:armature:child_bone:parent_bone"""
        parts = command.split(":")
        if len(parts) < 4:
            self.errors.append("Invalid SET_BONE_PARENT format")
            return False

        arm_name = parts[1]
        child_bone = parts[2]
        parent_bone = parts[3]

        arm_obj = bpy.data.objects.get(arm_name)
        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.errors.append(f"Armature not found: {arm_name}")
            return False

        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')

        try:
            edit_bones = arm_obj.data.edit_bones
            if child_bone in edit_bones and parent_bone in edit_bones:
                edit_bones[child_bone].parent = edit_bones[parent_bone]
                return True
            else:
                self.errors.append(f"Bone not found")
                return False
        except Exception as e:
            self.errors.append(f"Failed to set parent: {str(e)}")
            return False
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')

    def _modify_property(self, command: str) -> bool:
        """Modify object property. Format: MODIFY_PROPERTY:object:property:value"""
        parts = command.split(":")
        if len(parts) < 4:
            self.errors.append("Invalid MODIFY_PROPERTY format")
            return False

        obj_name, prop_name, value = parts[1], parts[2], parts[3]

        obj = bpy.data.objects.get(obj_name)
        if not obj:
            self.errors.append(f"Object not found: {obj_name}")
            return False

        # Handle Vector values like [0.0,0.0,0.0]
        if value.startswith("["):
            try:
                vec_values = [float(x) for x in value.strip("[]").split(",")]
                setattr(obj, prop_name, vec_values)
                return True
            except:
                pass

        # Try numeric value
        try:
            setattr(obj, prop_name, float(value))
            return True
        except:
            pass

        self.errors.append(f"Cannot set property {prop_name} on {obj_name}")
        return False

    def _set_frame(self, command: str) -> bool:
        """Set current frame. Format: SET_FRAME:number"""
        parts = command.split(":")
        if len(parts) < 2:
            self.errors.append("Invalid SET_FRAME format")
            return False

        try:
            frame = int(parts[1])
            bpy.context.scene.frame_set(frame)
            return True
        except:
            self.errors.append(f"Invalid frame number: {parts[1]}")
            return False

    def _add_keyframe(self, command: str) -> bool:
        """Add keyframe. Format: ADD_KEYFRAME:object:property:frame"""
        parts = command.split(":")
        if len(parts) < 4:
            self.errors.append("Invalid ADD_KEYFRAME format")
            return False

        obj_name, prop_name, frame = parts[1], parts[2], int(parts[3])

        obj = bpy.data.objects.get(obj_name)
        if not obj:
            self.errors.append(f"Object not found: {obj_name}")
            return False

        try:
            obj.keyframe_insert(prop_name, frame=frame)
            return True
        except:
            self.errors.append(f"Cannot add keyframe for {prop_name} on {obj_name}")
            return False

    def parse_and_execute(self, response: str) -> tuple:
        """Parse AI response for commands and execute them."""
        lines = response.split("\n")
        success_count = 0
        fail_count = 0

        for line in lines:
            line = line.strip()
            if line.startswith("BLENDER_CMD:"):
                command = line[len("BLENDER_CMD:"):].strip()
                if self.execute_command(command):
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"Command failed: {command}")
                    print(f"Errors: {self.errors[-3:]}")  # Print last 3 errors

        if fail_count > 0:
            print(f"AI Response was:\n{response[:500]}...")  # Print first 500 chars of response

        return success_count, fail_count

    def get_errors(self) -> list:
        return self.errors
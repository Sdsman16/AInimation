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
        try:
            # Parse command type and execute
            if command.startswith("CREATE_OBJECT:"):
                return self._create_object(command)
            elif command.startswith("MODIFY_PROPERTY:"):
                return self._modify_property(command)
            elif command.startswith("SET_FRAME:"):
                return self._set_frame(command)
            elif command.startswith("ADD_KEYFRAME:"):
                return self._add_keyframe(command)
            else:
                self.errors.append(f"Unknown command: {command}")
                return False
        except Exception as e:
            self.errors.append(str(e))
            return False

    def _create_object(self, command: str) -> bool:
        """Create a new object. Format: CREATE_OBJECT:type:name"""
        parts = command.split(":")
        if len(parts) < 3:
            self.errors.append("Invalid CREATE_OBJECT format")
            return False

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

        self.errors.append(f"Unknown object type: {obj_type}")
        return False

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

        # Try to set property
        if hasattr(obj, prop_name):
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

        return success_count, fail_count

    def get_errors(self) -> list:
        return self.errors
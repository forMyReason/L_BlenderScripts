import bpy
import math
import random
from mathutils import Vector, Euler

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def setup_scene(size_x=5, size_y=5, size_z=4):
    primitives = ['primitive_cube_add', 'primitive_uv_sphere_add', 'primitive_cone_add', 'primitive_torus_add', 'primitive_monkey_add', 'primitive_cylinder_add']
    for _ in range(8):
        pos = (random.uniform(-size_x * 0.5 , size_x * 0.5), random.uniform(-0.5 * size_y, size_y * 0.5), random.uniform(0, size_z))
        primitive = random.choice(primitives)
        getattr(bpy.ops.mesh, primitive)(location=pos)
        obj = bpy.context.object
        obj.pass_index = _ + 1

        # 为每个物体新建材质并赋予随机颜色（优化为渲染消耗最小的材质）
        mat = bpy.data.materials.new(name=f"Material_{_}")
        mat.use_nodes = False                                                       # 禁用节点以减少渲染消耗
        mat.diffuse_color = (random.random(), random.random(), random.random(), 1)  # 随机颜色
        obj.data.materials.append(mat)

    bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
    light = bpy.context.object
    light.data.energy = 5

    direction = light.location - Vector((0, 10, 0))
    light.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()

    for _ in range(3):
        pos = (random.uniform(-3, 3), random.uniform(-3, 3), random.uniform(-2, 3) * 0.5)
        bpy.ops.object.light_add(type='POINT', location=pos)
        light = bpy.context.object
        light.data.energy = random.uniform(5, 10)
        
        light.data.color = (random.random(), random.random(), random.random())

# # TODO:可能需要调整摄像机看到的范围
def add_cameras(num=4, radius=15, height=8, fov=60):
    scene = bpy.context.scene
    cameras = []
    for i in range(num):
        angle = math.radians(i * 360 / num)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        bpy.ops.object.camera_add(location=(x, y, height))
        cam = bpy.context.object
        cam.rotation_mode = 'XYZ'
        
        direction = cam.location - Vector((0, 0, 0))
        cam.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
        
        # 设置摄像机的FOV
        cam.data.lens_unit = 'FOV'
        cam.data.angle = math.radians(fov)

        cameras.append(cam)
    return cameras

def set_animation(obj, start=1, end=250):
    scene = bpy.context.scene
    scene.frame_start = start  # 设置场景帧范围
    scene.frame_end = end
    
    # 物体动画
    if obj.type == 'MESH':
        for frame in range(start, end+1, 10):
            obj.location += Vector((
                random.uniform(-1.5,1.5),
                random.uniform(-1.5,1.5),
                random.uniform(-1,1)
            ))
            obj.keyframe_insert("location", frame=frame)
    
    # 摄像机动画
    if obj.type == 'CAMERA':
        obj.rotation_euler = Euler((
            math.radians(60),  # 俯角
            0,
            math.radians(90) + math.radians(obj.location.x)*0.1
        ), 'XYZ')
        
        # 增强动画幅度
        for frame in range(start, end+1, 10):
            obj.location += Vector((
                random.uniform(-0.8,0.8),
                random.uniform(-0.8,0.8),
                random.uniform(-0.5,0.5)
            ))
            obj.keyframe_insert("location", frame=frame)
            
            obj.rotation_euler = Euler((
                obj.rotation_euler.x + math.radians(random.uniform(-15,15)),
                obj.rotation_euler.y + math.radians(random.uniform(-10,10)),
                obj.rotation_euler.z + math.radians(random.uniform(-20,20))
            ))

            constraint = obj.constraints.new(type='TRACK_TO')
            constraint.target = bpy.data.objects.get('Empty') or bpy.data.objects.new('Empty', None)
            if not bpy.data.objects.get('Empty'):
                bpy.context.collection.objects.link(constraint.target)
                constraint.target.location = (0, 0, 0)
            constraint.track_axis = 'TRACK_NEGATIVE_Z'
            constraint.up_axis = 'UP_Y'

            # 让目标位置在每一帧都在3x3x3范围内变化
            target = constraint.target
            for frame in range(start, end + 1, 10):
                target.location = Vector((
                    random.uniform(-1.5, 1.5),
                    random.uniform(-1.5, 1.5),
                    random.uniform(-1.5, 1.5)
                ))
                target.keyframe_insert("location", frame=frame)

            # 对摄像机的旋转动画进行关键帧插值
            obj.keyframe_insert("rotation_euler", frame=frame)
            print(f"已为 {obj.name} 创建 {obj.animation_data.action.frame_range} 帧动画")


### 优化后的代码 ###
def setup_render(engine='CYCLES'):
    scene = bpy.context.scene
    
    scene.render.engine = engine
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540

    scene.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
    scene.render.image_settings.color_depth = '32'
    scene.render.use_motion_blur = False
    
    vl = scene.view_layers["ViewLayer"]
    
    vl.use_pass_combined = True       # RGB
    vl.use_pass_object_index = True   # ID
    
    # 创建自定义AOV
    def ensure_aov(layer, name):
        if name not in [aov.name for aov in layer.aovs]:
            new_aov = layer.aovs.add()
            new_aov.name = name
            new_aov.type = 'VALUE'
    
    # 节点配置
    scene.use_nodes = True
    node_tree = scene.node_tree
    node_tree.nodes.clear()
    
    rl_node = node_tree.nodes.new('CompositorNodeRLayers')
    rl_node.location = (400, 0)

    output_node = node_tree.nodes.new('CompositorNodeOutputFile')
    output_node.location = (800, 0)

    color_ramp_node = node_tree.nodes.new('CompositorNodeValToRGB')
    color_ramp_node.location = (600, 200)

    output_node.base_path = "//render/"
    output_node.format.file_format = 'OPEN_EXR_MULTILAYER'
    output_node.format.color_depth = '32'

    output_node.file_slots.new(name="Object Index")
    output_node.file_slots.new(name="Depth")
    output_node.file_slots.new(name="VerticalDistance")
    
    links = node_tree.links
    links.new(rl_node.outputs["Image"], output_node.inputs["Image"])
    links.new(rl_node.outputs["IndexOB"], output_node.inputs["Object Index"])
    links.new(rl_node.outputs["IndexOB"], color_ramp_node.inputs[0])
    links.new(color_ramp_node.outputs[0], output_node.inputs["Object Index"])


    output_node.format.exr_codec = 'ZIP'
    bpy.data.scenes["Scene"].node_tree.nodes["File Output"].format.color_depth = '16'
    
    if engine == 'CYCLES':
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True

def render_cameras(cameras):
    scene = bpy.context.scene
    original_camera = scene.camera

    scene.frame_start = 1
    scene.frame_end = 1
    
    for cam in cameras:
        scene.camera = cam
        scene.render.filepath = f"//renders/{cam.name}/frame_"
        
        print(f"正在使用摄像机 {cam.name} 渲染...")
        bpy.ops.render.render(animation=True)
    
    scene.camera = original_camera

clear_scene()
setup_scene()
cameras = add_cameras(4)

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        set_animation(obj)

for cam in cameras:
    set_animation(cam)

setup_render(engine='CYCLES')

# render_cameras(cameras)
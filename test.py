import bpy
import math
import random
from mathutils import Vector, Euler
import os

# 共生成多少个物体
num = 8
output_base_path = r"C:/Users/79160/Desktop/L_BlenderPlugin_1/renders/"
engine_type = 'BLENDER_EEVEE_NEXT'  # 'BLENDER_EEVEE_NEXT' or 'CYCLES'

def clear_scene():
    # Delete all objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Clear all data blocks
    for data_block in (bpy.data.materials, bpy.data.meshes, bpy.data.lights, 
                       bpy.data.cameras, bpy.data.textures, bpy.data.images, 
                       bpy.data.collections, bpy.data.actions, bpy.data.particles, 
                       bpy.data.worlds):
        for item in data_block:
            data_block.remove(item)

    # Clear all nodes in the compositor
    if bpy.context.scene.use_nodes:
        bpy.context.scene.node_tree.nodes.clear()

def setup_scene(size_x=5, size_y=5, size_z=4):
    primitives = ['primitive_cube_add', 'primitive_uv_sphere_add', 'primitive_cone_add', 'primitive_torus_add', 'primitive_monkey_add', 'primitive_cylinder_add']
    global num
    for _ in range(num):
        pos = (random.uniform(-size_x * 0.5 , size_x * 0.5), random.uniform(-0.5 * size_y, size_y * 0.5), random.uniform(0, size_z))
        primitive = random.choice(primitives)
        getattr(bpy.ops.mesh, primitive)(location=pos)
        obj = bpy.context.object
        # obj.pass_index = _ + 1  # 设置ID通道
        obj.pass_index = random.randint(1, 100)

        # 检查是否已有相同名称的材质，避免重复创建
        mat_name = f"Material_{_}"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = False  # 禁用节点以减少渲染消耗
            mat.diffuse_color = (random.random(), random.random(), random.random(), 1)  # 随机颜色
        obj.data.materials.append(mat)

    # 添加太阳光
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
    light = bpy.context.object
    light.data.energy = 5

    direction = light.location - Vector((0, 10, 0))
    light.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()

    # 添加3个点光源
    for _ in range(3):
        pos = (random.uniform(-3, 3), random.uniform(-3, 3), random.uniform(-2, 3) * 0.5)
        bpy.ops.object.light_add(type='POINT', location=pos)
        light = bpy.context.object
        light.data.energy = random.uniform(5, 10)
        
        # 设置随机颜色
        light.data.color = (random.random(), random.random(), random.random())

# 添加摄像机，从不同角度渲染，看向原点
# TODO:可能需要调整摄像机看到的范围
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
        
        # 让摄像机看向原点
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
    
    # 摄像机动画（修正拼写错误）
    if obj.type == 'CAMERA':
        # 确保摄像机初始朝向场景中心
        obj.rotation_euler = Euler((
            math.radians(60),  # 俯角
            0,
            math.radians(90) + math.radians(obj.location.x)*0.1
        ), 'XYZ')
        
        # 增强动画幅度
        for frame in range(start, end+1, 10):
            # 平移动画
            obj.location += Vector((
                random.uniform(-0.8,0.8),
                random.uniform(-0.8,0.8),
                random.uniform(-0.5,0.5)
            ))
            obj.keyframe_insert("location", frame=frame)
            
            # 旋转动画（更明显的变化）
            obj.rotation_euler = Euler((
                obj.rotation_euler.x + math.radians(random.uniform(-15,15)),
                obj.rotation_euler.y + math.radians(random.uniform(-10,10)),
                obj.rotation_euler.z + math.radians(random.uniform(-20,20))
            ))

            # 对摄像机进行限制，确保其始终朝向场景中心一定范围内
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
    
    # Format
    scene.render.engine = engine
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    
    # Frame Range
    scene.frame_start = 1
    scene.frame_end = 2
    scene.frame_step = 1

    # Output Settings
    scene.render.filepath = ""
    scene.render.use_file_extension = True
    scene.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
    scene.render.image_settings.color_depth = '32'
    scene.render.image_settings.exr_codec = 'ZIP'
    scene.render.use_overwrite = True
    scene.render.use_motion_blur = False

    # Compositing
    scene.render.use_compositing = True
    scene.render.use_compositing = True
    scene.render.dither_intensity = 1.0

    # 视图层配置
    vl = scene.view_layers["ViewLayer"]

    # Disable all unnecessary passes
    passes_to_disable = [
        "use_pass_combined", "use_pass_z", "use_pass_diffuse_color", 
        "use_pass_mist", "use_pass_normal", "use_pass_shadow", 
        "use_pass_ambient_occlusion", "use_pass_emit", "use_pass_environment", 
        "use_pass_diffuse_direct", "use_pass_diffuse_indirect", 
        "use_pass_glossy_direct", "use_pass_glossy_indirect", 
        "use_pass_transmission_direct", "use_pass_transmission_indirect", 
        "use_pass_subsurface_direct", "use_pass_subsurface_indirect"
    ]
    
    for pass_name in passes_to_disable:
        setattr(vl, pass_name, False)
    
    # 启用基础通道
    vl.use_pass_combined = True         # RGB
    vl.use_pass_z = True                # Z-depth（垂直平面距离）
    vl.use_pass_diffuse_color = True    # 彩色ID图，把diffuse color渲染作ID图
        
    # 节点系统配置
    if not scene.node_tree:
        scene.use_nodes = True
    node_tree = scene.node_tree
    node_tree.nodes.clear()
    
    # 创建render layer节点
    rl_node = node_tree.nodes.new('CompositorNodeRLayers')
    rl_node.location = (400, 0)

    # 创建file_output输出节点
    output_node = node_tree.nodes.new('CompositorNodeOutputFile')           # file output 渲染设置继承全局设置，其中输出路径在渲染部分动态更新
    output_node.name = "FileOutputNode"
    output_node.location = (900, 0)

    output_node.format.file_format = 'OPEN_EXR_MULTILAYER'  # 显式设置格式
    output_node.format.color_depth = '32'
    output_node.format.exr_codec = 'ZIP'

    output_node.file_slots.clear()
    # # 连接节点
    links = node_tree.links

    if engine == 'CYCLES' and "CameraDistance" not in vl.aovs:
        aov = vl.aovs.add()
        aov.name = "CameraDistance"
        aov.type = 'VALUE'

    output_slots = [
        ("Image", "RGB"),
        ("DiffCol", "Object Index"),
        ("Depth", "Depth"),
        ("Mist", "Mist") if engine == 'EEVEE' else ("CameraDistance", "CameraDistance")
    ]
    
    for socket, name in output_slots:
        slot = output_node.file_slots.new(name)
        links.new(rl_node.outputs[socket], output_node.inputs[name])

    # 深度通道归一化（仅Cycles需要）
    if engine == 'CYCLES':
        normalize = node_tree.nodes.new('CompositorNodeNormalize')
        normalize.location = (700, -100)
        normalize.label = 'Normalize Depth'
        links.new(rl_node.outputs['Depth'], normalize.inputs[0])
        links.new(normalize.outputs[0], output_node.inputs['Depth'])
    
    # 引擎特定配置
    if engine == 'CYCLES':
        # Cycles配置
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True
        scene.cycles.device = 'CPU'         # 全局设置CPU渲染，只有cycles分CPU和GPU

        # 创建自定义AOV
        if "CameraDistance" not in vl.aovs:
            aov = vl.aovs.add()
            aov.name = "CameraDistance"
            aov.type = 'VALUE'
        
        # 创建距离计算材质
        if not bpy.data.materials.get("AOV_Distance"):
            mat = bpy.data.materials.new("AOV_Distance")
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            nodes.clear()

            # 节点网络
            geometry = nodes.new('ShaderNodeNewGeometry')
            camera = nodes.new('ShaderNodeCameraData')
            math_sub = nodes.new('ShaderNodeVectorMath')
            math_sub.operation = 'SUBTRACT'
            math_length = nodes.new('ShaderNodeVectorMath')
            math_length.operation = 'LENGTH'
            aov_out = nodes.new('ShaderNodeOutputAOV')
            aov_out.name = 'CameraDistance'
            
            # 连接节点
            links = mat.node_tree.links
            links.new(camera.outputs["View Vector"], math_sub.inputs[0])
            links.new(geometry.outputs["Position"], math_sub.inputs[1])
            links.new(math_sub.outputs["Vector"], math_length.inputs[0])
            links.new(math_length.outputs["Value"], aov_out.inputs["Value"])

            # 确保材质输出连接到表面输出
            output_node = nodes.new('ShaderNodeOutputMaterial')
            emission_node = nodes.new('ShaderNodeEmission')
            links.new(math_length.outputs["Value"], emission_node.inputs["Strength"])
            links.new(emission_node.outputs["Emission"], output_node.inputs["Surface"])
            
        # 应用材质到所有物体
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and not obj.data.materials:
                obj.data.materials.append(bpy.data.materials["AOV_Distance"])


        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # 清空原有材质并添加 AOV 材质
                obj.data.materials.clear()
                obj.data.materials.append(bpy.data.materials["AOV_Distance"])

    else:  # EEVEE配置
        scene.eevee.taa_render_samples = 64
        scene.eevee.use_ssr = True
        scene.eevee.use_gtao = True
        vl.use_pass_mist = True  # 使用雾效近似距离
        if not scene.world:
            scene.world = bpy.data.worlds.new(name="World")
        if hasattr(scene.world, "mist_settings"):
            scene.world.mist_settings.use_mist = True
            scene.world.mist_settings.start = 0.1  # 雾效起始距离
            scene.world.mist_settings.depth = 5.0  # 雾效深度
            scene.world.mist_settings.falloff = 'LINEAR'  # 雾效衰减类型，可选 'LINEAR', 'QUADRATIC', 'INVERSE_QUADRATIC'
    
def render_cameras(cameras):
    scene = bpy.context.scene
    original_camera = scene.camera
    
    global output_base_path
    for cam in cameras:
        scene.camera = cam
        camera_folder = os.path.join(output_base_path, cam.name)
        current_camera_path = camera_folder + "/" + cam.name + "_" + engine_type + "_"
        os.makedirs(camera_folder, exist_ok=True)

        # 动态设置输出路径
        file_output_node = scene.node_tree.nodes.get("FileOutputNode")
        file_output_node.base_path = current_camera_path

        bpy.ops.render.render(animation=True)
        print(f"正在使用摄像机 {cam.name} 渲染到路径: {current_camera_path}")
        break

    scene.camera = original_camera

# 判断控制台是否已经打开，如果未打开则打开
if not bpy.app.debug_value:
    bpy.ops.wm.console_toggle()

# 执行主程序
clear_scene()
setup_scene()
cameras = add_cameras(4)

# 设置物体动画
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        set_animation(obj)

# 设置摄像机动画
for cam in cameras:
    set_animation(cam)

# 渲染设置
setup_render(engine = engine_type )

# 开始渲染
render_cameras(cameras)

print("所有渲染任务完成！")
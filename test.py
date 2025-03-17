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
        obj.pass_index = _ + 1  # 设置ID通道
        
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

# # 添加摄像机，从不同角度渲染，看向原点
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
        
        # 让摄像机看向原点
        direction = cam.location - Vector((0, 0, 0))
        cam.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
        
        # 设置摄像机的FOV
        cam.data.lens_unit = 'FOV'
        cam.data.angle = math.radians(fov)
        
        # # 启用运动路径显示
        # cam.display_type = 'WIRE'
        # cam.show_in_front = True

        # # 添加路径动画标记
        # bpy.ops.object.paths_calculate(start_frame=scene.frame_start, end_frame=scene.frame_end)

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

# def setup_render(engine='CYCLES'):
#     scene = bpy.context.scene
#     scene.render.engine = engine
#     scene.render.resolution_x = 960
#     scene.render.resolution_y = 540
#     scene.render.image_settings.file_format = 'OPEN_EXR'
#     scene.render.image_settings.color_depth = '32'
    
#     # 启用通道
#     vl = scene.view_layers[0]
#     vl.use_pass_z = True                    # 深度通道
#     vl.use_pass_object_index = True         # ID通道
    
#     # 引擎特定设置
#     if engine == 'CYCLES':
#         scene.cycles.samples = 16
#         scene.cycles.use_denoising = True
#     else:
#         scene.eevee.taa_render_samples = 64

# def render_cameras(cameras, frame_start=1, frame_end=20):
#     original_camera = bpy.context.scene.camera
#     scene = bpy.context.scene
    
#     # 设置渲染的帧范围
#     scene.frame_start = frame_start
#     scene.frame_end = frame_end
    
#     for cam in cameras:
#         scene.camera = cam
#         scene.render.filepath = f"//renders/{cam.name}/frame_"
#         print(f"Rendering with camera: {cam.name}")
#         bpy.ops.render.render(animation=True)
    
#     scene.camera = original_camera

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

# # 渲染设置
# setup_render(engine='CYCLES')  # 切换为'BLENDER_EEVEE'使用EEVEE

# # 开始渲染
# render_cameras(cameras)

# print("所有渲染任务完成！")
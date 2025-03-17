import bpy
import math
import random
from mathutils import Vector, Euler

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def setup_scene(size_x=5, size_y=5, size_z=4):
    primitives = ['primitive_cube_add', 'primitive_uv_sphere_add', 'primitive_cone_add', 'primitive_torus_add']
    for _ in range(5):
        pos = (random.uniform(-size_x * 0.5 , size_x * 0.5), random.uniform(-0.5 * size_y, size_y * 0.5), random.uniform(0, size_z))
        primitive = random.choice(primitives)
        getattr(bpy.ops.mesh, primitive)(location=pos)
        obj = bpy.context.object
        obj.pass_index = _ + 1  # 设置ID通道
        
    # 添加灯光
    bpy.ops.object.light_add(type='SUN', location=(0,0,10))
    bpy.context.object.data.energy = 5

# 添加摄像机，从不同角度渲染，看向原点
# TODO:可能需要调整摄像机看到的范围
def add_cameras(num=4, radius=15, height=8, fov=60):
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

def set_animation(obj, start=1, end=250, location_speed = 10):
    # 设置随机移动动画
    for frame in range(start, end+1, location_speed):
        obj.location += Vector((random.uniform(-1,1), 
                              random.uniform(-1,1),
                              random.uniform(-0.5,0.5)))
        obj.keyframe_insert("location", frame=frame)
        
    # 设置随机旋转动画
    if obj.type == 'CAMERA':
        for frame in range(start, end+1, 15):
            obj.rotation_euler = Euler((obj.rotation_euler.x + math.radians(random.uniform(-5,5)),
                                        obj.rotation_euler.y + math.radians(random.uniform(-5,5)),
                                        obj.rotation_euler.z + math.radians(random.uniform(-5,5))))
            obj.keyframe_insert("rotation_euler", frame=frame)

def setup_render(engine='CYCLES'):
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.render.image_settings.color_depth = '32'
    
    # 启用通道
    vl = scene.view_layers[0]
    vl.use_pass_z = True                    # 深度通道
    vl.use_pass_object_index = True         # ID通道
    
    # 引擎特定设置
    if engine == 'CYCLES':
        scene.cycles.samples = 16
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 64

def render_cameras(cameras, frame_start=1, frame_end=20):
    original_camera = bpy.context.scene.camera
    scene = bpy.context.scene
    
    # 设置渲染的帧范围
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    
    for cam in cameras:
        scene.camera = cam
        scene.render.filepath = f"//renders/{cam.name}/frame_"
        print(f"Rendering with camera: {cam.name}")
        bpy.ops.render.render(animation=True)
    
    scene.camera = original_camera

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
setup_render(engine='CYCLES')  # 切换为'BLENDER_EEVEE'使用EEVEE

# 开始渲染
render_cameras(cameras)

print("所有渲染任务完成！")
import bpy
import math
import random
from mathutils import Vector, Euler

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def setup_scene():
    # 添加随机物体
    primitives = ['cube', 'sphere', 'cone', 'torus']
    for _ in range(5):
        pos = (random.uniform(-5,5), random.uniform(-5,5), random.uniform(-5,5))
        bpy.ops.mesh.primitive_cube_add(location=pos)
        obj = bpy.context.object
        obj.1814 = _ + 1  # 设置ID通道+
        2031
        
    # 添加灯光
    bpy.ops.object.light_add(type='SUN', location=(0,0,10))
    bpy.context.object.data.energy = 5

# def add_cameras(num=4):
#     cameras = []
#     for i in range(num):
#         angle = math.radians(i * 360/num)
#         x = 10 * math.cos(angle)
#         y = 10 * math.sin(angle)
#         bpy.ops.object.camera_add(location=(x, y, 5))
#         cam = bpy.context.object
#         cam.rotation_mode = 'XYZ'
#         cameras.append(cam)
#     return cameras

# def set_animation(obj, start=1, end=250):
#     # 设置随机移动动画
#     for frame in range(start, end+1, 10):
#         obj.location += Vector((random.uniform(-1,1), 
#                               random.uniform(-1,1),
#                               random.uniform(-0.5,0.5)))
#         obj.keyframe_insert("location", frame=frame)
        
#     # 设置随机旋转动画
#     if obj.type == 'CAMERA':
#         for frame in range(start, end+1, 15):
#             obj.rotation_euler += Euler((math.radians(random.uniform(-5,5)),
#                                        math.radians(random.uniform(-5,5)),
#                                        math.radians(random.uniform(-5,5))))
#             obj.keyframe_insert("rotation_euler", frame=frame)

# def setup_render(engine='CYCLES'):
#     scene = bpy.context.scene
#     scene.render.engine = engine
#     scene.render.resolution_x = 1920
#     scene.render.resolution_y = 1080
#     scene.render.image_settings.file_format = 'OPEN_EXR'
#     scene.render.image_settings.color_depth = '32'
    
#     # 启用通道
#     vl = scene.view_layers[0]
#     vl.use_pass_z = True          # 深度通道
#     vl.use_pass_object_index = True  # ID通道
    
#     # 引擎特定设置
#     if engine == 'CYCLES':
#         scene.cycles.samples = 64
#         scene.cycles.use_denoising = True
#     else:
#         scene.eevee.taa_render_samples = 64

# def render_cameras(cameras):
#     original_camera = bpy.context.scene.camera
#     scene = bpy.context.scene
    
#     for cam in cameras:
#         scene.camera = cam
#         scene.render.filepath = f"//renders/{cam.name}/frame_"
#         print(f"Rendering with camera: {cam.name}")
#         bpy.ops.render.render(animation=True)
    
#     scene.camera = original_camera

# # 执行主程序
# clear_scene()
# setup_scene()
# cameras = add_cameras(4)

# # 设置物体动画
# for obj in bpy.data.objects:
#     if obj.type == 'MESH':
#         set_animation(obj)

# # 设置摄像机动画
# for cam in cameras:
#     set_animation(cam)

# # 渲染设置
# setup_render(engine='CYCLES')  # 切换为'BLENDER_EEVEE'使用EEVEE

# # 开始渲染
# render_cameras(cameras)

# print("所有渲染任务完成！")
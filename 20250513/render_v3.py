import bpy
import os
import random
import math
import mathutils
from mathutils import Vector, Matrix
import json
import time
import sys
from bpy_extras.object_utils import world_to_camera_view

# === 用户配置区 ===
INPUT_PLY_DIR = 'C:/Users/KZ/Softwares/Script/Bpy/多角度渲染/models'    # PLY 文件夹
OUTPUT_DIR = 'C:/Users/KZ/Softwares/Script/Bpy/多角度渲染/render'           # 渲染结果输出文件夹
HDRI_DIR = 'D:/data-beifen/3d软件/blender安装/2.82/scripts/addons/Extreme PBR Combo 2_8/Extreme PBR Risorse/HDRi/Photo studio.hdr'       # 可选 HDRI 环境贴图
NUM_VIEWS_PER_MODEL = 2               # 每个模型渲染视角数
IMAGE_SIZE = 1024                       # 渲染分辨率
CENTER_MODEL = True                     # 是否将模型居中处理
ADAPTIVE_CAMERA = True                  # 是否自动调整相机确保拍摄完整
CAMERA_FOV = 50                         # 相机视场角(度)，较小的值会有更窄的视角和更少的透视变形
CAMERA_MARGIN = 0.2                     # 模型与视图边界的边距比例(0.2表示保留20%的边距)
SAVE_CAMERA_PARAMS = True               # 是否保存相机参数
LOAD_CAMERA_PARAMS = False              # 是否加载已保存的相机参数
CAMERA_PARAMS_FILE = os.path.join(OUTPUT_DIR, 'camera_params.json')  # 相机参数文件路径
UNIFORM_CAMERA_DISTRIBUTION = True      # 是否使用均匀分布的相机位置(而不是完全随机)
USE_CAMERA_CONSTRAINTS = True           # 是否使用相机约束功能(锁定焦点)
TEETH_MODE = True                       # 牙列模式，如果为真，专门针对牙列模型优化相机角度

# === 场景初始化 ===
# 不清空场景，保留用户手动导入的网格对象
# bpy.ops.wm.read_homefile(use_empty=True)

# 创建输出目录结构
for sub in ['rgb', 'depth', 'normal', 'silhouette', 'caminfo','keypoints']:
    os.makedirs(os.path.join(OUTPUT_DIR, sub), exist_ok=True)

# 设置渲染参数
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.render.resolution_x = IMAGE_SIZE
scene.render.resolution_y = IMAGE_SIZE
scene.render.resolution_percentage = 100
scene.cycles.samples = 50

# 启用必要的 passes
view_layer = scene.view_layers[0]
view_layer.use_pass_normal = True  # 启用法线通道
view_layer.use_pass_z = True       # 启用深度通道

# 设置 Freestyle 边缘渲染 (Silhouette)
view_layer.use_freestyle = True
freestyle = view_layer.freestyle_settings
line_set = freestyle.linesets.new('LineSet')
line_set.select_silhouette = True
line_set.select_border = False
line_set.select_contour = False
line_set.select_crease = False

# === 渲染节点（用于 Depth & Normal） ===
scene.use_nodes = True
tree = scene.node_tree
for node in tree.nodes:
    tree.nodes.remove(node)

# 输入渲染层
rl = tree.nodes.new('CompositorNodeRLayers')
rl.location = (-300, 300)

# 打印所有可用的输出通道，辅助调试
print("可用的输出通道:")
for output in rl.outputs:
    print(f"- {output.name}")

# 添加一个函数来安全地连接节点，避免不存在的输出通道导致错误
def safe_link(outputs, output_names, input_socket):
    """尝试多个可能的输出名称，连接第一个存在的"""
    for name in output_names:
        if name in outputs:
            tree.links.new(outputs[name], input_socket)
            print(f"成功连接通道: {name}")
            return True
    return False

# Normal 输出
norm = tree.nodes.new('CompositorNodeOutputFile')
norm.label = 'Normal'
norm.base_path = os.path.join(OUTPUT_DIR, 'normal')
norm.file_slots[0].path = 'normal_'
norm.format.file_format = 'OPEN_EXR'
norm.format.color_mode = 'RGB'
# 尝试多个可能的法线通道名称
normal_success = safe_link(rl.outputs, ['Normal', 'Normal Pass', 'normalPass'], norm.inputs[0])
if not normal_success:
    print("警告: 无法找到法线通道，请检查 View Layer 设置")

# Depth 输出
depth = tree.nodes.new('CompositorNodeOutputFile')
depth.label = 'Depth'
depth.base_path = os.path.join(OUTPUT_DIR, 'depth')
depth.file_slots[0].path = 'depth_'
depth.format.file_format = 'OPEN_EXR'
# 尝试多个可能的深度通道名称
depth_success = safe_link(rl.outputs, ['Z', 'Depth', 'depthPass'], depth.inputs[0])
if not depth_success:
    print("警告: 无法找到深度通道，请检查 View Layer 设置")

# RGB 直接由渲染设置输出

# === 材质与照明准备 ===
# 环境光：随机 HDRI
if os.path.isdir(HDRI_DIR):
    hdri_files = [f for f in os.listdir(HDRI_DIR) if f.lower().endswith(('.hdr', '.exr'))]
    if hdri_files:
        # 确保世界存在
        if "World" not in bpy.data.worlds:
            world = bpy.data.worlds.new("World")
            scene.world = world
        else:
            world = bpy.data.worlds["World"]
            
        # 确保世界使用节点
        if not world.use_nodes:
            world.use_nodes = True
            
        # 创建或获取节点树
        node_tree = world.node_tree
        
        # 清理现有节点
        for node in node_tree.nodes:
            node_tree.nodes.remove(node)
            
        # 创建新节点
        env_tex = node_tree.nodes.new('ShaderNodeTexEnvironment')
        env_out = node_tree.nodes.new('ShaderNodeBackground')
        output = node_tree.nodes.new('ShaderNodeOutputWorld')
        
        # 选择随机 HDRI
        hdri_path = os.path.join(HDRI_DIR, random.choice(hdri_files))
        env_tex.image = bpy.data.images.load(hdri_path)
        
        # 连接节点
        node_tree.links.new(env_tex.outputs['Color'], env_out.inputs['Color'])
        node_tree.links.new(env_out.outputs['Background'], output.inputs['Surface'])

# 定义setup_camera_constraints函数
def setup_camera_constraints(cam_obj, scene):
    """设置相机约束，使相机始终朝向目标点"""
    if USE_CAMERA_CONSTRAINTS:
        # 创建一个空物体作为相机的目标点
        if 'CameraTarget' not in bpy.data.objects:
            target = bpy.data.objects.new('CameraTarget', None)
            scene.collection.objects.link(target)
            target.location = (0, 0, 0)  # 放在原点
        else:
            target = bpy.data.objects['CameraTarget']
        
        # 清除现有的所有约束
        for constraint in cam_obj.constraints:
            cam_obj.constraints.remove(constraint)
        
        # 添加跟踪约束，使相机始终朝向目标点
        track = cam_obj.constraints.new('TRACK_TO')
        track.target = target
        track.track_axis = 'TRACK_NEGATIVE_Z'  # 相机的-Z轴(朝前)指向目标
        track.up_axis = 'UP_Y'  # Y轴向上
        
        print("已添加相机跟踪约束，相机将始终朝向中心点")
        return target
    return None

# 创建相机
cam = bpy.data.objects.get('Camera') or bpy.data.cameras.new('Camera')
if isinstance(cam, bpy.types.Camera):
    cam_obj = bpy.data.objects.new('Camera', cam)
    scene.collection.objects.link(cam_obj)
else:
    cam_obj = cam
scene.camera = cam_obj

# 设置相机参数
cam_obj.data.lens_unit = 'FOV'
cam_obj.data.angle = math.radians(CAMERA_FOV)  # 设置FOV角度

# 设置相机约束
camera_target = setup_camera_constraints(cam_obj, scene)

# 随机光源（可选三点光）
def add_random_point_light():
    light_data = bpy.data.lights.new(name='PointLight', type='POINT')
    light = bpy.data.objects.new(name='PointLight', object_data=light_data)
    scene.collection.objects.link(light)
    light.location = (random.uniform(-1,1), random.uniform(-1,1), random.uniform(0.5,2))
    light.data.energy = random.uniform(500, 1500)

# === 批量渲染主循环 ===
# 尝试列出所有已启用的插件
try:
    print("已启用的插件:")
    for addon in bpy.context.preferences.addons.keys():
        print(f" - {addon}")
except Exception as e:
    print(f"获取插件列表时出错: {e}")

# 列出支持的导入格式
print("支持的导入格式:")
for op_name in dir(bpy.ops):
    if op_name.startswith('import_'):
        print(f" - {op_name}")

# 记录要处理的PLY文件列表
ply_files = [f for f in os.listdir(INPUT_PLY_DIR) if f.lower().endswith('.ply')]
print(f"找到 {len(ply_files)} 个PLY文件需要处理")

# 检查当前场景中已加载的对象
scene_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
print(f"场景中已有 {len(scene_objects)} 个网格对象")

# 添加检查模型是否在相机视野内的函数
def is_object_in_camera_view(scene, cam, obj, threshold=CAMERA_MARGIN):
    """
    检查物体是否在相机视野内
    
    参数:
        scene: 当前场景
        cam: 相机对象
        obj: 被检查的物体
        threshold: 边缘缓冲区大小(CAMERA_MARGIN表示边界内预留的边距)
    
    返回:
        完全在视野内返回True，否则返回False
    """
    # 获取相机矩阵
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cam_matrix = cam.matrix_world.normalized()
    
    # 获取物体的边界点
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    
    # 转换边界点到相机空间
    cam_matrix_inv = cam_matrix.inverted()
    corners_cam = [cam_matrix_inv @ corner for corner in corners]
    
    # 检查所有点是否在相机视锥体内
    min_x = min_y = 1.0
    max_x = max_y = -1.0
    
    # 相机设置
    render = scene.render
    res_x = render.resolution_x
    res_y = render.resolution_y
    scale = render.resolution_percentage / 100.0
    aspect = res_x * scale / (res_y * scale)
    
    # 相机参数
    if cam.data.type == 'PERSP':
        lens = cam.data.lens
        sensor_size = cam.data.sensor_width
        sensor_fit = cam.data.sensor_fit
        
        if sensor_fit == 'VERTICAL':
            sensor_size = cam.data.sensor_height
            aspect = 1 / aspect
        
        fov = 2 * math.atan(sensor_size / (2 * lens))
        
    elif cam.data.type == 'ORTHO':
        fov = 1.0
    
    # 检查各点是否在视野内
    for corner in corners_cam:
        # 转换到NDC空间
        if corner.z <= 0:  # 相机后方
            return False
            
        # 透视除法
        x = corner.x / corner.z
        y = corner.y / corner.z
        
        # 更新最大/最小坐标
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)
    
    # 检查坐标是否在范围内(加上阈值)
    if min_x < -1 + threshold or max_x > 1 - threshold or min_y < -1 + threshold or max_y > 1 - threshold:
        return False
    
    return True

# 加载相机参数
def load_camera_params(filepath, obj_name):
    """从JSON文件加载特定对象的相机参数"""
    if not os.path.exists(filepath):
        print(f"相机参数文件不存在: {filepath}")
        return None
    
    try:
        with open(filepath, 'r') as f:
            all_params = json.load(f)
        
        if obj_name in all_params:
            return all_params[obj_name]
        else:
            print(f"没有找到对象 {obj_name} 的相机参数")
            return None
    except Exception as e:
        print(f"加载相机参数失败: {e}")
        return None

# 保存相机参数
def save_camera_params(filepath, obj_name, camera_params):
    """将相机参数保存到JSON文件"""
    # 确保输出目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # 读取现有参数或创建新字典
    all_params = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                all_params = json.load(f)
        except:
            pass
    
    # 更新当前对象的参数
    all_params[obj_name] = camera_params
    
    # 保存到文件
    try:
        with open(filepath, 'w') as f:
            json.dump(all_params, f, indent=2)
        print(f"相机参数已保存: {filepath}")
    except Exception as e:
        print(f"保存相机参数失败: {e}")

def setup_viewlayer_override_with_emission():
    # 获取当前视图层
    view_layer = bpy.context.view_layer

    # 创建一个新的白色自发光材质
    mat_name = "White_Emission_Override"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 清空默认节点
        for node in nodes:
            nodes.remove(node)

        # 添加节点
        output_node = nodes.new(type="ShaderNodeOutputMaterial")
        emission_node = nodes.new(type="ShaderNodeEmission")
        emission_node.inputs[0].default_value = (1, 1, 1, 1)  # 白色
        emission_node.inputs[1].default_value = 1.0  # 强度

        # 连接发光到输出
        links.new(emission_node.outputs[0], output_node.inputs[0])
    else:
        mat = bpy.data.materials[mat_name]

    # 设置视图层材质覆盖
    view_layer.material_override = mat

    # 关闭 World 的 camera 可见性
    if bpy.context.scene.world is not None:
        bpy.context.scene.world.cycles_visibility.camera = False
    else:
        print("当前场景没有 World 设置，无法修改其可见性。")

    print("已设置白色自发光材质覆盖，并关闭 World 的摄像机可见性。")

# 备份设置
def backup_render_settings():
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    world = scene.world

    return {
        "material_override": view_layer.material_override,
        "world_visibility": world.cycles_visibility.camera if world else None
    }

# 恢复设置
def restore_render_settings(backup):
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    world = scene.world

    view_layer.material_override = backup.get("material_override")
    if world and backup.get("world_visibility") is not None:
        world.cycles_visibility.camera = backup["world_visibility"]

# 生成均匀分布在球面上的点
def generate_uniform_sphere_points(count):
    """
    生成均匀分布在球面上的点
    使用黄金螺旋算法生成均匀分布的点
    
    参数:
        count: 需要生成的点数量
        
    返回:
        包含(phi, theta)球坐标的列表
    """
    points = []
    phi = math.pi * (3.0 - math.sqrt(5.0))  # 黄金角
    
    for i in range(count):
        y = 1 - (i / float(count - 1)) * 2  # y从1到-1均匀分布
        radius = math.sqrt(1 - y * y)       # 半径
        
        theta = phi * i                     # 黄金角旋转
        
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        
        # 转换为球坐标(phi, theta)
        elevation = math.asin(y)            # 仰角
        azimuth = math.atan2(z, x)          # 方位角
        
        points.append((azimuth, elevation))

        # # 创建一个球体 mesh 并设置位置和缩放
        # pos = Vector((x, y, z)) * radius
        # bpy.ops.mesh.primitive_uv_sphere_add(radius=0.01, location=pos)

    return points

# 显示进度条函数
def show_progress(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    """
    命令行进度条
    
    参数:
        iteration   - 当前迭代 (Int)
        total       - 总迭代数 (Int)
        prefix      - 前缀字符串 (Str)
        suffix      - 后缀字符串 (Str)
        decimals    - 百分比的小数位数 (Int)
        length      - 进度条长度 (Int)
        fill        - 进度条填充字符 (Str)
        print_end   - 打印结束字符 (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    # 如果完成，打印换行符
    if iteration == total: 
        print()

def update_camera_target(target_obj, obj):
    """更新相机目标的位置"""
    if USE_CAMERA_CONSTRAINTS and target_obj:
        # 设置目标对象位置（如果模型不居中，则使用模型中心）
        target_point = (0, 0, 0) if CENTER_MODEL else obj.location
        target_obj.location = target_point
        
        # 更新场景以确保约束生效
        bpy.context.view_layer.update()

def export_camera_info(cam, filepath):
    """
    导出摄像机的基本参数信息到 txt 文件（包含约束影响的旋转）。
    
    参数:
        cam: 摄像机对象
        filepath: 保存的 txt 文件路径
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cam_eval = cam.evaluated_get(depsgraph)

    loc = cam_eval.location
    rot_world = cam_eval.matrix_world.to_euler()  # 世界空间旋转（带约束）
    data = cam_eval.data

    with open(filepath, 'w') as f:
        f.write("Camera Info:\n")
        f.write(f"Location: {loc.x:.6f}, {loc.y:.6f}, {loc.z:.6f}\n")
        f.write(f"Rotation (Euler XYZ, in degrees): {rot_world.x * 57.2958:.2f}, {rot_world.y * 57.2958:.2f}, {rot_world.z * 57.2958:.2f}\n")
        f.write(f"Shift X: {data.shift_x:.6f}\n")
        f.write(f"Shift Y: {data.shift_y:.6f}\n")
        f.write(f"Focal Angle: {data.lens:.2f} \n")

    print(f"摄像机信息已写入: {filepath}")

def export_visible_vertex_projection(obj, cam, txt_path,  point_radius=5, visibility_threshold=0.2, cleanup_prefix="temp_cube_"):
    """
    导出摄像机可见顶点的像素坐标和投影图像。

    参数:
        obj: 要处理的 Blender 对象
        cam: 摄像机对象
        txt_path: txt 文件保存路径
        img_path: PNG 图像保存路径
        point_radius: 在图像上绘制点的半径
        visibility_threshold: 可见性判断的距离阈值
    """
    scene = bpy.context.scene
    render = scene.render
    res_x = int(render.resolution_x * render.resolution_percentage / 100.0)
    res_y = int(render.resolution_y * render.resolution_percentage / 100.0)

    verts_world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    visible_points = []

    for i, v in enumerate(verts_world):
        co2D = world_to_camera_view(scene, cam, v)
        x, y, z = co2D
        
        # 可选：添加辅助立方体（用于调试）
        # bpy.ops.mesh.primitive_cube_add(size=0.02, location=v)
        # cube = bpy.context.active_object
        # cube.name = f"{cleanup_prefix}{i}"  # 给临时物体命名，方便后续删除

        
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and z >= 0.0:
            # 检查是否可见
            result, hit_loc, _, _, _, _ = scene.ray_cast(
                bpy.context.view_layer.depsgraph, cam.location, (v - cam.location).normalized()
            )
            if result and (v - hit_loc).length < visibility_threshold:
                px = round(x * res_x)
                py = round(y * res_y)
                visible_points.append((i, px, py))
    
    # 写入可见顶点坐标到 txt 文件
    with open(txt_path, 'w') as f:
        for idx, px, py in visible_points:
            f.write(f"{idx},{px},{py}\n")

    print(f"可见顶点数: {len(visible_points)}，已写入: {txt_path}")

    # 创建图像并绘制点
    # img = Image.new("RGB", (res_x, res_y), color=(255, 255, 255))
    # draw = ImageDraw.Draw(img)
    # for _, px, py in visible_points:
    #     py = int(res_y - py)  # y轴翻转
    #     draw.ellipse([(px - point_radius, py - point_radius),
    #                   (px + point_radius, py + point_radius)], fill=(0, 0, 0))

    # img.save(img_path)
    # print(f"已保存可见点投影图像到: {img_path}")
        # 清理临时立方体
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.name.startswith(cleanup_prefix):
            obj.select_set(True)
    bpy.ops.object.delete()

if len(scene_objects) > 0:
    # 使用场景中已有的对象
    print("使用场景中已有的对象进行渲染...")
    
    # 计算总渲染数量，用于显示进度
    total_renders = len(scene_objects) * NUM_VIEWS_PER_MODEL
    current_render = 0
    
    start_time = time.time()
    
    # 先隐藏所有对象，然后一个个处理
    for obj in scene_objects:
        obj.hide_render = True
        obj.hide_viewport = True
    
    for obj in scene_objects:
        print(f"处理对象: {obj.name}")
        
        # 显示当前要处理的对象
        obj.hide_render = False
        obj.hide_viewport = False
        
        # 计算模型的中心点
        local_bbox_center = sum((Vector(b) for b in obj.bound_box), Vector()) / 8
        global_bbox_center = obj.matrix_world @ local_bbox_center
        
        # 保存原始位置
        original_location = obj.location.copy()
        
        # 将模型临时移动到原点附近，确保能被正确渲染
        if CENTER_MODEL:
            print(f"将模型 {obj.name} 居中处理...")
            obj.location = (0, 0, 0)
        
        # 计算模型的边界框尺寸，用于确定合适的相机距离
        bound_box = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        max_dim = max([(max(p[i] for p in bound_box) - min(p[i] for p in bound_box)) for i in range(3)])
        
        # 使用模型尺寸计算最小安全距离，确保相机能拍摄到整个模型
        min_camera_distance = max_dim * 1.5  # 至少是模型最大尺寸的1.5倍
        
        # 随机材质或保持原贴图
        # TODO: 如需自定义 PBR，可在此添加材质节点。  
    
        # 尝试加载已保存的相机参数
        loaded_camera_params = None
        if LOAD_CAMERA_PARAMS:
            loaded_camera_params = load_camera_params(CAMERA_PARAMS_FILE, obj.name)
            if loaded_camera_params:
                print(f"已加载对象 {obj.name} 的相机参数")
        
        # 存储当前对象的相机参数
        camera_params = []
        
        # 预生成均匀分布的相机位置
        if UNIFORM_CAMERA_DISTRIBUTION and not loaded_camera_params:
            print("生成均匀分布的相机位置...")
            uniform_points = generate_uniform_sphere_points(NUM_VIEWS_PER_MODEL)
        else:
            uniform_points = None
    
        # 渲染多视角
        for i in range(NUM_VIEWS_PER_MODEL):
            view_start_time = time.time()
            
            # 计算并显示总体进度
            current_render += 1
            elapsed_time = time.time() - start_time
            avg_time_per_render = elapsed_time / current_render
            estimated_total_time = avg_time_per_render * total_renders
            remaining_time = estimated_total_time - elapsed_time
            
            progress_prefix = f"对象 {obj.name} ({scene_objects.index(obj)+1}/{len(scene_objects)})"
            progress_suffix = f"视角 {i+1}/{NUM_VIEWS_PER_MODEL} | 剩余时间: {remaining_time:.1f}秒"
            show_progress(current_render, total_renders, prefix=progress_prefix, suffix=progress_suffix)
            
            # 使用已加载的相机参数或生成新的参数
            if loaded_camera_params and i < len(loaded_camera_params):
                # 使用保存的相机参数
                params = loaded_camera_params[i]
                cam_obj.location = tuple(params['location'])
                cam_obj.rotation_euler = mathutils.Euler(params['rotation'])
                print(f"使用已保存的相机参数，视角 {i+1}/{NUM_VIEWS_PER_MODEL}")
                camera_position_found = True
            else:
                # 生成新的相机参数
                # 尝试找到一个合适的相机角度，确保模型在视野内
                attempts = 0
                max_attempts = 20  # 最多尝试次数
                camera_position_found = False
                
                while (not camera_position_found) and attempts < max_attempts and ADAPTIVE_CAMERA:
                    if UNIFORM_CAMERA_DISTRIBUTION and uniform_points:
                        # 使用预生成的均匀分布点
                        azimuth, elevation = uniform_points[i]
                        
                        # 针对牙列模型优化相机角度
                        if TEETH_MODE:
                            # 牙列模型通常需要更多从上方和侧面的视角
                            if random.random() < 0.7:  # 70%的概率偏向上方视角
                                elevation = random.uniform(0.1, 0.7)  # 更多从上方看的角度
                            else:
                                elevation = random.uniform(-0.3, 0.3)  # 其余从侧面看
                        else:
                            # 调整高度角范围，避免过高或过低
                            elevation = max(min(elevation, math.pi/4), -math.pi/4)
                        
                        # 随机调整距离
                        radius = random.uniform(min_camera_distance, min_camera_distance * 1.5)
                        
                        # 转换为笛卡尔坐标
                        x = radius * math.cos(elevation) * math.cos(azimuth)
                        y = radius * math.cos(elevation) * math.sin(azimuth)
                        z = radius * math.sin(elevation)
                        z = abs(z) + min_camera_distance * 0.3  # 确保高度总是有一定值
                    else:
                        # 完全随机生成
                        angle = random.uniform(0, 2*math.pi)
                        
                        # 针对牙列模型优化相机角度
                        if TEETH_MODE:
                            if random.random() < 0.7:  # 70%的概率偏向上方视角
                                elev = random.uniform(0.5, 1.0)  # 更多从上方看的角度
                            else:
                                elev = random.uniform(0.2, 0.5)  # 其余从侧面看
                        else:
                            elev = random.uniform(0.2, 1.0)
                        
                        radius = random.uniform(min_camera_distance, min_camera_distance * 2)
                        
                        x = radius * math.cos(angle)
                        y = radius * math.sin(angle)
                        z = elev * max_dim
                    
                    cam_obj.location = (x, y, z)
                    
                    # 如果不使用约束，手动设置相机朝向
                    if not USE_CAMERA_CONSTRAINTS:
                        # 让相机朝向原点(0,0,0)
                        direction = mathutils.Vector((0, 0, 0)) - cam_obj.location
                        rot_quat = direction.to_track_quat('-Z', 'Y')
                        cam_obj.rotation_euler = rot_quat.to_euler()
                    # 更新相机目标位置
                    update_camera_target(camera_target, obj)
                    
                    # 检查模型是否在相机视野内
                    if is_object_in_camera_view(scene, cam_obj, obj):
                        camera_position_found = True
                    else:
                        attempts += 1
                
                if not camera_position_found and ADAPTIVE_CAMERA:
                    print(f"警告: 无法找到合适的相机位置拍摄到完整模型 {obj.name}，使用最后一次尝试的位置")
                elif not ADAPTIVE_CAMERA:
                    # 如果不使用自适应相机，则直接设置随机角度
                    if UNIFORM_CAMERA_DISTRIBUTION and uniform_points:
                        azimuth, elevation = uniform_points[i]
                        
                        # 针对牙列模型优化相机角度
                        if TEETH_MODE:
                            if random.random() < 0.7:
                                elevation = random.uniform(0.1, 0.7)
                            else:
                                elevation = random.uniform(-0.3, 0.3)
                        else:
                            elevation = max(min(elevation, math.pi/4), -math.pi/4)
                            
                        radius = random.uniform(min_camera_distance, min_camera_distance * 1.5)
                        
                        x = radius * math.cos(elevation) * math.cos(azimuth)
                        y = radius * math.cos(elevation) * math.sin(azimuth)
                        z = radius * math.sin(elevation)
                        z = abs(z) + min_camera_distance * 0.3
                    else:
                        angle = random.uniform(0, 2*math.pi)
                        
                        # 针对牙列模型优化相机角度
                        if TEETH_MODE:
                            if random.random() < 0.7:
                                elev = random.uniform(0.5, 1.0)
                            else:
                                elev = random.uniform(0.2, 0.5)
                        else:
                            elev = random.uniform(0.2, 1.0)
                            
                        radius = random.uniform(min_camera_distance, min_camera_distance * 2)
                        
                        x = radius * math.cos(angle)
                        y = radius * math.sin(angle)
                        z = elev * max_dim
                    
                    cam_obj.location = (x, y, z)
            
            # 随机灯光
            add_random_point_light()
    
            # 渲染 RGB
            scene.render.filepath = os.path.join(OUTPUT_DIR, 'rgb', f"{obj.name}_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
            
            # 显示单个视角渲染时间
            view_time = time.time() - view_start_time
            print(f"\n完成视角渲染，耗时 {view_time:.2f}秒")
    
            scene.render.filepath = os.path.join(OUTPUT_DIR, 'silhouette', f"{obj.name}_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
    
            # 清理光源
            for obj_light in [o for o in scene.objects if o.type=='LIGHT' and o.name.startswith('PointLight')]:
                bpy.data.objects.remove(obj_light, do_unlink=True)
        
        # 恢复模型的原始位置
        if CENTER_MODEL:
            obj.location = original_location
        
        # 保存最终的相机参数
        if SAVE_CAMERA_PARAMS and camera_params:
            save_camera_params(CAMERA_PARAMS_FILE, obj.name, camera_params)
        
        # 处理完后，再次隐藏当前对象
        obj.hide_render = True
        obj.hide_viewport = True
    
    # 渲染完所有对象后，恢复它们的可见性
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = False
            obj.hide_viewport = False
else:
    # 如果场景中没有对象，则为每个PLY文件创建一个立方体
    # print("场景中没有现有对象，创建立方体替代...")
    
    # 计算总渲染数量，用于显示进度
    total_renders = len(ply_files) * NUM_VIEWS_PER_MODEL
    current_render = 0
    
    start_time = time.time()

    def import_single_ply(ply_dir, ply_file):
        full_path = os.path.join(ply_dir, ply_file)
        if not os.path.exists(full_path):
            print(f"文件不存在: {full_path}")
            return None
        
        # 遍历所有窗口和区域，寻找 VIEW_3D 区域
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            override = {
                                'window': window,
                                'screen': screen,
                                'area': area,
                                'region': region,
                            }
                            with bpy.context.temp_override(**override):
                                bpy.ops.wm.ply_import(filepath=full_path)

        obj = bpy.context.selected_objects[0]
        return obj
    def assign_bsdf_material_from_col(obj):
        """
        为对象创建并分配一个使用顶点颜色 'Col' 的 BSDF 材质。
        """
        if obj.type != 'MESH':
            print(f"{obj.name} 不是 Mesh 类型，跳过")
            return

        mesh = obj.data

        # 检查是否存在顶点颜色层
        if 'Col' not in mesh.color_attributes and 'Col' not in mesh.vertex_colors:
            print(f"{obj.name} 不包含 'Col' 顶点颜色")
            return

        # 创建材质
        mat = bpy.data.materials.new(name=f"{obj.name}_Mat")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 清除默认节点
        for node in nodes:
            nodes.remove(node)

        # 创建必要节点
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (300, 0)

        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf_node.location = (0, 0)

        color_node = nodes.new(type='ShaderNodeVertexColor')
        color_node.location = (-300, 0)
        color_node.layer_name = 'Col'

        # 连接节点
        links.new(color_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

        # 分配材质
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        print(f"已为 {obj.name} 创建并分配顶点色材质")

    for ply_file in ply_files:
        print(f"处理模型: {ply_file}")
        obj = import_single_ply(INPUT_PLY_DIR, ply_file)
        assign_bsdf_material_from_col(obj)
        
        # 创建立方体
        # print(f"创建立方体代替 {ply_file}...")
        
        # 记录当前场景中的对象数量
        # objects_before = set(bpy.data.objects)
        
        # 创建立方体
        # bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
        
        # 找到新创建的对象
        # objects_after = set(bpy.data.objects)
        # new_objects = objects_after - objects_before
        
        # if new_objects:
        #     obj = list(new_objects)[0]  # 获取新创建的对象
        #     obj.name = os.path.splitext(ply_file)[0]
        #     print(f"创建了对象: {obj.name}")
        # else:
        #     print("警告: 无法创建新对象")
        #     continue
        
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        bpy.ops.object.location_clear(clear_delta=False)
        
        # 获取立方体尺寸作为基准距离
        bound_box = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        max_dim = max([(max(p[i] for p in bound_box) - min(p[i] for p in bound_box)) for i in range(3)])
        min_camera_distance = max_dim * 1.5  # 至少是模型最大尺寸的1.5倍
        
        # 尝试加载已保存的相机参数
        loaded_camera_params = None
        if LOAD_CAMERA_PARAMS:
            loaded_camera_params = load_camera_params(CAMERA_PARAMS_FILE, obj.name)
            if loaded_camera_params:
                print(f"已加载对象 {obj.name} 的相机参数")
        
        # 存储当前对象的相机参数
        camera_params = []
        
        # 预生成均匀分布的相机位置
        if UNIFORM_CAMERA_DISTRIBUTION and not loaded_camera_params:
            print("生成均匀分布的相机位置...")
            uniform_points = generate_uniform_sphere_points(NUM_VIEWS_PER_MODEL)
        else:
            uniform_points = None
    
        # 渲染多视角
        for i in range(NUM_VIEWS_PER_MODEL):
            view_start_time = time.time()
            
            # 计算并显示总体进度
            current_render += 1
            elapsed_time = time.time() - start_time
            avg_time_per_render = elapsed_time / current_render
            estimated_total_time = avg_time_per_render * total_renders
            remaining_time = estimated_total_time - elapsed_time
            
            progress_prefix = f"模型 {ply_file} ({ply_files.index(ply_file)+1}/{len(ply_files)})"
            progress_suffix = f"视角 {i+1}/{NUM_VIEWS_PER_MODEL} | 剩余时间: {remaining_time:.1f}秒"
            show_progress(current_render, total_renders, prefix=progress_prefix, suffix=progress_suffix)
            
            # 使用已加载的相机参数或生成新的参数
            if loaded_camera_params and i < len(loaded_camera_params):
                # 使用保存的相机参数
                params = loaded_camera_params[i]
                cam_obj.location = tuple(params['location'])
                cam_obj.rotation_euler = mathutils.Euler(params['rotation'])
                print(f"使用已保存的相机参数，视角 {i+1}/{NUM_VIEWS_PER_MODEL}")
                camera_position_found = True
            else:
                # 生成新的相机参数
                # 尝试找到一个合适的相机角度，确保模型在视野内
                attempts = 0
                max_attempts = 20  # 最多尝试次数
                camera_position_found = False
                
                while (not camera_position_found) and attempts < max_attempts and ADAPTIVE_CAMERA:
                    if UNIFORM_CAMERA_DISTRIBUTION and uniform_points:
                        # 使用预生成的均匀分布点
                        azimuth, elevation = uniform_points[i]
                        
                        # 针对牙列模型优化相机角度
#                        if TEETH_MODE:
#                            # 牙列模型通常需要更多从上方和侧面的视角
#                            if random.random() < 0.7:  # 70%的概率偏向上方视角
#                                elevation = random.uniform(0.1, 0.7)  # 更多从上方看的角度
#                            else:
#                                elevation = random.uniform(-0.3, 0.3)  # 其余从侧面看
#                        else:
#                            # 调整高度角范围，避免过高或过低
#                            elevation = max(min(elevation, math.pi/4), -math.pi/4)
#                        
                        # 随机调整距离
                        radius = random.uniform(min_camera_distance, min_camera_distance * 1.5)
                        # 转换为笛卡尔坐标
                        x = radius * math.cos(elevation) * math.cos(azimuth)
                        y = radius * math.cos(elevation) * math.sin(azimuth)
                        z = radius * math.sin(elevation)
                        z = abs(z) + min_camera_distance * 0.3  # 确保高度总是有一定值

                        position = Vector((x, y, z))
                        # 创建绕 Y 轴旋转 90° 的旋转矩阵
                        angle_rad = math.radians(90)
                        rotation_matrix = Matrix.Rotation(angle_rad, 4, 'Y')  # 4x4 旋转矩阵
                        # 执行旋转
                        rotated_position = rotation_matrix @ position
                        (x, y, z) = rotated_position
                        
                    else:
                        # 完全随机生成
                        angle = random.uniform(0, 2*math.pi)
                        
                        # 针对牙列模型优化相机角度
                        if TEETH_MODE:
                            if random.random() < 0.7:  # 70%的概率偏向上方视角
                                elev = random.uniform(0.5, 1.0)  # 更多从上方看的角度
                            else:
                                elev = random.uniform(0.2, 0.5)  # 其余从侧面看
                        else:
                            elev = random.uniform(0.2, 1.0)
                        
                        radius = random.uniform(min_camera_distance, min_camera_distance * 2)
                        
                        x = radius * math.cos(angle)
                        y = radius * math.sin(angle)
                        z = elev * max_dim
                    
                    cam_obj.location = (x, y, z)

                    # 如果不使用约束，手动设置相机朝向
                    if not USE_CAMERA_CONSTRAINTS:
                        # 让相机朝向原点(0,0,0)
                        direction = mathutils.Vector((0, 0, 0)) - cam_obj.location
                        rot_quat = direction.to_track_quat('-Z', 'Y')
                        cam_obj.rotation_euler = rot_quat.to_euler()
                    # 更新相机目标位置
                    update_camera_target(camera_target, obj)
                    
                    # 检查模型是否在相机视野内
                    if is_object_in_camera_view(scene, cam_obj, obj):
                        camera_position_found = True
                    else:
                        attempts += 1
                
                if not camera_position_found and ADAPTIVE_CAMERA:
                    print(f"警告: 无法找到合适的相机位置拍摄到完整模型 {obj.name}，使用最后一次尝试的位置")
                elif not ADAPTIVE_CAMERA:
                    # 如果不使用自适应相机，则直接设置随机角度
                    if UNIFORM_CAMERA_DISTRIBUTION and uniform_points:
                        azimuth, elevation = uniform_points[i]
                        
                        # 针对牙列模型优化相机角度
                        if TEETH_MODE:
                            if random.random() < 0.7:
                                elevation = random.uniform(0.1, 0.7)
                            else:
                                elevation = random.uniform(-0.3, 0.3)
                        else:
                            elevation = max(min(elevation, math.pi/4), -math.pi/4)
                            
                        radius = random.uniform(min_camera_distance, min_camera_distance * 1.5)
                        
                        x = radius * math.cos(elevation) * math.cos(azimuth)
                        y = radius * math.cos(elevation) * math.sin(azimuth)
                        z = radius * math.sin(elevation)
                        z = abs(z) + min_camera_distance * 0.3
                    else:
                        angle = random.uniform(0, 2*math.pi)
                        
                        # 针对牙列模型优化相机角度
                        if TEETH_MODE:
                            if random.random() < 0.7:
                                elev = random.uniform(0.5, 1.0)
                            else:
                                elev = random.uniform(0.2, 0.5)
                        else:
                            elev = random.uniform(0.2, 1.0)
                            
                        radius = random.uniform(min_camera_distance, min_camera_distance * 2)
                        
                        x = radius * math.cos(angle)
                        y = radius * math.sin(angle)
                        z = elev * max_dim
                    
                    cam_obj.location = (x, y, z)

            # 创建一个球体 mesh 并设置位置和缩放
#            pos = Vector((x, y, z)) 
#            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.01, location=pos)
            # 随机灯光
            add_random_point_light()
    
            # 渲染 RGB
            scene.render.filepath = os.path.join(OUTPUT_DIR, 'rgb', f"{os.path.splitext(ply_file)[0]}_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
            
            # 显示单个视角渲染时间
            view_time = time.time() - view_start_time
            print(f"\n完成视角渲染，耗时 {view_time:.2f}秒")
    
            # 渲染遮罩
            # 备份设置
            backup = backup_render_settings()
            setup_viewlayer_override_with_emission()
            scene.render.filepath = os.path.join(OUTPUT_DIR, 'silhouette', f"{os.path.splitext(ply_file)[0]}_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
            restore_render_settings(backup)

            # 清理光源
            for obj_light in [o for o in scene.objects if o.type=='LIGHT' and o.name.startswith('PointLight')]:
                bpy.data.objects.remove(obj_light, do_unlink=True)

            cam_info_path = os.path.join(OUTPUT_DIR, 'caminfo', f"{os.path.splitext(ply_file)[0]}_{i:03d}.txt")
            export_camera_info(cam_obj, cam_info_path)

            # 导出摄像机可见顶点的像素坐标
            txt_output = os.path.join(OUTPUT_DIR, 'keypoints', f"{os.path.splitext(ply_file)[0]}_{i:03d}.txt")
            export_visible_vertex_projection(obj, cam_obj, txt_output)

        # 保存最终的相机参数
        if SAVE_CAMERA_PARAMS and camera_params:
            save_camera_params(CAMERA_PARAMS_FILE, obj.name, camera_params)

        # 删除模型，准备下一个
        bpy.data.objects.remove(obj, do_unlink=True)

print('渲染完成！')
# 显示总渲染时间
total_time = time.time() - start_time
print(f"总渲染时间: {total_time:.2f}秒，平均每个视角: {total_time/current_render:.2f}秒")

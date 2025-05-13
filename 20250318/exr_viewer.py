# 本脚本用于提取EXR文件的元数据信息

# EXR头信息包含摄像机参数：
{
    'CameraLocation': 'Vector(x,y,z)', 
    'CameraRotation': 'Euler(x,y,z)',
    'FocalLength': '焦距(mm)'
}

import OpenEXR
import Imath

file = OpenEXR.InputFile("render.exr")
header = file.header()
channels = header['channels']
print("Available channels:", channels.keys())

# 读取摄像机元数据
print("Camera Location:", header['CameraLocation'])
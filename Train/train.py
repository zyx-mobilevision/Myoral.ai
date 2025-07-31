from ultralytics import YOLO
import torch
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 检查GPU可用性
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"使用设备: {device}")

# 加载预训练模型
model = YOLO('yolov8x-seg.pt')  # 使用x-large模型，对医学图像更有效

# 训练配置
results = model.train(
    data='Training/data.yaml',
    epochs=10,
    batch=8,  # 根据GPU内存调整
    imgsz=640,
    device=device,
    name='oral_segmentation_v1',
    optimizer='AdamW',
    lr0=1e-4,
    weight_decay=0.05,
    augment=True,
    save_period=20,
    pretrained=True,
    overlap_mask=True,  # 允许mask重叠
    box=7.5,  # 调整box损失权重
    cls=0.5,  # 调整分类损失权重
    dfl=1.5,  # 调整dfl损失权重
    close_mosaic=10,  # 最后10个epoch关闭mosaic增强
    degrees=15.0,  # 旋转角度范围
    translate=0.1,  # 平移增强
    scale=0.5,  # 缩放增强
    shear=0.1,  # 剪切增强
    perspective=0.0005,  # 透视变换
    flipud=0.1,  # 上下翻转概率
    fliplr=0.5,  # 左右翻转概率
    mosaic=1.0,  # mosaic数据增强概率
    mixup=0.1,  # mixup增强概率
    copy_paste=0.1,  # copy-paste增强概率
    hsv_h=0.015,  # 色调增强
    hsv_s=0.7,  # 饱和度增强
    hsv_v=0.4,  # 明度增强
)

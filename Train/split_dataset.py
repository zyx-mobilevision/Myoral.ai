import os
import random
from sklearn.model_selection import train_test_split

# 设置随机种子

random.seed(42)

# 获取所有图像文件
image_dir = "Training/job_10_dataset_2025_06_25_08_46_12_ultralytics yolo segmentation 1.0/images/Train"
all_images = [f for f in os.listdir(image_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]

# 分割数据集 (80%训练, 20%验证)
train_images, val_images = train_test_split(all_images, test_size=0.2, random_state=42)


# 写入Train.txt和Val.txt
def write_file_list(filepath, images):
    with open(filepath, 'w') as f:
        for img in images:
            f.write(f"data/images/Train/{img}\n")

write_file_list("Training/Train.txt", train_images)
write_file_list("Training/Val.txt", val_images)
print(f"数据集分割完成: {len(train_images)}训练, {len(val_images)}验证")

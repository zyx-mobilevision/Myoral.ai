import os
import cv2
import albumentations as A
import numpy as np
from tqdm import tqdm
from collections import defaultdict
import random

# 类别ID与增强策略
class_specific_transforms = {
    1: A.Compose([
        A.RandomResizedCrop(size=(512, 512), scale=(0.4, 1.0), ratio=(0.75, 1.33), p=0.7),
        A.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.02, p=0.7),
        A.RandomGamma(gamma_limit=(80, 120), p=0.7)
    ]),
    2: A.Compose([
        A.RGBShift(r_shift_limit=20, g_shift_limit=10, b_shift_limit=10, p=0.7),
        A.Blur(blur_limit=3, p=0.5)
    ]),
    5: A.Compose([
        A.ElasticTransform(alpha=1, sigma=20, p=0.7),
        A.GridDistortion(p=0.5)
    ])
}
base_transform = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.Rotate(limit=15, p=0.7),
    A.RandomBrightnessContrast(p=0.3),
    A.CLAHE(p=0.5),
    A.GaussNoise(p=0.2)
])

img_dir = "Training/data/images/Train"
label_dir = "Training/data/labels/Train"
aug_img_dir = "Training/data/images/aug"
aug_label_dir = "Training/data/labels/aug"
os.makedirs(aug_img_dir, exist_ok=True)
os.makedirs(aug_label_dir, exist_ok=True)

# 统计每类数量（只统计原始标签）
class_counts = defaultdict(int)
for label_file in os.listdir(label_dir):
    if not label_file.endswith(".txt"):
        continue
    with open(os.path.join(label_dir, label_file)) as f:
        for line in f:
            class_id = int(line.split()[0])
            class_counts[class_id] += 1

# 设定目标数量（最大少数类数量）
minority_max = max([v for k, v in class_counts.items() if k not in [0, 3]])
target_per_class = minority_max

# 记录每类已增强数量
aug_counts = defaultdict(int)

for label_file in tqdm(os.listdir(label_dir)):
    if not label_file.endswith(".txt"):
        continue
    label_path = os.path.join(label_dir, label_file)
    img_path = os.path.join(img_dir, label_file.replace(".txt", ".jpg"))
    if not os.path.exists(img_path):
        img_path = img_path.replace(".jpg", ".png")
        if not os.path.exists(img_path):
            continue
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    masks = []
    class_ids = []
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            class_id = int(parts[0])
            points = np.array(parts[1:], dtype=np.float32).reshape(-1, 2)
            points = (points * [w, h]).astype(np.int32)
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask, [points], 1)
            masks.append(mask)
            class_ids.append(class_id)
    # 对每个类别分别处理
    for cls in set(class_ids):
        if cls in [0, 3]:
            # tooth和mouth只保留原始样本，不增强
            if aug_counts[cls] < target_per_class:
                aug_img_name = f"{label_file.replace('.txt','')}_cls{cls}.jpg"
                aug_label_name = f"{label_file.replace('.txt','')}_cls{cls}.txt"
                cv2.imwrite(os.path.join(aug_img_dir, aug_img_name), img)
                with open(os.path.join(aug_label_dir, aug_label_name), "w") as f_out:
                    with open(label_path) as f_in:
                        f_out.write(f_in.read())
                aug_counts[cls] += 1
        else:
            # 其余类别增强，直到数量达到target_per_class
            n_aug = min(10, target_per_class - aug_counts[cls])
            for i in range(n_aug):
                if cls in class_specific_transforms:
                    aug = class_specific_transforms[cls](image=img, masks=masks)
                else:
                    aug = base_transform(image=img, masks=masks)
                aug_img = aug['image']
                aug_masks = aug['masks']
                aug_img_name = f"{label_file.replace('.txt','')}_cls{cls}_aug{i}.jpg"
                aug_label_name = f"{label_file.replace('.txt','')}_cls{cls}_aug{i}.txt"
                cv2.imwrite(os.path.join(aug_img_dir, aug_img_name), aug_img)
                with open(os.path.join(aug_label_dir, aug_label_name), "w") as f_out:
                    for idx, mask in enumerate(aug_masks):
                        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        for cnt in contours:
                            if len(cnt) < 3:
                                continue
                            norm_points = cnt.squeeze().astype(np.float32)
                            norm_points[:, 0] /= w
                            norm_points[:, 1] /= h
                            norm_points = norm_points.flatten()
                            norm_points = np.clip(norm_points, 0, 1)
                            f_out.write(f"{class_ids[idx]} " + " ".join(map(str, norm_points)) + "\n")
                aug_counts[cls] += 1
                if aug_counts[cls] >= target_per_class:
                    break
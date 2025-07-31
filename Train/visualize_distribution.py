import os
from collections import defaultdict
import matplotlib.pyplot as plt

# 标签路径
label_dir = "Training/data/labels/aug"  # 使用增强后的标签目录

# 统计类别数量
class_counts = defaultdict(int)
for label_file in os.listdir(label_dir):
    if label_file.endswith(".txt"):
        with open(os.path.join(label_dir, label_file)) as f:
            for line in f:
                class_id = int(line.split()[0])
                class_counts[class_id] += 1

# 类别名称（请根据你的实际类别顺序修改）
classes = [
    "Tooth", "Caries", "Gum Inflammation", "Mouth", "Gum",
    "Recession", "Orthodontics", "Mucosa", "Splint"
]
counts = [class_counts[i] for i in range(len(classes))]

# 可视化
plt.figure(figsize=(12, 6))
plt.bar(classes, counts, color='skyblue')
plt.title("Class Distribution in Dataset")
plt.xlabel("Class")
plt.ylabel("Count")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("Training/class_distribution_aug.png")  # 新增：保存图片
plt.show()
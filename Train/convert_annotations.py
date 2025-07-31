import os
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

src_root = 'data_annotation'
dst_label_dir = 'dataset/labels'
os.makedirs(dst_label_dir, exist_ok=True)

# 收集所有tooth number
tooth_numbers = set()

def extract_tooth_numbers(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for obj in root.findall('.//polygon'):
        label = obj.get('label')
        if label != "Tooth":
            continue
        for attr in obj.findall('attribute'):
            if attr.get('name') == "Tooth Number" and attr.text and attr.text.strip():
                tooth_numbers.add(attr.text.strip())

# 第一步：收集所有tooth number
for root, dirs, files in os.walk(src_root):
    for file in files:
        if file == 'annotations.xml':
            xml_path = os.path.join(root, file)
            extract_tooth_numbers(xml_path)

# 构建类别映射
tooth_number_list = sorted(tooth_numbers, key=lambda x: int(x))
class_map = {num: idx for idx, num in enumerate(tooth_number_list)}

def convert_cvat_xml_to_yolo(xml_path, img_file, img_width, img_height, output_txt, class_map):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    found = False
    with open(output_txt, 'w') as f:
        for obj in root.findall('.//polygon'):
            label = obj.get('label')
            if label != "Tooth":
                continue
            tooth_number = None
            for attr in obj.findall('attribute'):
                if attr.get('name') == "Tooth Number" and attr.text and attr.text.strip():
                    tooth_number = attr.text.strip()
                    break
            if tooth_number is None or tooth_number not in class_map:
                continue
            class_id = class_map[tooth_number]
            points = obj.get('points').split(';')
            normalized_points = []
            for point in points:
                x, y = map(float, point.split(','))
                normalized_points.extend([x / img_width, y / img_height])
            # YOLO分割格式: class_id x1 y1 x2 y2 ... xn yn
            line = f"{class_id} " + " ".join(map(str, normalized_points))
            f.write(line + '\n')
            found = True
    return found

# 第二步：递归转换标注
for root, dirs, files in os.walk(src_root):
    xml_path = os.path.join(root, 'annotations.xml')
    if not os.path.exists(xml_path):
        continue
    image_dir = os.path.join(root, 'images')
    img_files = []
    if os.path.exists(image_dir):
        for dirpath, _, filenames in os.walk(image_dir):
            for img_file in filenames:
                if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_files.append(os.path.join(dirpath, img_file))
    else:
        img_files = [os.path.join(root, f) for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    for img_path in img_files:
        img_file = os.path.basename(img_path)
        rel_dir = os.path.relpath(os.path.dirname(img_path), src_root).replace(os.sep, '_')
        dst_label = os.path.join(dst_label_dir, f"{rel_dir}_{Path(img_file).stem}.txt")
        has_ann = False
        tree = ET.parse(xml_path)
        root_xml = tree.getroot()
        img_elem = root_xml.find(f".//image[@name='{img_file}']")
        if img_elem is not None:
            img_width = int(img_elem.get('width'))
            img_height = int(img_elem.get('height'))
            tmp_root = ET.Element('annotations')
            tmp_img = ET.SubElement(tmp_root, 'image', attrib=img_elem.attrib)
            for poly in img_elem.findall('polygon'):
                tmp_img.append(poly)
            tmp_tree = ET.ElementTree(tmp_root)
            tmp_xml = f"{dst_label}.tmp.xml"
            tmp_tree.write(tmp_xml)
            has_ann = convert_cvat_xml_to_yolo(tmp_xml, img_file, img_width, img_height, dst_label, class_map)
            os.remove(tmp_xml)
        if not has_ann:
            open(dst_label, 'w').close()  # 空标签

# 生成dataset.yaml
dataset_yaml = {
    'path': os.path.abspath('dataset'),
    'train': 'images',
    'val': 'images',
    'names': [f"tooth_{num}" for num in tooth_number_list]
}
with open('dataset.yaml', 'w') as f:
    yaml.dump(dataset_yaml, f, allow_unicode=True)
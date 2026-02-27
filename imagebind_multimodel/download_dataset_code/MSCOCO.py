"""
从网站 https://cocodataset.org/#download 下载对应的训练集的图片和注释数据   11万张图片 每张图片对应5个文本描述
按照这种列表字典的形式进行保存对应关系
data = {
    "image_id": image_id,
    "image_base64": base64_code,
    "captions": captions,
    }
data_list.append(data)
"""
import base64
import os
import requests
import zipfile
import json
from tqdm import tqdm
import torch

def deal_MSCOCO(save_path):
    # 解析 captions 注释文件，提取每张图片对应的 caption 文本
    annotations_file = os.path.join(save_path, "MSCOCO_origin", "annotations", "captions_train2017.json")
    image_file = os.path.join(save_path, "MSCOCO_origin", "train2017")
    with open(annotations_file, 'r', encoding='utf-8') as f:
        captions_data = json.load(f)

    # 建立从 image_id 到 captions 的映射 11万张图片 每张图片对应5个文本描述
    image_to_captions = {}
    for ann in tqdm(captions_data['annotations']):
        image_id = ann['image_id']
        caption = ann['caption']
        image_to_captions.setdefault(image_id, []).append(caption)

    # 保存每张图片对应的 captions 到文本文件中（文件名与图片文件名对应，不包含扩展名）
    output_dir = os.path.join(save_path, "MSCOCO_classified")
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "img_text.json")
    with open(output_file, 'w+', encoding='utf-8') as f:
        for img in tqdm(captions_data['images']):
            image_id = img['id'] # 391895
            file_name = img['file_name']  # "000000391895.jpg"
            captions = image_to_captions.get(image_id, []) # 在对应映射里面找到图片id对应的5个文本描述

            data = {
                    "image_id": image_id,
                    "image_file_name": file_name,
                    "text": captions,
            }
            f.write(json.dumps(data) + "\n")

    print("MSCOCO end")


if __name__ == '__main__':
    save_path = "../dataset"
    os.makedirs(save_path, exist_ok=True)

    deal_MSCOCO(save_path)

# image_path = os.path.join(image_file, file_name)
# with open(image_path, 'rb') as f:
#     image_data = f.read()
# base64_code = base64.b64encode(image_data).decode('utf-8')
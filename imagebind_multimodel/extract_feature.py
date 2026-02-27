"""
读取
"""
import torch
import json
import librosa
import os
from tqdm import tqdm
from pyexpat import features

from imagebind import data
from imagebind.models import imagebind_model
from imagebind.models.imagebind_model import ModalityType
import torch.nn.functional as F


device = "cuda" if torch.cuda.is_available() else "cpu"
model = imagebind_model.imagebind_huge(pretrained=True)
model.eval()
model.to(device)

def extract_image_text_feature(save_path):
    image_text_path = os.path.join(save_path, "MSCOCO_classified", "img_text.json")
    image_text_feature_list = []
    image_text_feature_path = os.path.join(save_path,  "img_text_feature")
    idx= 0
    with open(image_text_path, "r") as image_text_file:
        # 每行读取获取对应的内容 {"image_id": 391895, "image_file_name": "000000391895.jpg", "text": ["A man with a red helmet on a small mop, 用torch来保存，用json的话一行一行读太慢了
        for line in tqdm(image_text_file):
            idx+=1
            line_data = json.loads(line)
            image_id = line_data["image_id"]
            image_file_name = line_data["image_file_name"]
            text = line_data["text"]

            image_file_path = os.path.join(save_path, "MSCOCO_origin", "train2017", image_file_name)

            input_image_text = {
                ModalityType.TEXT: data.load_and_transform_text(text, device),
                ModalityType.VISION: data.load_and_transform_vision_data([image_file_path], device),
            }

            with torch.no_grad():
                feature = model(input_image_text)

            image_text_feature = {
                "image_id": image_id,
                "image_file_name": image_file_name,
                "text": text,
                "image_feature": feature[ModalityType.VISION].cpu().numpy().tolist(),
                "text_feature": feature[ModalityType.TEXT].cpu().numpy().tolist(),
            }
            image_text_feature_list.append(image_text_feature)
            if idx % 4000 ==0:
                torch.save(image_text_feature_list, image_text_feature_path)
    torch.save(image_text_feature_list, image_text_feature_path)


def extract_audio_feature(save_path):
    audio_path = os.path.join(save_path, "ESC-50_classified", "class_label.json")
    audio_feature_path = os.path.join(save_path, "audio_feature")
    audio_feature_list = []
    with open(audio_path, "r") as audio_file:
        for line in tqdm(audio_file):
            line_data = json.loads(line)
            audio_file_name = line_data["audio_file_name"]
            audio_class_label = line_data["audio_class_label"]
            audio_id = line_data["audio_id"]

            audio_file_path = os.path.join(save_path, "ESC-50_classified", f"{audio_class_label}", f"{audio_id}.wav")

            input_text_audio = {
                ModalityType.TEXT: data.load_and_transform_text([audio_class_label], device),
                ModalityType.AUDIO: data.load_and_transform_audio_data([audio_file_path], device),
            }

            with torch.no_grad():
                feature = model(input_text_audio)

            audio_feature = {
                "audio_file_name": audio_file_name,
                "audio_class_label": audio_class_label,
                "audio_id": audio_id,
                "audio_feature": feature[ModalityType.AUDIO].cpu().numpy().tolist(),
                "text_feature": feature[ModalityType.TEXT].cpu().numpy().tolist(),
            }
            audio_feature_list.append(audio_feature)
    torch.save(audio_feature_list, audio_feature_path)

if __name__ == '__main__':
    save_path = "dataset"
    os.makedirs(save_path, exist_ok=True)

    # extract_audio_feature(save_path)
    extract_image_text_feature(save_path)

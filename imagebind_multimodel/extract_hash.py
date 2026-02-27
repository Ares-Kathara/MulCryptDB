import torch
from utils import ImageMlp, TextMlp, AudioMlp
import os
from tqdm import tqdm
import json
import numpy as np
from torch.utils.data.dataset import Dataset
from torch.utils.data import DataLoader
import time

feature_len = 1024
hash_len = 32
epoch = 100


def extract_hash():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    # 提前生成好的img text feature pair
    image_text_feature_path = f"dataset/img_text_feature"
    audio_text_feature_path = f"dataset/audio_feature"
    assert os.path.exists(image_text_feature_path), f"{image_text_feature_path} not exists"
    assert os.path.exists(audio_text_feature_path), f"{audio_text_feature_path} not exists"
    print(f"feat path : {image_text_feature_path}")
    print(f"feat path : {audio_text_feature_path}")

    audio_text_feature = torch.load(audio_text_feature_path)
    image_text_feature = torch.load(image_text_feature_path)
    print("load feature successfully")

    # 导入先前训练好的MLP model
    img_model = ImageMlp(feature_len, hash_len).to(device)
    text_model = TextMlp(feature_len, hash_len).to(device)
    audio_model = AudioMlp(feature_len, hash_len).to(device)

    file_name =  'hash_' + str(hash_len) + f"_epoch_{epoch}" + ".pt"
    model_state_path = f'hash_model_save'
    model_state_path = os.path.join(model_state_path, file_name)
    state = torch.load(model_state_path)
    img_model.load_state_dict(state['ImageMlp'])
    text_model.load_state_dict(state['TextMlp'])
    audio_model.load_state_dict(state['AudioMlp'])

    img_model.eval()
    text_model.eval()
    audio_model.eval()

    image_text_list, audio_data_list = [], []

    for item in tqdm(image_text_feature):
        # [ {"image_id": 391895, "image_file_name": "000000391895.jpg", "text": ["A man ide."], "image_feature": [[ feature]] "text_feature": [[feature, feature]] ````]
        image_id = item['image_id']
        image_file_name = item['image_file_name']
        text = item['text']
        image_feature = torch.tensor(item['image_feature'][0], dtype=torch.float32).to(device).unsqueeze(dim=0)
        text_feature = torch.tensor(item['text_feature'][0], dtype=torch.float32).to(device).unsqueeze(dim=0)

        output = img_model(image_feature)
        binary_hash = (output >= 0.0).float()
        binary_hash = binary_hash.squeeze().cpu().numpy()
        img_binary_str = ''.join(str(int(data)) for data in binary_hash)  # 转换为二进制字符串

        output = text_model(text_feature)
        binary_hash = (output >= 0.0).float()
        binary_hash = binary_hash.squeeze().cpu().numpy()
        text_binary_str = ''.join(str(int(data)) for data in binary_hash)  # 转换为二进制字符串

        #### text和text对应特征只选取第一个
        qweqwe_data = {
            "image_id": image_id,
            "image_file_name": image_file_name,
            "text": text[0],
            "image_hash_code": img_binary_str,
            "text_hash_code": text_binary_str,
        }

        image_text_list.append(qweqwe_data)
    image_text_list_save_path = os.path.join("dataset", "image_text_hash_code")
    torch.save(image_text_list, image_text_list_save_path)


    for item in tqdm(audio_text_feature):
        # [  {"audio_file_name": "0.wav", "audio_class_label": "dog", "audio_id": 0, "audio_feature": [[ feature]], "text_feature": [[ feature ]] `````]
        audio_file_name = item['audio_file_name']
        audio_class_label = item['audio_class_label']
        audio_id = item['audio_id']
        audio_feature = torch.tensor(item['audio_feature'][0], dtype=torch.float32).to(device).unsqueeze(dim=0)

        output = audio_model(audio_feature)
        binary_hash = (output >= 0.0).float()
        binary_hash = binary_hash.squeeze().cpu().numpy()
        audio_binary_str = ''.join(str(int(data)) for data in binary_hash)  # 转换为二进制字符串

        qweqwe_data = {
            "audio_file_name": audio_file_name,
            "audio_class_label": audio_class_label,
            "audio_id": audio_id,
            "audio_hash_code": audio_binary_str,
        }

        audio_data_list.append(qweqwe_data)
    audio_text_list_save_path = os.path.join("dataset", "audio_hash_code")
    torch.save(audio_data_list, audio_text_list_save_path)

    print("save img text hash end!!")

if __name__ == '__main__':
    extract_hash()

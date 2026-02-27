import torch
import os
from googletrans import Translator
from tqdm import tqdm
import json
from PIL import Image

import imagebind
from imagebind import data
from imagebind.models import imagebind_model
from imagebind.models.imagebind_model import ModalityType

device = "cuda" if torch.cuda.is_available() else "cpu"

model = imagebind_model.imagebind_huge(pretrained=True)
model.eval()
model.to(device)

def retrival(save_path, input_feature):
    # [  {"audio_file_name": "0.wav", "audio_class_label": "dog", "audio_id": 0, "audio_feature": [[ feature]], "text_feature": [[ feature ]] `````]
    audio_feature_database_path = os.path.join(save_path, "audio_feature")
    # [ {"image_id": 391895, "image_file_name": "000000391895.jpg", "text": ["A man ide."], "image_feature": [[ feature]] "text_feature": [[feature, feature]] ````]
    image_text_feature_database_path = os.path.join(save_path, "img_text_feature")

    image_feature_list, text_feature_list = [], []
    # json 每行读太慢了， 要五分钟读完MSCOCO 用torch吧
    audio_feature = torch.load(audio_feature_database_path)
    print("audio feature load end")
    image_text_feature = torch.load(image_text_feature_database_path)
    print("image text feature load end")

    for line_data in tqdm(image_text_feature):
        image_feature_list.append(torch.tensor(line_data["image_feature"], dtype=torch.float32))
        # 这块每个图像对应五个文本就有点问题
        text_feature_list.extend([torch.tensor([line_data["text_feature"][0]], dtype=torch.float32) ])

    image_feature_tensor = torch.cat(image_feature_list, dim=0).cuda()
    text_feature_tensor = torch.cat(text_feature_list, dim=0).cuda()

    audio_feature_list = []
    for line_data in tqdm(audio_feature):
        audio_feature_list.append(torch.tensor(line_data["audio_feature"], dtype=torch.float32))

    audio_feature_tensor = torch.cat(audio_feature_list, dim=0).cuda()

    # # 图搜文
    # vision_text_similarity = torch.nn.functional.cosine_similarity(
    #     input_feature[ModalityType.VISION], text_feature_tensor
    # )

    # # 图搜音频
    # vision_audio_similarity = torch.nn.functional.cosine_similarity(
    #     input_feature[ModalityType.VISION], audio_feature_tensor
    # )

    # 文搜图
    text_image_similarity = torch.nn.functional.cosine_similarity(
        input_feature[ModalityType.TEXT], image_feature_tensor
    )

    # # 文搜音频
    # text_audio_similarity = torch.nn.functional.cosine_similarity(
    #     input_feature[ModalityType.TEXT], audio_feature_tensor
    # )

    # # 音频搜图
    # audio_image_similarity = torch.nn.functional.cosine_similarity(
    #     input_feature[ModalityType.AUDIO], image_feature_tensor
    # )

    # ### AAAA 音频搜文 效果比较差
    # audio_text_similarity = torch.nn.functional.cosine_similarity(
    #     input_feature[ModalityType.AUDIO], text_feature_tensor
    # )

    # 取 Top-K 最相似的图像和文本
    top_k = 5
    # top_vision_audio_indices = torch.topk(vision_audio_similarity, top_k).indices
    # top_text_audio_indices = torch.topk(text_audio_similarity, top_k).indices
    # top_audio_text_indices = torch.topk(audio_image_similarity, top_k).indices
    top_text_image_indices = torch.topk(text_image_similarity, top_k).indices

    # for idx in top_vision_audio_indices:
    #     print(f"图搜音频 : {audio_feature[idx]['audio_class_label']}")
    #
    # for idx in top_text_audio_indices:
    #     print(f"文搜音频 : {audio_feature[idx]['audio_class_label']}")
    #
    # for idx in top_audio_text_indices:
    #     print(f"音频搜图 image flie name : {image_text_feature[idx]['image_file_name']}")

    for idx in top_text_image_indices:
        img_file_name = image_text_feature[idx]['image_file_name']
        print(f"文搜图 image flie name : {img_file_name}")
        # 显示图像
        img_file_name = os.path.join(save_path, "MSCOCO_origin", "train2017", img_file_name)
        img = Image.open(img_file_name)
        img.show()


if __name__ == '__main__':
    # 明文检索是ok的，但是密文检索还是有点问题，要找找方法
    save_path = "dataset"
    os.makedirs(save_path, exist_ok=True)

    zn_text_list=["狗"]
    image_paths = [".assets/dog_image.jpg"]
    audio_paths = [".assets/dog_audio.wav"]

    en_text_list = []
    tanslator = Translator()
    for zn_text in zn_text_list:
        result = tanslator.translate(zn_text, src='zh-cn', dest='en').text
        en_text_list.append(result)

    inputs = {
        ModalityType.TEXT: data.load_and_transform_text(en_text_list, device),
        ModalityType.VISION: data.load_and_transform_vision_data(image_paths, device),
        ModalityType.AUDIO: data.load_and_transform_audio_data(audio_paths, device),
    }

    with torch.no_grad():
        input_feature = model(inputs)

    retrival(save_path, input_feature)

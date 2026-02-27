"""
ESC-50的原始数据来自这个网站 https://github.com/karolpiczak/ESC-50?tab=readme-ov-file
音频相比audioset只有5s但是质量更高，不知道那个模型能不能正确去分类
"""
import json

import pandas as pd
import os
from tqdm import tqdm
import librosa
import soundfile as sf

# #　带ｌａｂｅｌ清洗
# def deal_ESC_50(save_path):
#     audio_path = os.path.join(save_path, "ESC-50_origin", "audio")
#     label_path = os.path.join(save_path, "ESC-50_origin", "esc50.csv")
#
#     label_df = pd.read_csv(label_path)
#     class_label_list = []
#
#     class_label_save_path = os.path.join(save_path, "ESC-50_classified", "class_label.json")
#     with open(class_label_save_path, "w+") as f:
#         for idx, row in tqdm(label_df.iterrows()):
#             file_name = os.path.join(audio_path, row['filename'])
#
#             class_label = row['category']
#
#             label_path = os.path.join(save_path, "ESC-50_classified", class_label)
#             if not os.path.exists(label_path):
#                 os.makedirs(label_path)
#                 class_label_list.append(class_label)
#
#             # 加载音频数据
#             audio_data, sample_rate = librosa.load(file_name, sr=None)
#
#             # 保存音频数据到新的路径
#             output_file = os.path.join(label_path, f"{idx}" + '.wav')
#             sf.write(output_file, audio_data, sample_rate)
#             print(f"Audio file saved to: {output_file}")
#
#             data = {
#                 "audio_file_name": f"{idx}" + '.wav',
#                 "audio_class_label": class_label,
#                 "audio_id": idx
#             }
#             f.write(json.dumps(data)+ "\n")


#　不带ｌａｂｅｌ清洗
def deal_ESC_50(save_path):
    audio_path = os.path.join(save_path, "ESC-50_origin", "audio")
    label_path = os.path.join(save_path, "ESC-50_origin", "esc50.csv")

    label_df = pd.read_csv(label_path)
    class_label_list = []

    class_label_save_path = os.path.join(save_path, "ESC-50_classified", "class_label.json")
    with open(class_label_save_path, "w+") as f:
        for idx, row in tqdm(label_df.iterrows()):
            file_name = os.path.join(audio_path, row['filename'])

            class_label = row['category']

            label_path = os.path.join(save_path, "ESC-50_classified", "audio_database")
            if not os.path.exists(label_path):
                os.makedirs(label_path)
                class_label_list.append(class_label)

            # 加载音频数据
            audio_data, sample_rate = librosa.load(file_name, sr=None)

            # 保存音频数据到新的路径
            output_file = os.path.join(label_path, f"{idx}" + '.wav')
            sf.write(output_file, audio_data, sample_rate)
            print(f"Audio file saved to: {output_file}")

if __name__ == '__main__':
    save_path = "../dataset"
    os.makedirs(save_path, exist_ok=True)

    deal_ESC_50(save_path)

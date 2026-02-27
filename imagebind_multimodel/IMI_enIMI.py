from scheme_AES import *
from collections import defaultdict
import torch
import pickle
import os
from tqdm import tqdm

hash_len = 32
ss = 4
blocksize = 16


def make_IMI_enIMI():
    hashLenByte = hash_len >> 3  # 字节数

    # 列表里面嵌套集合（键值对） 方便添加集合
    IMI_image = [defaultdict(set) for i in range(ss)]
    IMI_text = [defaultdict(set) for i in range(ss)]
    IMI_audio = [defaultdict(set) for i in range(ss)]

    enIMI_image = [{} for i in range(ss)]
    enIMI_text = [{} for i in range(ss)]
    enIMI_audio = [{} for i in range(ss)]

    # 导入image text hash文件
    hash_code_path = "dataset"
    image_text_hash_path = os.path.join(hash_code_path, f"image_text_hash_code")
    audio_hash_path = os.path.join(hash_code_path, f"audio_hash_code")
    assert image_text_hash_path, "image hash not exist!!"
    assert audio_hash_path, "text hash not exist!!"
    # [  {"audio_file_name": "0.wav", "audio_class_label": "dog", "audio_id": 0, "audio_hash_code": " 010101" `````]
    # [ {"image_id": 391895, "image_file_name": "000000391895.jpg", "text": ["A man ide."], "image_hash_code": "01010101", "text_hash_code": "0101010101" ````]
    image_text_data = torch.load(image_text_hash_path)
    audio_data = torch.load(audio_hash_path)

    # img text num
    image_hash, text_hash, audio_hash = [], [], []
    for data in image_text_data:
        image_hash.append(data['image_hash_code'])
        text_hash.append(data['text_hash_code'])
    for data in audio_data:
        audio_hash.append(data['audio_hash_code'])

    print(image_hash[:1000])

    image_num = len(image_hash)
    text_num = len(text_hash)
    audio_num = len(audio_hash)
    print(f"image hash num : {image_num}")
    print(f"text hash num : {text_num}")
    print(f"audio hash num : {audio_num}")

    # 制作IMI索引文件
    IMI_path = "dataset"
    IMI_image_file = os.path.join(IMI_path, f'IMI_image_{hash_len}_{ss}_.pkl')
    IMI_text_file = os.path.join(IMI_path, f'IMI_text_{hash_len}_{ss}_.pkl')
    IMI_audio_file = os.path.join(IMI_path, f'IMI_audio_{hash_len}_{ss}_.pkl')

    interval = (hashLenByte // ss)

    # image hash 制作IMI
    for i in tqdm(range(image_num)):
        content = int(image_hash[i], 2)  # 转化成十进制int
        content = content.to_bytes(hashLenByte, byteorder='big')  # 把content转化成与hashLenByte一样大小的字节，"big"表示大端表示法
        for j, II in enumerate(IMI_image):
            l, r = interval * j, interval * (j + 1)
            II[content[l: r]].add(i)

    with open(IMI_image_file, 'wb') as f:
        pickle.dump(IMI_image, f)

    # text hash 制作IMI
    for i in tqdm(range(text_num)):
        content = int(text_hash[i], 2)  # 转化成十进制int
        content = content.to_bytes(hashLenByte, byteorder='big')  # 把content转化成与hashLenByte一样大小的字节，"big"表示大端表示法
        for j, II in enumerate(IMI_text):
            l, r = interval * j, interval * (j + 1)
            II[content[l: r]].add(i)

    with open(IMI_text_file, 'wb') as f:
        pickle.dump(IMI_text, f)

    # audio hash 制作IMI
    for i in tqdm(range(audio_num)):
        content = int(audio_hash[i], 2)  # 转化成十进制int
        content = content.to_bytes(hashLenByte, byteorder='big')  # 把content转化成与hashLenByte一样大小的字节，"big"表示大端表示法
        for j, II in enumerate(IMI_audio):
            l, r = interval * j, interval * (j + 1)
            II[content[l: r]].add(i)

    with open(IMI_audio_file, 'wb') as f:
        pickle.dump(IMI_audio, f)

    # IMI每个M的value的最大数目，因为最终加密的时候要进行padding
    max_img_ElemNum = []
    max_text_ElemNum = []
    max_audio_ElemNum = []
    for idx, II in enumerate(IMI_image):
        max_img_ElemNum.append(max([len(item) for item in II.values()]))
    for idx, II in enumerate(IMI_text):
        max_text_ElemNum.append(max([len(item) for item in II.values()]))
    for idx, II in enumerate(IMI_audio):
        max_audio_ElemNum.append(max([len(item) for item in II.values()]))

    # data owner 对IMI 进行加密操作的一个类
    data_owner = Label(blocksize=blocksize)

    # 加密IMI
    enIMI_path = "dataset"
    enIMI_image_file = os.path.join(enIMI_path, f'enIMI_image_{hash_len}_{ss}.pkl')
    enIMI_text_file = os.path.join(enIMI_path, f'enIMI_text_{hash_len}_{ss}.pkl')
    enIMI_audio_file = os.path.join(enIMI_path, f'enIMI_audio_{hash_len}_{ss}.pkl')

    for i, II in enumerate(IMI_image):
        enIMI_image[i] = data_owner.Enc(data_owner.Gen(), II)
    for i, II in enumerate(IMI_text):
        enIMI_text[i] = data_owner.Enc(data_owner.Gen(), II)
    for i, II in enumerate(IMI_audio):
        enIMI_audio[i] = data_owner.Enc(data_owner.Gen(), II)

    with open(enIMI_image_file, 'wb') as f:
        pickle.dump(enIMI_image, f)
    with open(enIMI_text_file, 'wb') as f:
        pickle.dump(enIMI_text, f)
    with open(enIMI_audio_file, 'wb') as f:
        pickle.dump(enIMI_audio, f)


if __name__ == '__main__':
    make_IMI_enIMI()

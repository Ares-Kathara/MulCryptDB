import os
import pickle
import time
from os import utime
import asyncio
from PIL import Image
# from googletrans import Translator
from translate import Translator


from scheme_AES import *
from utils import *

from imagebind import data
from imagebind.models import imagebind_model
from imagebind.models.imagebind_model import ModalityType
import torch.nn.functional as F

import random
import numpy as np
seed = 2025

torch.manual_seed(seed)
# torch.cuda.manual_seed(seed)
# torch.cuda.manual_seed_all(seed)  # if you are using multi-GPU.
np.random.seed(seed)  # Numpy module.
random.seed(seed)  # Python random module.
torch.use_deterministic_algorithms(True)  # for pytorch >= 1.8
torch.backends.cudnn.enabled = False
torch.backends.cudnn.benchmark = False
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
os.environ['PYTHONHASHSEED'] = str(seed)

blocksize = 16
hash_len = 32
ss = 4
R = 5
hashLenByte = hash_len >> 3
epoch = 100
top_k_num=1

# 导入imagebind 模型
# device = "cuda" if torch.cuda.is_available() else "cpu"
device = torch.device("cpu")

model = imagebind_model.imagebind_huge(pretrained=True)
model.eval()
model.to(device)

# 导入MLP模型
# image_model = ImageMlp(1024, hash_len).cuda()
# text_model = TextMlp(1024, hash_len).cuda()
# audio_model = AudioMlp(1024, hash_len).cuda()
image_model = ImageMlp(1024, hash_len).to(device)
text_model = TextMlp(1024, hash_len).to(device)
audio_model = AudioMlp(1024, hash_len).to(device)

file_name = 'hash_' + str(hash_len) + f"_epoch_{epoch}" + ".pt"
model_state_path = f'hash_model_save'
model_state_path = os.path.join(model_state_path, file_name)
# state = torch.load(model_state_path)
state = torch.load(model_state_path,map_location=device)

image_model.load_state_dict(state["ImageMlp"])
text_model.load_state_dict(state['TextMlp'])
audio_model.load_state_dict(state['AudioMlp'])

# 导入两个主要的类， data_owner用于对data IMI 加密， user用于检索操作
data_owner = Label(blocksize=blocksize)
user = User(blocksize=blocksize, hashLen=hash_len, K=data_owner.Gen(), ss=ss)

# 导入事先计算好的image text audio enIMI
enIMI_image_path = os.path.join(f"dataset/enIMI_image_{hash_len}_{ss}.pkl")
enIMI_text_path = os.path.join(f"dataset/enIMI_text_{hash_len}_{ss}.pkl")
enIMI_audio_path = os.path.join(f"dataset/enIMI_audio_{hash_len}_{ss}.pkl")
with open(enIMI_image_path, "rb") as file:
    enIMI_image= pickle.load(file)
with open(enIMI_text_path, "rb") as file:
    enIMI_text = pickle.load(file)
with open(enIMI_audio_path, "rb") as file:
    enIMI_audio = pickle.load(file)

# 采用递归的方法去给出指定R下所有SS可能的r情况，比如nn=2, ss=2，输出结果为[0,0] [0,1] [1,0] [1,1]
partitions_dict = {}
for nn in range(R + 1):
    partitions = partition_ordered(nn, ss, hash_len // ss)
    partitions_dict[(nn, ss)] = partitions

# 导入image text hash文件 来作为 id和原始文件的映射
hash_code_path = "dataset"
image_text_hash_path = os.path.join(hash_code_path, f"image_text_hash_code")
audio_hash_path = os.path.join(hash_code_path, f"audio_hash_code")
assert image_text_hash_path, "image hash not exist!!"
assert audio_hash_path, "text hash not exist!!"
# [  {"audio_file_name": "0.wav", "audio_class_label": "dog", "audio_id": 0, "audio_hash_code": " 010101" `````]
# [ {"image_id": 391895, "image_file_name": "000000391895.jpg", "text": ["A man ide."], "image_hash_code": "01010101", "text_hash_code": "0101010101" ````]
image_text_database = torch.load(image_text_hash_path)
audio_database = torch.load(audio_hash_path)

# 图像、音频放的位置
origin_img_path = "dataset/MSCOCO_origin/train2017"
origin_audio_path = "dataset/ESC-50_classified"

# 输入加密IMI，查询和汉明距离R
def pack_Search(enIMI, query, R):
    # 生成查询令牌
    query = int(query, 2)
    query = query.to_bytes(hashLenByte, byteorder="big")

    token_start_time = time.time()
    token = user.tokenGen(query, R, data_owner.Gen())
    token_total_time = time.time() - token_start_time
    # print(f"生成token所需时间 : {token_total_time:.6f}")
    yield f"生成token所需时间 : {token_total_time:.6f}\n".encode('utf-8')

    # print("加密token：")
    yield "加密token：\n".encode('utf-8')

    for key, value_list in token[0].items():
        # print(f"r={key}时")
        yield f"r={key}时\n".encode('utf-8')
        for pair in value_list:
            yield f"token : {pair[0].hex()}, {pair[1].hex()}\n".encode('utf-8')

    # 产生搜索结果
    search_start_time = time.time()
    res = user.hammingSearch(enIMI, token, R, partitions_dict)
    search_total_time = time.time() - search_start_time
    # print(f"返回加密检索结果：")
    yield "返回加密检索结果：\n".encode('utf-8')

    for item in res:
        if item != set():
            for idx in item:
                # print(f"{idx.hex()}")
                yield f"{idx.hex()}\n".encode('utf-8')

    # 对res解密
    result_list = []
    for data in res:
        if data:  # 检查集合是否非空
            for item in data:
                de_id = decrypt(item, 'd' * blocksize, blocksize)
                result_list.append(int.from_bytes(de_id, byteorder='big'))  # 解码字符串
    # print(f"检索所需时间 : {search_total_time:.6f}")
    yield f"检索所需时间 : {search_total_time:.6f}\n".encode('utf-8')
    # return result_list
    yield result_list

# def zn_en(Chinese_text):
#     translator = Translator()
#     english_text = translator.translate(Chinese_text, src='zh-cn', dest='en').text
#     print(english_text)
#     return english_text
#
# def en_zn(english_text):
#     translator = Translator()
#     chinese_text = translator.translate(english_text, src='en', dest='zh-cn').text
#     print(chinese_text)
#     return chinese_text

####################################################
# def zn_en(Chinese_text):
#     translator = Translator()
#     # 在同步函数中运行异步操作
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         translation = loop.run_until_complete(
#             translator.translate(Chinese_text, src='zh-cn', dest='en')
#         )
#         english_text = translation.text
#         print(english_text)
#         return english_text
#     finally:
#         loop.close()
#
# def en_zn(english_text):
#     translator = Translator()
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     try:
#         translation = loop.run_until_complete(
#             translator.translate(english_text, src='en', dest='zh-cn')
#         )
#         chinese_text = translation.text
#         print(chinese_text)
#         return chinese_text
#     finally:
#         loop.close()



def zn_en(Chinese_text):
    try:
        # 创建翻译器，从中文到英文
        translator = Translator(from_lang='zh', to_lang='en')
        # 执行翻译
        english_text = translator.translate(Chinese_text)
        print(english_text)
        return english_text
    except Exception as e:
        print(f"翻译错误: {e}")
        return Chinese_text  # 如果翻译失败，返回原文本

def en_zn(english_text):
    try:
        # 创建翻译器，从英文到中文
        translator = Translator(from_lang='en', to_lang='zh')
        # 执行翻译
        chinese_text = translator.translate(english_text)
        print(chinese_text)
        return chinese_text
    except Exception as e:
        print(f"翻译错误: {e}")
        return english_text  # 如果翻译失败，返回原文本
#### 图搜音频
def img2audio_retrial(input_image_path = os.path.join(origin_img_path, "000000000081.jpg")):
    # model calculate load time
    other_time = time.time()
    inputs = {
        ModalityType.VISION: data.load_and_transform_vision_data([input_image_path], device),
    }

    with torch.no_grad():
        feature = model(inputs)

    image_feature = feature[ModalityType.VISION]

    # 得到二进制字符串
    image_model.eval()
    get_image_hash = image_model(image_feature)
    binary_hash = (get_image_hash >= 0).float()
    binary_hash = binary_hash.squeeze().cpu().numpy()
    binary_str = ''.join(str(int(b)) for b in binary_hash)  # 转换为二进制字符串

    other_total_time = time.time() - other_time
    other_total_time = f"{other_total_time:.6f}"
    yield f"推理所需时间 : {other_total_time}\n".encode('utf-8')

    # 查询
    # search_result = pack_Search(enIMI_audio, binary_str, R)
    result_list = list(pack_Search(enIMI_audio, binary_str, R))  # 把所有 yield 的值放到列表里
    search_result = result_list[-1]  # 获取最后一个 yield 出来的值
    for value in result_list[:-1]:  # 只 yield 除最后一个值之外的内容
        yield value
    yield f"检索结果数量 : {len(search_result)}\n".encode('utf-8')
    # print(f"检索结果数量 : {len(search_result)}")


    choose_audio_ids = search_result[:top_k_num]

    yield f"选择检索audio : {choose_audio_ids}\n".encode('utf-8')

    # audio_file_names = []
    # for id in choose_audio_ids:
    #     audio_file_name = audio_database[id]["audio_file_name"]
    #     audio_label = audio_database[id]["audio_class_label"]
    #     # audio_file_names.append()
    #     print(f"choose audio label : {audio_label}")

    # 给出的choose audio id 是一个列表，这里固定只返回一个
    audio_file_name = audio_database[choose_audio_ids[0]]["audio_file_name"]
    audio_label = audio_database[choose_audio_ids[0]]["audio_class_label"]
    # audio_file_names.append()
    yield f"choose audio label : {audio_label}\n".encode('utf-8')
    audio_file_path = os.path.join(origin_audio_path, audio_label, audio_file_name)
    yield f"choose audio file path : {audio_file_path}\n".encode('utf-8')

    # 只返回audio file name
    # return audio_file_name,audio_file_name
    return audio_file_name

#### 音频搜图
def audio2img_retrial(input_audio_path = os.path.join(origin_audio_path, "cat", "175.wav")):
    # model calculate load time
    other_time = time.time()
    inputs = {
        ModalityType.AUDIO: data.load_and_transform_audio_data([input_audio_path], device),
    }

    with torch.no_grad():
        feature = model(inputs)

    audio_feature = feature[ModalityType.AUDIO]

    # 得到二进制字符串
    audio_model.eval()
    get_audio_hash = audio_model(audio_feature)
    binary_hash = (get_audio_hash >= 0).float()
    binary_hash = binary_hash.squeeze().cpu().numpy()
    binary_str = ''.join(str(int(b)) for b in binary_hash)  # 转换为二进制字符串

    other_total_time = time.time() - other_time
    other_total_time = f"{other_total_time:.6f}"
    # print(f"推理所需时间 : {other_total_time}")
    yield f"推理所需时间 : {other_total_time}\n".encode('utf-8')

    # 查询
    # search_result = pack_Search(enIMI_image, binary_str, R)
    result_list = list(pack_Search(enIMI_image, binary_str, R))  # 把所有 yield 的值放到列表里
    search_result = result_list[-1]  # 获取最后一个 yield 出来的值
    for value in result_list[:-1]:  # 只 yield 除最后一个值之外的内容
        yield value
    # print(f"检索结果数量 : {len(search_result)}")
    yield f"检索结果数量 : {len(search_result)}\n".encode('utf-8')

    choose_image_ids = search_result[:top_k_num]
    # print(f"选择检索图像索引：{choose_image_ids}")
    yield f"选择检索图像索引 : {choose_image_ids}\n".encode('utf-8')

    # img_file_names = []
    # for img_id in choose_image_ids:
    #     img_file_names.append(image_text_database[img_id]["image_file_name"])
    # print(f"检索得到的文件名称：{img_file_names}")
    #
    # # 依次显示图像
    # for file_name in img_file_names:
    #     file_name = os.path.join(origin_img_path, file_name)
    #     img = Image.open(file_name)
    #     img.show()

    # 假设只返回一个检索到的值
    image_file_name = image_text_database[choose_image_ids[0]]["image_file_name"]
    image_file_path = os.path.join(origin_img_path, image_file_name)
    # img = Image.open(image_file_path)
    # img.show()
    # print("choose image file path : ", image_file_path)
    yield f"choose image file path :{image_file_path}\n".encode('utf-8')

    return image_file_name

#### 文本搜图片和音频
def text2img_audio_retrial(zn_input_text='飞机'):
    en_input_text = zn_en(zn_input_text)
    # print(en_input_text)
    yield f"{en_input_text}\n".encode('utf-8')
    # model calculate load time
    other_time = time.time()
    inputs = {
        ModalityType.TEXT: data.load_and_transform_text([en_input_text], device),
    }

    with torch.no_grad():
        feature = model(inputs)

    text_feature = feature[ModalityType.TEXT]

    # 得到二进制字符串
    text_model.eval()
    get_text_hash = text_model(text_feature)
    binary_hash = (get_text_hash >= 0).float()
    binary_hash = binary_hash.squeeze().cpu().numpy()
    binary_str = ''.join(str(int(b)) for b in binary_hash)  # 转换为二进制字符串

    other_total_time = time.time() - other_time
    other_total_time = f"{other_total_time:.6f}"
    # print(f"推理所需时间 : {other_total_time}")
    yield f"推理所需时间 : {other_total_time}\n".encode('utf-8')

    # 查询
    # search_result = pack_Search(enIMI_image, binary_str, R)
    result_list = list(pack_Search(enIMI_image, binary_str, R))  # 把所有 yield 的值放到列表里
    search_result = result_list[-1]  # 获取最后一个 yield 出来的值
    for value in result_list[:-1]:  # 只 yield 除最后一个值之外的内容
        yield value

    # print(f"检索结果数量 : {len(search_result)}")
    yield f"检索结果数量 : {len(search_result)}\n".encode('utf-8')

    choose_image_ids = search_result[:top_k_num]

    # print(f"选择检索图像索引：{choose_image_ids}")
    yield f"选择检索图像索引:{choose_image_ids}\n".encode('utf-8')

    # 假设只返回一个检索到的值
    image_file_name = image_text_database[choose_image_ids[0]]["image_file_name"]
    image_file_path = os.path.join(origin_img_path, image_file_name)

    # img = Image.open(image_file_path)
    # img.show()

    # 查询
    # search_result = pack_Search(enIMI_audio, binary_str, R)
    result_list = list(pack_Search(enIMI_audio, binary_str, R))  # 把所有 yield 的值放到列表里
    search_result = result_list[-1]  # 获取最后一个 yield 出来的值
    for value in result_list[:-1]:  # 只 yield 除最后一个值之外的内容
        yield value
    # print(f"检索结果数量 : {len(search_result)}")
    yield f"检索结果数量 : {len(search_result)}\n".encode('utf-8')

    choose_audio_ids = search_result[:top_k_num]

    # print(f"选择检索audio：{choose_audio_ids}")
    yield f"选择检索audio：{choose_audio_ids}\n".encode('utf-8')

    # 给出的choose audio id 是一个列表，这里固定只返回一个
    audio_file_name = audio_database[choose_audio_ids[0]]["audio_file_name"]
    audio_label = audio_database[choose_audio_ids[0]]["audio_class_label"]
    # audio_file_names.append()
    # print(f"choose audio label : {audio_label}")
    yield f"choose audio label : {audio_label}\n".encode('utf-8')
    audio_file_path = os.path.join(origin_audio_path, audio_file_name)

    # print("choose image file path : ", image_file_path)
    yield f"choose image file path : {image_file_path}\n".encode('utf-8')
    # print(f"choose audio file path : {audio_file_path}")
    yield f"choose audio file path : {audio_file_path}\n".encode('utf-8')

    return image_file_name, audio_file_name



#### 音频和文本搜图像
# 猫音频   趴在电脑上 cat 175.wav
# 狗音频   游泳  dog 0.wav
def audio_text2img_retrial(
        input_audio_path = os.path.join(origin_audio_path, "cat", "175.wav"), zn_input_text='趴在电脑上'):
    en_input_text = zn_en(zn_input_text)
    # model calculate load time
    other_time = time.time()
    inputs = {
        ModalityType.TEXT: data.load_and_transform_text([en_input_text], device),
        ModalityType.AUDIO: data.load_and_transform_audio_data([input_audio_path], device),
    }

    with torch.no_grad():
        feature = model(inputs)

    audio_feature = feature[ModalityType.AUDIO]
    text_feature = feature[ModalityType.TEXT]

    temperature = 0.5  # 设置温度参数

    # 对各模态特征先进行温度缩放
    audio_feature = audio_feature / temperature
    text_feature = text_feature / temperature

    audio_feature = audio_feature / torch.norm(audio_feature, dim=-1, keepdim=True)
    text_feature = text_feature / torch.norm(text_feature, dim=-1, keepdim=True)

    add_feature = 0.5 * audio_feature + 0.5 * text_feature

    # 得到二进制字符串
    image_model.eval()
    get_image_hash = image_model(add_feature)
    binary_hash = (get_image_hash >= 0).float()
    binary_hash = binary_hash.squeeze().cpu().numpy()
    binary_str = ''.join(str(int(b)) for b in binary_hash)  # 转换为二进制字符串

    other_total_time = time.time() - other_time
    other_total_time = f"{other_total_time:.6f}"
    # print(f"推理所需时间 : {other_total_time}")
    yield  f"推理所需时间 : {other_total_time}\n".encode('utf-8')

    # 查询
    # search_result = pack_Search(enIMI_image, binary_str, R)
    result_list = list(pack_Search(enIMI_image, binary_str, R))  # 把所有 yield 的值放到列表里
    search_result = result_list[-1]  # 获取最后一个 yield 出来的值
    for value in result_list[:-1]:  # 只 yield 除最后一个值之外的内容
        yield value

    # print(f"检索结果数量 : {len(search_result)}")
    yield f"检索结果数量 : {len(search_result)}\n".encode('utf-8')

    choose_image_ids = search_result[:top_k_num]

    # print(f"选择检索图像索引：{choose_image_ids}")
    yield f"选择检索图像索引:{choose_image_ids}\n".encode('utf-8')

    # img_file_names = []
    # for img_id in choose_image_ids:
    #     img_file_names.append(image_text_database[img_id]["image_file_name"])
    # print(f"检索得到的文件名称：{img_file_names}")
    #
    # # 依次显示图像
    # for file_name in img_file_names:
    #     file_name = os.path.join(origin_img_path, file_name)
    #     img = Image.open(file_name)
    #     img.show()

    # 假设只返回一个检索到的值
    image_file_name = image_text_database[choose_image_ids[0]]["image_file_name"]
    image_file_path = os.path.join(origin_img_path, image_file_name)
    # print("choose image file path : ", image_file_path)
    yield f"choose image file path : {image_file_path}\n".encode('utf-8')
    # img = Image.open(image_file_path)
    # img.show()

    return image_file_name

#### 音频和图像搜出现在图像上的音频
# 狗dog 0.wav和草地上的羊 就会检索图片是草地上的狗 2164 草地
def audio_img2img_retrial(
        input_audio_path = os.path.join(origin_audio_path, "dog", "0.wav"), input_image_path = os.path.join(origin_img_path, "000000002164.jpg")):
    # model calculate load time
    other_time = time.time()
    inputs = {
        ModalityType.VISION: data.load_and_transform_vision_data([input_image_path], device),
        ModalityType.AUDIO: data.load_and_transform_audio_data([input_audio_path], device),
    }

    with torch.no_grad():
        feature = model(inputs)

    audio_feature = feature[ModalityType.AUDIO]
    img_feature = feature[ModalityType.VISION]

    temperature = 0.5  # 设置温度参数

    # 对各模态特征先进行温度缩放
    audio_feature = audio_feature / temperature
    img_feature = img_feature / temperature

    audio_feature = audio_feature / torch.norm(audio_feature, dim=-1, keepdim=True)
    img_feature = img_feature / torch.norm(img_feature, dim=-1, keepdim=True)

    add_feature = 0.5 * audio_feature + 0.5 * img_feature

    # 得到二进制字符串
    image_model.eval()
    get_image_hash = image_model(add_feature)
    binary_hash = (get_image_hash >= 0).float()
    binary_hash = binary_hash.squeeze().cpu().numpy()
    binary_str = ''.join(str(int(b)) for b in binary_hash)  # 转换为二进制字符串

    other_total_time = time.time() - other_time
    other_total_time = f"{other_total_time:.6f}"
    # print(f"推理所需时间 : {other_total_time}")
    yield f"推理所需时间 : {other_total_time}\n".encode('utf-8')

    # 查询
    # search_result = pack_Search(enIMI_image, binary_str, R)
    result_list = list(pack_Search(enIMI_image, binary_str, R))  # 把所有 yield 的值放到列表里
    search_result = result_list[-1]  # 获取最后一个 yield 出来的值
    for value in result_list[:-1]:  # 只 yield 除最后一个值之外的内容
        yield value

    # print(f"检索结果数量 : {len(search_result)}")
    yield f"检索结果数量 : {len(search_result)}\n".encode('utf-8')

    choose_image_ids = search_result[:top_k_num]

    # print(f"选择检索图像索引：{choose_image_ids}")
    yield f"选择检索图像索引:{choose_image_ids}\n".encode('utf-8')

    # img_file_names = []
    # for img_id in choose_image_ids:
    #     img_file_names.append(image_text_database[img_id]["image_file_name"])
    # print(f"检索得到的文件名称：{img_file_names}")
    #
    # # 依次显示图像
    # for file_name in img_file_names:
    #     file_name = os.path.join(origin_img_path, file_name)
    #     img = Image.open(file_name)
    #     img.show()

    # 假设只返回一个检索到的值
    image_file_name = image_text_database[choose_image_ids[0]]["image_file_name"]
    image_file_path = os.path.join(origin_img_path, image_file_name)
    # print("choose image file path : ", image_file_path)
    yield f"choose image file path :  {image_file_path}\n".encode('utf-8')
    # img = Image.open(image_file_path)
    # img.show()

    return image_file_name

# 最后展示 图搜音频 音频搜图 文搜图片和音频 音频和文本联合搜索图像

# img2audio_retrial()
# audio2img_retrial()
# text2img_audio_retrial()
# audio_text2img_retrial()
# audio_img2img_retrial()





# #### 文搜图 #　一个人在街道上骑摩托　＃　一个猫趴在电脑键盘上　＃ 汽车在马路上行驶
# def text2img_retrial(zn_input_text='汽车在马路上行驶', top_k_num=1): #飞机　＃交通标志
#     en_input_text = zn_en(zn_input_text)
#     # print(en_input_text)
#     # model calculate load time
#     other_time = time.time()
#     inputs = {
#         ModalityType.TEXT: data.load_and_transform_text([en_input_text], device),
#     }
#
#     with torch.no_grad():
#         feature = model(inputs)
#
#     text_feature = feature[ModalityType.TEXT]
#
#     # 得到二进制字符串
#     text_model.eval()
#     get_text_hash = text_model(text_feature)
#     binary_hash = (get_text_hash >= 0).float()
#     binary_hash = binary_hash.squeeze().cpu().numpy()
#     binary_str = ''.join(str(int(b)) for b in binary_hash)  # 转换为二进制字符串
#
#     other_total_time = time.time() - other_time
#     other_total_time = f"{other_total_time:.6f}"
#     print(f"推理所需时间 : {other_total_time}")
#
#     # 查询
#     search_result = pack_Search(enIMI_image, binary_str, R)
#     print(f"检索结果数量 : {len(search_result)}")
#
#     choose_image_ids = search_result[:top_k_num]
#
#     print(f"选择检索图像索引：{choose_image_ids}")
#
#     img_file_names = []
#     for img_id in choose_image_ids:
#         img_file_names.append(image_text_database[img_id]["image_file_name"])
#     print(f"检索得到的文件名称：{img_file_names}")
#
#     # 依次显示图像
#     for file_name in img_file_names:
#         file_name = os.path.join(origin_img_path, file_name)
#         img = Image.open(file_name)
#         img.show()
#
# #### 文搜音频
# def text2audio_retrial(zn_input_text = "小猫", top_k_num=1):
#     en_input_text = zn_en(zn_input_text)
#     # model calculate load time
#     other_time = time.time()
#     inputs = {
#         ModalityType.TEXT: data.load_and_transform_text([en_input_text], device),
#     }
#
#     with torch.no_grad():
#         feature = model(inputs)
#
#     text_feature = feature[ModalityType.TEXT]
#
#     # 得到二进制字符串
#     text_model.eval()
#     get_text_hash = text_model(text_feature)
#     binary_hash = (get_text_hash >= 0).float()
#     binary_hash = binary_hash.squeeze().cpu().numpy()
#     binary_str = ''.join(str(int(b)) for b in binary_hash)  # 转换为二进制字符串
#
#     other_total_time = time.time() - other_time
#     other_total_time = f"{other_total_time:.6f}"
#     print(f"推理所需时间 : {other_total_time}")
#
#     # 查询
#     search_result = pack_Search(enIMI_audio, binary_str, R)
#     print(f"检索结果数量 : {len(search_result)}")
#
#     choose_audio_ids = search_result[:top_k_num]
#
#     print(f"选择检索audio：{choose_audio_ids}")
#
#     audio_file_names = []
#     for id in choose_audio_ids:
#         audio_file_name = audio_database[id]["audio_file_name"]
#         audio_label = audio_database[id]["audio_class_label"]
#         # audio_file_names.append()
#         print(f"choose audio label : {audio_label}")

# #### 图搜文
# def img2text_retrial(input_image_path=os.path.join(origin_img_path, "000000000081.jpg"), top_k_num=1):
#     # model calculate load time
#     other_time = time.time()
#     inputs = {
#         ModalityType.VISION: data.load_and_transform_vision_data([input_image_path], device),
#     }
#
#     with torch.no_grad():
#         feature = model(inputs)
#
#     image_feature = feature[ModalityType.VISION]
#
#     # 得到二进制字符串
#     image_model.eval()
#     get_image_hash = image_model(image_feature)
#     binary_hash = (get_image_hash >= 0).float()
#     binary_hash = binary_hash.squeeze().cpu().numpy()
#     binary_str = ''.join(str(int(b)) for b in binary_hash)  # 转换为二进制字符串
#
#     other_total_time = time.time() - other_time
#     other_total_time = f"{other_total_time:.6f}"
#     print(f"推理所需时间 : {other_total_time}")
#
#     # 查询
#     search_result = pack_Search(enIMI_text, binary_str, R)
#     print(f"检索结果数量 : {len(search_result)}")
#
#     choose_text_ids = search_result[:top_k_num]
#
#     print(f"选择检索文本索引：{choose_text_ids}")
#
#     # 依次显示文本
#     text_list = []
#     for text_id in choose_text_ids:
#         text = en_zn(image_text_database[text_id]["text"])
#         text_list.append(text)
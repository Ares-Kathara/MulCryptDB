import sys
import time
import torch.optim as optim
# from torch.optim import lr_scheduler
import torch
import os

from tqdm import tqdm
from torch.utils.data.dataset import Dataset
from torch.utils.data import DataLoader
from torch.nn import functional as F
import numpy as np
import random
from utils import setup_seed, TextMlp, ImageMlp, ContrastiveLoss, AudioMlp, save_checkpoints

epoch = 100
hash_lens = 32

# 直接从原始text数据集中的img text对来进行操作
class CustomDataSet(Dataset):
    def __init__(self, images_text_pair):
        self.img_text_pair = images_text_pair

    def __getitem__(self, index):
        img_feature = torch.tensor(self.img_text_pair[index][0], dtype=torch.float32)
        text_feature = torch.tensor(self.img_text_pair[index][1], dtype=torch.float32)
        return img_feature, text_feature, index

    def __len__(self):
        return len(self.img_text_pair)


def load_dataset(batch_size, feat_pair):
    split = 0.8
    split_num = int(len(feat_pair) * split)

    train_pair, test_pair = feat_pair[:split_num], feat_pair[split_num:]
    img_feature_len = len(train_pair[0][0])
    text_feature_len = len(train_pair[0][1])
    assert img_feature_len == text_feature_len, "img and text dim has question!!"

    train_dataset = CustomDataSet(train_pair)
    test_dataset = CustomDataSet(test_pair)
    print(f"train text pair num : {len(train_dataset)}")
    print(f"test text pair num : {len(test_dataset)}")
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, pin_memory=True)
    test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, pin_memory=True)
    print("make dataset and dataloader successfully!!")

    return img_feature_len, train_dataloader, test_dataloader


class Solver(object):
    def __init__(self, epoch, hash_lens, image_text_feature_pair, audio_text_feature_pair, model_save_path):
        self.batch_size = 256
        self.total_epoch = epoch
        self.model_save_dir = model_save_path
        self.image_text_feature_pair = image_text_feature_pair
        self.audio_text_feature_pair = audio_text_feature_pair
        self.nbits = hash_lens

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        # 制作用于model训练的train的dataloader, 因为中文数据集没有搞到查询、检索来验证训练的好坏，直接就train看loss吧
        self.feat_lens, self.image_text_train_loader, self.image_text_test_loader = load_dataset(self.batch_size, self.image_text_feature_pair)
        self.feat_lens, self.audio_text_train_loader, self.audio_text_test_loader = load_dataset(self.batch_size, self.audio_text_feature_pair)

        # 对 img text audio feature直接训练 MLP 来转化成二进制哈希码
        self.ImageMlp = ImageMlp(self.feat_lens, self.nbits).to(self.device)
        self.TextMlp = TextMlp(self.feat_lens, self.nbits).to(self.device)
        self.AudioMlp = AudioMlp(self.feat_lens, self.nbits).to(self.device)

        # 打印model总共需要的参数数量
        paramsImage = list(self.ImageMlp.parameters())
        paramsText = list(self.TextMlp.parameters())
        paramsAudio = list(self.AudioMlp.parameters())
        MLP_param = sum([param.nelement() for param in paramsImage]) + sum([param.nelement() for param in paramsText]) + sum([param.nelement() for param in paramsAudio])
        print("MLP_param:", MLP_param)

        # 优化器SGD
        self.optimizer_ImageMlp = optim.Adam(paramsImage, lr=1e-3,  betas=(0.5, 0.999))
        self.optimizer_TextMlp = optim.Adam(paramsText, lr=1e-3,  betas=(0.5, 0.999))
        self.optimizer_AudioMlp = optim.Adam(paramsAudio, lr=1e-3, betas=(0.5, 0.999))

        self.ContrastiveLoss = ContrastiveLoss(device=self.device)

    def train(self):
        print("Training Hash Fuction...")
        for epoch in range(self.total_epoch):
            self.trainhash()
            print("epoch : {}, lr : {:.6f}".format(epoch + 1, self.optimizer_ImageMlp.param_groups[0]['lr']))
            test_loss = self.testhash()
            print(f"test loss : {test_loss}")
        save_checkpoints(self, epoch + 1)

    def trainhash(self):
        self.ImageMlp.train()
        self.TextMlp.train()
        self.AudioMlp.train()
        running_loss = 0.0
        total_batches = 0

        for idx, (img, txt, _) in enumerate(tqdm(self.image_text_train_loader)):
            img, txt = img.to(self.device), txt.to(self.device)

            img_embedding = self.ImageMlp(img)
            text_embedding = self.TextMlp(txt)
            loss = self.ContrastiveLoss(img_embedding, text_embedding)

            self.optimizer_ImageMlp.zero_grad()
            self.optimizer_TextMlp.zero_grad()
            loss.backward()
            self.optimizer_ImageMlp.step()
            self.optimizer_TextMlp.step()
            running_loss += loss.item()
            total_batches += 1
        print(f"image text : running loss/total batch : {running_loss / total_batches:.6f}")
        running_loss = 0.0
        total_batches = 0
        for idx, (audio, txt, _) in enumerate(tqdm(self.audio_text_train_loader)):
            audio, txt = audio.to(self.device), txt.to(self.device)

            audio_embedding = self.AudioMlp(audio)
            text_embedding = self.TextMlp(txt)
            loss = self.ContrastiveLoss(audio_embedding, text_embedding)

            self.optimizer_AudioMlp.zero_grad()
            self.optimizer_TextMlp.zero_grad()
            loss.backward()
            self.optimizer_AudioMlp.step()
            self.optimizer_TextMlp.step()
            running_loss += loss.item()
            total_batches += 1
        print(f"audio text : running loss/total batch : {running_loss / total_batches:.6f}")
        # return running_loss / total_batches

    def testhash(self):
        self.ImageMlp.eval()
        self.TextMlp.eval()
        self.AudioMlp.eval()
        running_loss = 0.0
        total_batches = 0
        with torch.no_grad():
            for idx, (img, txt, _) in enumerate(tqdm(self.image_text_test_loader)):
                img, txt = img.to(self.device), txt.to(self.device)

                img_embedding = self.ImageMlp(img)
                text_embedding = self.TextMlp(txt)
                loss = self.ContrastiveLoss(img_embedding, text_embedding)

                running_loss += loss.item()
                total_batches += 1
        with torch.no_grad():
            for idx, (audio, txt, _) in enumerate(tqdm(self.audio_text_test_loader)):
                audio, txt = audio.to(self.device), txt.to(self.device)

                audio_embedding = self.AudioMlp(audio)
                text_embedding = self.TextMlp(txt)
                loss = self.ContrastiveLoss(audio_embedding, text_embedding)

                running_loss += loss.item()
                total_batches += 1

        return running_loss / total_batches


if __name__ == '__main__':
    # setting seed
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    seed = 2025
    setup_seed(seed)

    # MLP model 保存地址
    model_save_path = f"hash_model_save"
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

    audio_text_feature_pair = []
    for line_data in audio_text_feature:
        audio_feature = line_data['audio_feature'][0]
        text_feature = line_data['text_feature'][0]

        audio_text_feature_pair.append([audio_feature, text_feature])

    image_text_feature_pair = []
    for line_data in image_text_feature:
        image_feature = line_data['image_feature'][0]
        text_feature = line_data['text_feature'][0]

        image_text_feature_pair.append([image_feature, text_feature])

    # 输出日志地址
    out_path = 'log'
    os.makedirs(out_path, exist_ok=True)
    out_path = os.path.join(out_path, f"seed={seed}_hash_len={hash_lens}")
    sys.stdout = open(out_path, 'a+', encoding='utf-8')
    print(f"log_dir: {out_path}")

    start_time = time.time()
    task_out = str(hash_lens) + " bits" + "train hash"

    print('=============== {}--{}--Total epochs:{} ==============='.format(f"seed={seed}", f"hash_len={hash_lens}", epoch))

    print('...Training is beginning...')
    solver = Solver(epoch=epoch, hash_lens=hash_lens, image_text_feature_pair=image_text_feature_pair, audio_text_feature_pair=audio_text_feature_pair, model_save_path=model_save_path)
    print("init end!!!")

    solver.train()
    time_elapsed = time.time() - start_time
    print(f"train total time:{time_elapsed}")

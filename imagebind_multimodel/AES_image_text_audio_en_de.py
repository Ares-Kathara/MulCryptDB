import sys
import wave

import cv2
import numpy as np
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
np.random.seed(2025)


# 选择加密模式（包括ECB和CBC）
mode = AES.MODE_CBC
# mode = AES.MODE_ECB
if mode != AES.MODE_CBC and mode != AES.MODE_ECB:
    print('Only CBC and ECB mode supported...')
    sys.exit()

# 设置密钥长度
keySize = 32
ivSize = AES.block_size if mode == AES.MODE_CBC else 0 # AES.blocksize = 16
print(f"AES.block_size:{AES.block_size}")
# 密钥key和初始向量IV
key = (b'a' * keySize)
iv = (b"a" * ivSize)

### 输入：原始图像地址、输出加密图像地址  输出：无
def encrypt_image(origin_image_path, encrypt_image_path):
    imageOrig = cv2.imread(origin_image_path)
    rowOrig, columnOrig, depthOrig = imageOrig.shape
    print(f"image size : {imageOrig.shape}")

    # 检查图像的宽度是否低于图像加密的宽度限制
    minWidth = (AES.block_size + AES.block_size) // depthOrig + 1
    print(f"minWidth:{minWidth}")
    if columnOrig < minWidth:
        print('The minimum width of the image must be {} pixels, so that IV and padding can be stored in a single additional row!'.format(minWidth))
        sys.exit()

    imageOrigBytes = imageOrig.tobytes()
    print(f"image data to byte: {len(imageOrigBytes)}")

    ### 加密
    # 初始化AES加密器
    cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)

    # 填充
    imageOrigBytesPadded = pad(imageOrigBytes, AES.block_size, "pkcs7")
    ciphertext = cipher.encrypt(imageOrigBytesPadded)

    paddedSize = len(imageOrigBytesPadded) - len(imageOrigBytes)
    print(f'paddedSize: {paddedSize}')

    void = columnOrig * depthOrig - ivSize - paddedSize
    ivCiphertextVoid = iv + ciphertext + bytes(void)

    # 字节---》图像
    imageEncrypted = np.frombuffer(ivCiphertextVoid, dtype=imageOrig.dtype).reshape(rowOrig + 1, columnOrig, depthOrig)

    # 保存加密图像
    cv2.imwrite(encrypt_image_path, imageEncrypted)

### 输入：加密图像地址、解密图像地址 输出：无
def decrypt_image(encrypt_image_path, decrypt_image_path):
    imageEncrypted = cv2.imread(encrypt_image_path)
    rowEncrypted, columnOrig, depthOrig = imageEncrypted.shape
    rowOrig = rowEncrypted - 1
    # np矩阵转字节
    encryptedBytes = imageEncrypted.tobytes()
    # 取前IvSize位为IV
    iv = encryptedBytes[:ivSize]
    imageOrigBytesSize = rowOrig * columnOrig * depthOrig
    # 确定填充的字节数
    paddedSize = (imageOrigBytesSize // AES.block_size + 1) * AES.block_size - imageOrigBytesSize
    # 确定图像的密文
    encrypted = encryptedBytes[ivSize: ivSize + imageOrigBytesSize + paddedSize]

    # 解密
    cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)
    decryptedImageBytesPadded = cipher.decrypt(encrypted)
    # 去除填充的数据
    decryptedImageBytes = unpad(decryptedImageBytesPadded, AES.block_size, "pkcs7")

    # 字节---》图像
    decryptedImage = np.frombuffer(decryptedImageBytes, imageEncrypted.dtype).reshape(rowOrig, columnOrig, depthOrig)

    cv2.imwrite(decrypt_image_path, decryptedImage)

### 输入：原始文本  输出：加密文本
def encrypt_text(origin_text):
    ### 加密
    # 初始化AES加密器
    cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)
    pad_text = pad(origin_text.encode(), AES.block_size, "pkcs7")

    en_text = cipher.encrypt(pad_text)
    return  en_text

### 输入：加密文本  输出：解密文本
def decrypt_text(en_text):
    cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)
    de_text = cipher.decrypt(en_text)
    de_text = unpad(de_text, AES.block_size, "pkcs7")

    return de_text.decode("utf-8")

### 输入：原始音频地址、输出加密音频地址  输出：无
def encrypt_audio(origin_audio_path, encrypt_audio_path):
    with wave.open(origin_audio_path, "rb") as wf:
        # 读取音频文件头信息
        params = wf.getparams()
        nchannels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        comptype = wf.getcomptype()
        compname = wf.getcompname()

        # 读取音频数据
        audio_data = wf.readframes(nframes)
        wf.close()

    cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)
    pad_audio = pad(audio_data, AES.block_size, "pkcs7")

    en_audio = cipher.encrypt(pad_audio)

    with wave.open(encrypt_audio_path, 'wb') as wf:
        wf.setparams((nchannels, sample_width, framerate, nframes, comptype, compname))
        wf.writeframes(en_audio)
        wf.close()


### 输入： 加密音频地址、解密音频地址  输出：无
def decrypt_audio(encrypt_audio_path, decrypt_audio_path):
    with wave.open(encrypt_audio_path, 'rb') as wf:
        # 读取音频文件头信息
        params = wf.getparams()
        nchannels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        comptype = wf.getcomptype()
        compname = wf.getcompname()

        # 读取加密音频数据
        en_audio = wf.readframes(nframes)
        wf.close()
    cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)
    de_audio = cipher.decrypt(en_audio)
    de_audio = unpad(de_audio, AES.block_size, "pkcs7")

    # 写入解密后的音频文件
    with wave.open(decrypt_audio_path, 'wb') as wf:
        wf.setparams((nchannels, sample_width, framerate, nframes, comptype, compname))
        wf.writeframes(de_audio)
        wf.close()

# jpg是有损格式压缩，加密保存用jpg保存的话会导致信息丢失，还是用png保存吧
origin_image_file_name = "000000000034"
origin_image_path = f"data/{origin_image_file_name}.jpg"
encrypt_image_path = f"data/AES_encrypt_{origin_image_file_name}.png"
encrypt_image(origin_image_path, encrypt_image_path)

decrypt_image_path = f"data/AES_decrypt_{origin_image_file_name}.jpg"
decrypt_image(encrypt_image_path, decrypt_image_path)

origin_text = "qweqweqw"
en_text = encrypt_text(origin_text)
de_text = decrypt_text(en_text)
print(f"AES en_text: {en_text}")
print(f"AES de_text: {de_text}")

origin_audio_file_name = "dog.wav"
origin_audio_path = f"data/dog.wav"
encrypt_audio_path = f"data/AES_encrypt_{origin_audio_file_name}"
encrypt_audio(origin_audio_path, encrypt_audio_path)

decrypt_audio_path = f"data/AES_decrypt_{origin_audio_file_name}"
decrypt_audio(encrypt_audio_path, decrypt_audio_path)



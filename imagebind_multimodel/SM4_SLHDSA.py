import oqs
import hashlib
import os
import wave
import cv2
import time
import numpy as np
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
from Crypto.Util.Padding import pad, unpad

SIG_ALGO = "SPHINCS+-SHAKE-128f-simple"

np.random.seed(2025)

# 模式配置
MODE = 'CBC'  # 'ECB' 或 'CBC'
block_size = 16
key = b'a' * 16
iv = b'a' * 16 if MODE == 'CBC' else None

def sm4_encrypt(data: bytes) -> bytes:
    crypt_sm4 = CryptSM4()
    crypt_sm4.set_key(key, SM4_ENCRYPT)
    data = pad(data, block_size, style='pkcs7')
    return crypt_sm4.crypt_cbc(iv, data) if MODE == 'CBC' else crypt_sm4.crypt_ecb(data)


def sm4_decrypt(data: bytes) -> bytes:
    crypt_sm4 = CryptSM4()
    crypt_sm4.set_key(key, SM4_DECRYPT)
    decrypted = crypt_sm4.crypt_cbc(iv, data) if MODE == 'CBC' else crypt_sm4.crypt_ecb(data)
    return unpad(decrypted, block_size, style='pkcs7')


# ---------- 文本 ----------
def encrypt_text(origin_text: str) -> bytes:
    return sm4_encrypt(origin_text.encode())


def decrypt_text(en_text: bytes) -> str:
    return sm4_decrypt(en_text).decode('utf-8')


# ---------- 图像 ----------
def encrypt_image(origin_image_path, encrypt_image_path) -> bytes:
    image = cv2.imread(origin_image_path)
    h, w, c = image.shape
    raw_bytes = image.tobytes()
    ciphertext = sm4_encrypt(raw_bytes)

    padded = len(ciphertext) - len(raw_bytes)
    iv_size = 16 if MODE == 'CBC' else 0
    fill = w * c - iv_size - padded
    total_bytes = (iv if iv else b'') + ciphertext + bytes(fill)

    image_enc = np.frombuffer(total_bytes, dtype=image.dtype).reshape(h + 1, w, c)
    cv2.imwrite(encrypt_image_path, image_enc)
    return ciphertext


def decrypt_image(encrypt_image_path, decrypt_image_path) -> bytes:
    image = cv2.imread(encrypt_image_path)
    h, w, c = image.shape
    h -= 1  # 原图高度
    raw = image.tobytes()

    iv_size = 16 if MODE == 'CBC' else 0
    useful = raw[iv_size:].rstrip(b'\x00')
    plain_bytes = sm4_decrypt(useful)

    image_dec = np.frombuffer(plain_bytes, dtype=image.dtype).reshape(h, w, c)
    cv2.imwrite(decrypt_image_path, image_dec)
    return plain_bytes


# ---------- 音频 ----------
def encrypt_audio(origin_audio_path, encrypt_audio_path) -> bytes:
    with wave.open(origin_audio_path, "rb") as wf:
        params = wf.getparams()
        audio_data = wf.readframes(params.nframes)

    ciphertext = sm4_encrypt(audio_data)

    os.makedirs(os.path.dirname(encrypt_audio_path), exist_ok=True)
    with wave.open(encrypt_audio_path, 'wb') as wf:
        wf.setparams(params)
        wf.writeframes(ciphertext)

    return ciphertext


def decrypt_audio(encrypt_audio_path, decrypt_audio_path) -> bytes:
    with wave.open(encrypt_audio_path, 'rb') as wf:
        params = wf.getparams()
        enc_data = wf.readframes(params.nframes)

    plain_data = sm4_decrypt(enc_data)

    os.makedirs(os.path.dirname(decrypt_audio_path), exist_ok=True)
    with wave.open(decrypt_audio_path, 'wb') as wf:
        wf.setparams(params)
        wf.writeframes(plain_data)

    return plain_data

# 对密文求hash
def hash_data(data: bytes) -> bytes:
    return hashlib.shake_256(data).digest(32)

# 对每个data都保存一个公钥，私钥指用来签名或许都不用保存？
def sign_data(data: bytes):
    digest = hash_data(data)
    with oqs.Signature(SIG_ALGO) as signer:
        public_key = signer.generate_keypair()
        # private_key = signer.export_secret_key()  # 若以后支持恢复，可保存
        signature = signer.sign(digest)
    return signature, public_key


def verify_signature(data: bytes, signature: bytes, public_key: bytes) -> bool:
    digest = hash_data(data)
    with oqs.Signature(SIG_ALGO) as verifier:
        return verifier.verify(digest, signature, public_key)

# # ------------------- 测试调用 -------------------
# # -----图片
# origin_image_file_name = "000000000034"
# origin_image_path = f"data/{origin_image_file_name}.jpg"
# encrypt_image_path = f"data/SM4_encrypt_{origin_image_file_name}.png"
# decrypt_image_path = f"data/SM4_decrypt_{origin_image_file_name}.jpg"
# # --- 加密图像 ---
# start_encrypt = time.perf_counter()
# en_image = encrypt_image(origin_image_path, encrypt_image_path)
# end_encrypt = time.perf_counter()
# print(f"图像加密耗时: {end_encrypt - start_encrypt:.4f} 秒")
# # --- 生成签名 ---
# start_sign = time.perf_counter()
# signature, public_key = sign_data(en_image)
# end_sign = time.perf_counter()
# print(f"生成签名耗时: {end_sign - start_sign:.4f} 秒")
# # --- 验证签名 ---
# start_verify = time.perf_counter()
# valid = verify_signature(en_image, signature, public_key)
# end_verify = time.perf_counter()
# print(f"签名验证耗时: {end_verify - start_verify:.4f} 秒")
# print(f"后量子签名验证结果: {valid}")
# # --- 解密图像 ---
# start_decrypt = time.perf_counter()
# decrypt_image(encrypt_image_path, decrypt_image_path)
# end_decrypt = time.perf_counter()
# print(f"图像解密耗时: {end_decrypt - start_decrypt:.4f} 秒")
#
#
#
# # -----文本
# origin_text = "qweqweqw"
# # 加密
# en_text = encrypt_text(origin_text)
# # 生成签名
# signature, public_key = sign_data(en_text)
# # 验签
# valid = verify_signature(en_text, signature, public_key)
# print(f"后量子签名验证结果: {valid}")
# # 解密
# decrypt_text(en_text)
#
#
#
# # -----音频
# origin_audio_file_name = "dog.wav"
# origin_audio_path = f"data/{origin_audio_file_name}"
# encrypt_audio_path = f"data/SM4_encrypt_{origin_audio_file_name}"
# decrypt_audio_path = f"data/SM4_decrypt_{origin_audio_file_name}"
# # 加密
# en_audio = encrypt_audio(origin_audio_path, encrypt_audio_path)
# # 生成签名
# signature, public_key = sign_data(en_audio)
# # 验签
# valid = verify_signature(en_audio, signature, public_key)
# print(f"后量子签名验证结果: {valid}")
# # 解密
# decrypt_audio(encrypt_audio_path, decrypt_audio_path)

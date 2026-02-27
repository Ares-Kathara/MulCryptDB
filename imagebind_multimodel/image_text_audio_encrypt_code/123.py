import sys
import cv2
import numpy as np
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes


# 选择加密模式（包括ECB和CBC）
mode = AES.MODE_CBC
# mode = AES.MODE_ECB
if mode != AES.MODE_CBC and mode != AES.MODE_ECB:
    print('Only CBC and ECB mode supported...')
    sys.exit()

# 设置密钥长度
keySize = 32
# ivSize = 16 初始向量长度不变
ivSize = AES.block_size if mode == AES.MODE_CBC else 0

# 加密部分 ----------------------------------------------------------------------------------------------

# 加载本地图像，转成np矩阵
imageOrig = cv2.imread("000000000034.jpg")

# 输出图像大小
rowOrig, columnOrig, depthOrig = imageOrig.shape
print(imageOrig.shape)

# 检查图像的宽度是否低于图像加密的宽度限制
print("AES.block_size:"+str(AES.block_size))
minWidth = (AES.block_size + AES.block_size) // depthOrig + 1
print("minWidth:" + str(minWidth))
if columnOrig < minWidth:
    print('The minimum width of the image must be {} pixels, so that IV and padding can be stored in a single additional row!'.format(minWidth))
    sys.exit()

# 显示原始图像
cv2.imshow("Original image", imageOrig)
# 原始图像持续显示时间
cv2.waitKey()

# 将图像转化成字节
imageOrigBytes = imageOrig.tobytes()
print("imageOrigBytes:"+str(len(imageOrigBytes)))

# 加密
# 随机生成密钥key和初始向量IV
key = (b'a' * keySize)
iv = (b"a" * ivSize)
# 初始化AES加密器
cipher = AES.new(key, AES.MODE_CBC, iv) if mode == AES.MODE_CBC else AES.new(key, AES.MODE_ECB)
# 将字节数据进行填充，得到填充后的数据
imageOrigBytesPadded = pad(imageOrigBytes, AES.block_size)
# 得到密文
ciphertext = cipher.encrypt(imageOrigBytesPadded)

# bytes(s) 返回字节
# 填充的位数
paddedSize = len(imageOrigBytesPadded) - len(imageOrigBytes)
print('paddedSize:'+str(paddedSize))

void = columnOrig * depthOrig - ivSize - paddedSize
ivCiphertextVoid = iv + ciphertext + bytes(void)

# frombuffer将data以流的形式读入转化成ndarray对象
# 第一参数为stream,第二参数为返回值的数据类型，第三参数指定从stream的第几位开始读入
# data是字符串的时候，Python3默认str是Unicode类型，所以要转成bytestring在原str前加上
# 因为进行了数据填充，所有加密后的图像会比原图像多1行
imageEncrypted = np.frombuffer(ivCiphertextVoid, dtype=imageOrig.dtype).reshape(rowOrig + 1, columnOrig, depthOrig)

# 显示加密后的图像
cv2.imshow("Encrypted image", imageEncrypted)
cv2.waitKey()

# 保存加密后的图像
cv2.imwrite("topsecretEnc.bmp", imageEncrypted)
imageEncrypted = cv2.imread("topsecretEnc.bmp")
#
# 解密部分 ----------------------------------------------------------------------------------------------
#
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
decryptedImageBytes = unpad(decryptedImageBytesPadded, AES.block_size)

# 把字节转化成图像
decryptedImage = np.frombuffer(decryptedImageBytes, imageEncrypted.dtype).reshape(rowOrig, columnOrig, depthOrig)

# 显示解密后的图像
cv2.imshow("Decrypted Image", decryptedImage)
cv2.waitKey()

# 关闭所有窗口
cv2.destroyAllWindows()

from pyeclib.ec_iface import ECDriver
import random

# ===（1）参数设置===
k = 2           # 恢复原文件最少需要的分片数
m = 6           # 总共的分片数
p = 0.88703     # 保留正确分片的概率
q = 0.04416     # 增加无关分片的概率

# 初始化容错码
ec_driver = ECDriver(k=k, m=m-k, ec_type='reed_sol_van')

# 全局字典，用来存储所有文件的分片
shards_storage = {}

# ===（2）容错码编码===
def encode_document(id, doc_bytes):
    fragments = ec_driver.encode(doc_bytes)
    shards_storage[id] = fragments  # 存入全局字典

# ===（3）访问模式混淆===
def obfuscate_fragments(id):
    obfuscated = []
    target_fragments = shards_storage.get(id, [])

    # 其他文件的所有分片汇总
    other_fragments = []
    for other_id, fragments in shards_storage.items():
        if other_id != id:
            other_fragments.extend(fragments)

    # 以概率 p 返回正确分片
    for fragment in target_fragments:
        if random.random() < p:
            obfuscated.append(fragment)

    # 以概率 q 返回无关分片
    for fragment in other_fragments:
        if random.random() < q:
            obfuscated.append(fragment)

    return obfuscated

def decode_document(obfuscated):
    try:
        return ec_driver.decode(obfuscated)
    except Exception:
        return None

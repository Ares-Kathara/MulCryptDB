# 先安装：pip install translate
from translate import Translator

try:
    translator = Translator(to_lang="en", from_lang="zh")
    translation = translator.translate("你好，世界！")
    print(f"翻译结果: {translation}")
except Exception as e:
    print(f"错误: {e}")
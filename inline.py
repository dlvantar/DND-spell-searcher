# -*- coding: utf-8 -*-
"""把 spells.json 内联进 app.template.html，生成单文件版检索器。"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(BASE, "app.template.html")
DATA = os.path.join(BASE, "spells.json")
OUT = os.path.join(BASE, "..", "PHB法术检索器.html")

html = open(TEMPLATE, encoding="utf-8").read()
data = json.load(open(DATA, encoding="utf-8"))
# 紧凑序列化，并转义 </ 以免提前闭合 <script>
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

assert "/*__SPELL_DATA__*/" in html, "模板缺少数据占位符"
html = html.replace("/*__SPELL_DATA__*/", payload)
open(OUT, "w", encoding="utf-8").write(html)
print("wrote", os.path.normpath(OUT), len(html.encode("utf-8")) // 1024, "KB")

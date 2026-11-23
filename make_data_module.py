# -*- coding: utf-8 -*-
"""把 spells.json 压成 base64 数据模块，供桌面版随 exe 一起打包。"""
import base64
import json
import os
import zlib

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "spells.json")
OUT = os.path.join(BASE, "spells_data.py")

data = json.load(open(SRC, encoding="utf-8"))
raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
blob = base64.b64encode(zlib.compress(raw, 9)).decode("ascii")

with open(OUT, "w", encoding="utf-8") as f:
    f.write('# -*- coding: utf-8 -*-\n"""自动生成：玩家手册第 11 章法术数据（zlib + base64）。"""\n')
    f.write("import base64 as _b64\nimport json as _json\nimport zlib as _zlib\n\n")
    f.write("BLOB = (\n")
    for i in range(0, len(blob), 100):
        f.write('    "%s"\n' % blob[i:i + 100])
    f.write(")\n\n\n")
    f.write("def load():\n")
    f.write('    """解压并返回 spells.json 等价的数据。"""\n')
    f.write("    return _json.loads(_zlib.decompress(_b64.b64decode(BLOB)).decode(\"utf-8\"))\n")

print("raw", len(raw) // 1024, "KB ->", len(blob) // 1024, "KB base64")
print("wrote", OUT)

# -*- coding: utf-8 -*-
"""Build spells.json for the PHB spell searcher from the source PDF."""
import difflib
import json
import os
import re
import sys

import pymupdf
from pypinyin import lazy_pinyin

BASE = os.path.dirname(os.path.abspath(__file__))
# 用法: python build_data.py [PDF 路径]  （默认取仓库根目录里的那本手册）
PDF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    BASE, "..", "..", "5eDnD_玩家手册PHB_中译v1.72版.pdf")
OUT = os.path.join(BASE, "spells.json")

SCHOOLS = ["防护", "咒法", "预言", "附魔", "塑能", "幻术", "死灵", "变化"]
SCHOOL_EN = dict(zip(SCHOOLS, ["Abjuration", "Conjuration", "Divination", "Enchantment",
                               "Evocation", "Illusion", "Necromancy", "Transmutation"]))
SCHOOL_RE = "|".join(SCHOOLS)
LV_RE = r"(?:\d+|[０-９]+)\s*[环级换]|戏法"
HEADER_RE = re.compile(
    r"^\s*((?:" + LV_RE + r")\s*(?:" + SCHOOL_RE + r")(?:\s*（仪式）)?"
    r"|(?:" + SCHOOL_RE + r")\s*(?:(?:" + LV_RE + r")(?:\s*（仪式）)?)?)\s*$"
)
META_KEYS = ["施法时间", "施法距离", "法术成分", "持续时间"]

# the book's description headers omit the (ritual) tag for these, but the PHB marks
# them as rituals; keep rules-accurate data.
RITUAL_OVERRIDE = {"探知", "寻找陷阱", "寻路术"}

CLASSES = [("吟游诗人", "Bard"), ("牧师", "Cleric"), ("德鲁伊", "Druid"),
           ("圣武士", "Paladin"), ("游侠", "Ranger"), ("术士", "Sorcerer"),
           ("邪术师", "Warlock"), ("法师", "Wizard")]

# ---------------------------------------------------------------- tables
TABLES = [
    dict(spell="活化物件",
         start="活化物件属性资料Animated Object Statistics",
         end="被活化物件的AC、HP",
         title="活化物件属性资料 Animated Object Statistics",
         header=["体型", "HP", "AC", "攻击", "力量", "敏捷"],
         rows=[["微型", "20", "18", "命中+8，伤害1d4+4", "4", "18"],
               ["小型", "25", "16", "命中+6，伤害1d8+2", "6", "14"],
               ["中型", "40", "13", "命中+5，伤害2d6+1", "10", "12"],
               ["大型", "50", "10", "命中+6，伤害2d10+2", "14", "10"],
               ["巨型", "80", "10", "命中+8，伤害2d12+4", "18", "6"]]),
    dict(spell="困惑术",
         start="d10", end="受术生物在其每回合结束时可以在进行一次感知豁免",
         title=None, header=["d10", "行为"],
         rows=[["1", "该生物使用其所有移动力向一个随机方向移动。你可以掷一次d8并设定每个骰值代表的方向以决定其最终移动方向。该生物本回合不执行任何动作。"],
               ["2-6", "该生物本回合不移动也不执行任何动作。"],
               ["7-8", "该生物使用其动作对可触及范围内一个随机目标发动一次近战攻击。如果没有生物在其触及范围内，则该生物本回合什么都不做。"],
               ["9-10", "该生物本回合内可以正常的移动和行动。"]]),
    dict(spell="操控天气",
         start="降水Precipitation", end="气温Temperature",
         title="降水 Precipitation", header=["等级", "状况"],
         rows=[["1", "天晴 clear"], ["2", "薄云 light clouds"],
               ["3", "多云 overcast 或有雾 ground fog"],
               ["4", "有雨 rain，冰雹 hail 或有雪 snow"],
               ["5", "暴雨 torrential rain，冰暴 driving hail 或暴雪 blizzard"]])
    ,
    dict(spell="操控天气", start="气温Temperature", end="风势Wind",
         title="气温 Temperature", header=["等级", "状况"],
         rows=[["1", "酷热 unbearable heat"], ["2", "炎热 hot"], ["3", "暖和 warm"],
               ["4", "清凉 cool"], ["5", "寒冷 cold"], ["6", "极寒 arctic cold"]]),
    dict(spell="操控天气", start="风势Wind", end="警戒之箭Cordon of Arrows",
         title="风势 Wind", header=["等级", "状况"],
         rows=[["1", "无风 calm"], ["2", "和风 moderate wind"], ["3", "强风 strong wind"],
               ["4", "狂风 gale"], ["5", "暴风 storm"]]),
    dict(spell="造物术", start="材质", end="施展其他法术时，如果以这些创造物作为其材料成分",
         title=None, header=["材质", "持续时间"],
         rows=[["植物质 vegetable matter", "1 日"],
               ["石质 stone 或水晶 crystal", "12 小时"],
               ["贵金属 precious metals", "1 小时"],
               ["宝石 gems", "10 分钟"],
               ["精金 adamantine 或秘银 mithral", "1 分钟"]]),
    dict(spell="转生术", start="d100", end="转生后的生物保留其前生记忆和经验",
         title=None, header=["d100", "种族"],
         rows=[["01~04", "龙裔"], ["05~13", "丘陵矮人"], ["14~21", "山地矮人"],
               ["22~25", "黑暗精灵"], ["26~34", "高等精灵"], ["35~42", "木精灵"],
               ["43~46", "林侏儒"], ["47~52", "岩侏儒"], ["53~56", "半精灵"],
               ["57~60", "半兽人"], ["61~68", "轻足半身人"], ["69~76", "强魄半身人"],
               ["77~96", "人类"], ["97~00", "提夫林"]]),
    dict(spell="探知", start="了解程度", end="联系程度",
         title=None, header=["了解程度", "豁免调整值"],
         rows=[["二手信息（你曾经听说过受术者）", "+5"],
               ["直接信息（你曾经见过受术者）", "+0"],
               ["熟悉（你对受术者很了解）", "-5"]]),
    dict(spell="探知", start="联系程度", end="如果对方豁免成功",
         title=None, header=["联系程度", "豁免调整值"],
         rows=[["肖像或图像", "-2"], ["所有物或衣物", "-4"],
               ["身体部位，头发，指甲或类似物件", "-10"]]),
    dict(spell="传送术", start="熟悉程度", end="熟悉程度Familiarity",
         title=None, header=["熟悉程度", "遇难", "相似地区", "目标错误", "目标正确"],
         rows=[["永久法阵", "—", "—", "—", "01~100"],
               ["相关物件", "—", "—", "—", "01~100"],
               ["非常熟悉", "01~05", "06~13", "14~24", "25~100"],
               ["偶尔见过", "01~33", "34~43", "44~53", "54~100"],
               ["见过一次", "01~43", "44~53", "54~73", "74~100"],
               ["听过描述", "01~43", "44~53", "54~73", "74~100"],
               ["查无此地", "01~50", "51~100", "—", "—"]]),
]


def get_lines(pages):
    doc = pymupdf.open(PDF)
    out, page_of_line = [], []
    for pno in pages:
        for raw in doc[pno - 1].get_text().split("\n"):
            line = raw.rstrip()
            if re.fullmatch(r"\d{1,3}", line.strip()):
                continue
            out.append(line)
            page_of_line.append(pno)
    return out, page_of_line


def split_zh_en(name):
    m = re.search(r"[A-Za-z]", name)
    if m:
        i = m.start()
        zh, en = name[:i].strip().replace(" ", ""), re.sub(r"\s{2,}", " ", name[i:].strip())
        if zh and en:
            return zh, en
    return name.strip(), ""


def parse_spells():
    lines, pages = get_lines(range(211, 290))
    starts = []
    for i, l in enumerate(lines):
        if not l.strip():
            continue
        if HEADER_RE.match(l) and any("施法时间" in x for x in lines[i + 1:i + 6]):
            starts.append(i)

    # locate table line-blocks (on the raw line list)
    regions = {}                 # start index -> (end index, table dict)
    for t in TABLES:
        si = next((k for k, l in enumerate(lines) if l.strip().startswith(t["start"])), None)
        if si is None:
            print("!! table start not found:", t["start"], file=sys.stderr)
            continue
        ei = next((k for k in range(si + 1, len(lines))
                   if lines[k].strip().startswith(t["end"])), None)
        if ei is None:
            print("!! table end not found:", t["end"], file=sys.stderr)
            continue
        regions[si] = (ei, t)

    spells = []
    for idx, i in enumerate(starts):
        name = lines[i - 1].strip()
        if not re.search(r"[\u4e00-\u9fff]", name) and i - 2 >= 0:
            name = lines[i - 2].strip() + name
        name = re.sub(r"\s{2,}", " ", name).strip()

        hdr = lines[i].strip()
        m = re.search(r"(\d+|[０-９]+)\s*[环级换]", hdr)
        level = int(m.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))) if m else 0
        ritual = "仪式" in hdr
        school = next((s for s in SCHOOLS if s in hdr), "")

        if idx + 1 < len(starts):
            end = starts[idx + 1]
            nxt_name = 2 if not re.search(r"[\u4e00-\u9fff]", lines[end - 1].strip()) else 1
            end -= nxt_name
        else:
            end = len(lines)

        # metadata block: 4 labelled lines, which may wrap onto further lines
        meta = {}
        pos = i + 1
        while pos < end:
            st = lines[pos].strip()
            if not st:
                pos += 1
                continue
            key = next((k for k in META_KEYS if re.match("^" + k + r"\s*[：:；;]", st)), None)
            if key:
                meta[key] = re.sub("^" + key + r"\s*[：:；;]\s*", "", st)
                pos += 1
                continue
            if len(meta) == len(META_KEYS) or lines[pos].startswith("    "):
                break
            meta[list(meta)[-1]] += st      # continuation of the previous field
            pos += 1

        # description: paragraphs, tables, bullets
        paras, tables, skip_until = [], [], -1
        k = pos
        while k < end:
            if k <= skip_until:
                k += 1
                continue
            if k in regions:
                ei, t = regions[k]
                t = dict(t)
                t.pop("spell", None)
                t.pop("start", None)
                t.pop("end", None)
                tables.append(t)
                paras.append(f"@@TABLE{len(tables) - 1}@@")
                skip_until = ei - 1
                k = ei
                continue
            s = lines[k]
            txt = s.strip()
            if not txt:
                k += 1
                continue
            new_para = (s.startswith("    ") or s.startswith("\u3000") or not paras
                        or txt.startswith("•") or txt.startswith("◆")
                        or paras[-1].startswith("@@TABLE"))
            if new_para:
                paras.append(txt)
            else:
                paras[-1] += txt
            k += 1

        zh, en = split_zh_en(name)
        spells.append(dict(zh=zh, en=en, level=level, school=school,
                           schoolEn=SCHOOL_EN.get(school, ""),
                           ritual=ritual or zh in RITUAL_OVERRIDE,
                           meta=meta, desc="\n\n".join(paras), tables=tables,
                           page=pages[i]))
    return spells


def parse_class_lists(spells):
    lines, _ = get_lines(range(207, 212))
    texts = [l.strip() for l in lines]
    out = {}                     # class zh -> list of [level, name]
    cur_class, cur_level, in_lists = None, None, False
    cur = None
    for t in texts:
        if not t:
            continue
        if t.startswith("法术详述"):
            in_lists = False
            continue
        m = re.match(r"^(" + "|".join(c for c, _ in CLASSES) + r")法术", t)
        if m:
            cur_class = m.group(1)
            in_lists = True
            cur = None
            out.setdefault(cur_class, [])
            continue
        if not in_lists or cur_class is None:
            continue
        if t in ("Spells", "Spell"):
            continue
        m = re.fullmatch(r"(\d)\s*环(?:\s*戏法)?", t)
        if m:
            cur_level = int(m.group(1))
            continue
        if t == "戏法":
            cur_level = 0
            continue
        if HEADER_RE.match(t) and len(t) < 8:
            continue
        if t[0].isascii():
            if cur is not None:
                cur[1] += " " + t
            continue
        cur = [cur_level, t]
        out[cur_class].append(cur)

    known = spells
    index_zh = {s["zh"]: s for s in known}
    nz = {norm(s["zh"]): s for s in known}
    ne = {norm(s["en"]): s for s in known}

    unmatched = []
    for cls, items in out.items():
        for level, raw_item in items:
            zh, en = split_zh_en(raw_item)
            spell = index_zh.get(zh) or nz.get(norm(zh)) or ne.get(norm(en))
            if spell is None:
                cand = difflib.get_close_matches(norm(en), list(ne), n=1, cutoff=0.82)
                if cand:
                    spell = ne[cand[0]]
                else:
                    cand = difflib.get_close_matches(norm(zh), list(nz), n=1, cutoff=0.82)
                    if cand:
                        spell = nz[cand[0]]
            if spell is None:
                unmatched.append((cls, zh, en))
            else:
                spell.setdefault("classes", set()).add(cls)
    return out, unmatched


def norm(s):
    """Lower-case, drop punctuation/spaces; keep latin, digits and CJK."""
    s = s.lower().replace("／", "/").replace("＇", "'")
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", s)


def main():
    spells = parse_spells()
    print("spells:", len(spells), file=sys.stderr)

    out, unmatched = parse_class_lists(spells)
    print("class list items:", sum(len(v) for v in out.values()), file=sys.stderr)
    print("unmatched:", len(unmatched), file=sys.stderr)
    for u in unmatched:
        print("   ", u, file=sys.stderr)

    no_class = [s["zh"] for s in spells if not s.get("classes")]
    print("spells without class:", len(no_class), no_class[:20], file=sys.stderr)

    for s in spells:
        s["classes"] = sorted(s.get("classes", []), key=lambda c: [x for x, _ in CLASSES].index(c))
        s["pyc"] = lazy_pinyin(s["zh"])
        s["id"] = s["zh"]

    spells.sort(key=lambda s: (s["en"].lower(), s["zh"]))
    data = dict(source="D&D 5e 玩家手册 PHB 中译 v1.72", count=len(spells),
                classes=[c for c, _ in CLASSES], schools=SCHOOLS,
                spells=spells)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("written", OUT, file=sys.stderr)


if __name__ == "__main__":
    main()

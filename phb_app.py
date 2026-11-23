# -*- coding: utf-8 -*-
"""
PHB 法术检索器 · 桌面版
《龙与地下城》第五版《玩家手册》中译 v1.72 第 11 章 · 361 个法术的离线检索器。
单文件 exe 由 PyInstaller 打包，数据随程序内嵌。
"""
import json
import os
import re
import sys
import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk

try:
    import spells_data
except ImportError:                      # 开发时直接跑源码
    sys.path.insert(0, ".")
    import spells_data

APP_TITLE = "PHB 法术检索 · 玩家手册第 11 章"
APP_VERSION = "1.0"

# ---------------------------------------------------------------- palette
BG = "#f3eee4"
CARD = "#fffdf8"
CARD2 = "#faf6ee"
INK = "#221d17"
INK2 = "#4a4238"
MUTED = "#8b8172"
FAINT = "#a99d89"
LINE = "#e4dac6"
LINE2 = "#d6c9b0"
RED = "#b3261e"
GOLD = "#9a7b3f"
SEL = "#f5ecdb"
HOVER = "#f8f2e6"
CHIP_BG = "#fbf3e1"
CHIP_FG = "#7a5a1e"
SCHOOL_BG = "#f1f6fa"
SCHOOL_FG = "#42586b"
RIT_BG = "#f8f2fb"
RIT_FG = "#6b4b7a"
CLS_BG = "#f3f7ef"
CLS_FG = "#4d5a44"
UPCAST_BG = "#fbf6ea"
PAPER_EDGE = "#e9e2d4"


# ---------------------------------------------------------------- data index
def norm_en(s):
    out, mp = [], []
    for i, ch in enumerate(s):
        c = ch.lower()
        if ("a" <= c <= "z") or ("0" <= c <= "9"):
            out.append(c)
            mp.append(i)
    return "".join(out), mp


def all_indexes(hay, needle, limit=6):
    out, i = [], hay.find(needle)
    while i >= 0 and len(out) < limit:
        out.append((i, i + len(needle)))
        i = hay.find(needle, i + 1)
    return out


def pinyin_spans(toks, frm, to, initials):
    spans, pos = [], 0
    for i, t in enumerate(toks):
        ln = (1 if t else 0) if initials else len(t)
        if ln and pos + ln > frm and pos < to:
            spans.append([i, i + 1])
        pos += ln
    merged = []
    for sp in spans:
        if merged and merged[-1][1] == sp[0]:
            merged[-1][1] = sp[1]
        else:
            merged.append(sp)
    return [tuple(x) for x in merged]


class Index:
    def __init__(self, spells):
        self.spells = spells
        for s in spells:
            s["_en"], s["_enmap"] = norm_en(s["en"])
            toks = [t.lower() if re.fullmatch(r"[A-Za-z]+", t) else "" for t in s["pyc"]]
            s["_toks"] = toks
            s["_py"] = "".join(toks)
            s["_pyi"] = "".join(t[0] if t else "" for t in toks)
            s["_lvl"] = "戏法" if s["level"] == 0 else "%d环" % s["level"]

    def search(self, raw):
        q = (raw or "").strip()
        if not q:
            return [Match(s, 0, [], []) for s in self.spells]
        qn = norm_en(q)[0]
        ql = re.sub(r"[^a-z]", "", q.lower())
        out = []
        for s in self.spells:
            rank, zh, en = 99, [], []
            zi = s["zh"].find(q)
            if zi >= 0:
                zh = all_indexes(s["zh"], q)
                rank = 0 if zi == 0 else 1
            elif qn and qn in s["_en"]:
                ei = s["_en"].find(qn)
                k = ei
                while k >= 0 and len(en) < 6:
                    en.append((s["_enmap"][k], s["_enmap"][k + len(qn) - 1] + 1))
                    k = s["_en"].find(qn, k + 1)
                rank = 2 if ei == 0 else 3
            elif ql:
                pi = s["_py"].find(ql)
                ii = s["_pyi"].find(ql)
                if pi >= 0:
                    zh = pinyin_spans(s["_toks"], pi, pi + len(ql), False)
                    rank = 4 if pi == 0 else 5
                elif ii >= 0:
                    zh = pinyin_spans(s["_toks"], ii, ii + len(ql), True)
                    rank = 4 if ii == 0 else 5
            if rank < 99:
                out.append(Match(s, rank, zh, en))
        out.sort(key=lambda m: (m.rank, m.s["level"], len(m.s["zh"]), m.s["zh"]))
        return out


class Match:
    __slots__ = ("s", "rank", "zh", "en")

    def __init__(self, s, rank, zh, en):
        self.s, self.rank, self.zh, self.en = s, rank, zh, en


def chip_label(lvl):
    """把等级标签补成等宽 4 格（戏法 / 3环），保证整列对齐。"""
    pad = max(0, 4 - disp_width(lvl))
    return " " + lvl + " " * (1 + pad)


def disp_width(text):
    w = 0
    for ch in text:
        w += 2 if unicodedata_east_asian(ch) else 1
    return w


def unicodedata_east_asian(ch):
    import unicodedata
    return unicodedata.east_asian_width(ch) in ("W", "F")


# ---------------------------------------------------------------- app
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        data = spells_data.load()
        self.spells = data["spells"]
        self.spells.sort(key=lambda s: s["en"].lower())
        self.index = Index(self.spells)
        self.classes = data["classes"]
        self.schools = data["schools"]

        self.query = ""
        self.level = "all"
        self.school = "all"
        self.cls = "all"
        self.ritual_only = False
        self.results = []
        self.selected = None            # dict
        self.active = 0                 # index in results
        self.hover_line = 0

        self.title(APP_TITLE)
        self.configure(bg=BG)
        self.geometry("1180x780")
        self.minsize(940, 620)

        self._init_icon()
        self._init_fonts()
        self._init_styles()
        self._build_ui()
        self._bind_keys()

        self.apply_search("")
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            self.var.set(sys.argv[1])
        self.select(self.results[0].s if self.results else None, scroll_detail=True)
        self.after(120, self._first_layout)

    def _init_icon(self):
        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            ico = os.path.join(base, "app.ico")
            if os.path.exists(ico):
                self.iconbitmap(default=ico)
        except Exception:
            pass

    # ---------- fonts ----------
    def _init_fonts(self):
        fams = set(tkfont.families())

        def pick(*names):
            for n in names:
                if n in fams:
                    return n
            return "TkDefaultFont"

        ui = pick("微软雅黑", "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI")
        serif = pick("楷体", "KaiTi", "宋体", "SimSun", "Georgia")
        mono = pick("新宋体", "NSimSun", "宋体", "Consolas")
        self.f = {
            "ui": tkfont.Font(family=ui, size=10),
            "ui_sm": tkfont.Font(family=ui, size=9),
            "ui_xs": tkfont.Font(family=ui, size=8),
            "ui_big": tkfont.Font(family=ui, size=11),
            "input": tkfont.Font(family=ui, size=13),
            "serif": tkfont.Font(family=serif, size=16),
            "serif_big": tkfont.Font(family=serif, size=27),
            "serif_row": tkfont.Font(family=serif, size=12),
            "mono": tkfont.Font(family=mono, size=9),
            "mono_sm": tkfont.Font(family=mono, size=8),
        }
        self.f["serif_brand"] = tkfont.Font(family=serif, size=19)
        self.f["serif_row_b"] = tkfont.Font(family=serif, size=12)

    # ---------- ttk styles ----------
    def _init_styles(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TCombobox", fieldbackground=CARD, background=CARD, foreground=INK2,
                     arrowcolor=MUTED, bordercolor=LINE2, lightcolor=CARD, darkcolor=CARD,
                     padding=(8, 4))
        st.map("TCombobox",
               fieldbackground=[("readonly", CARD), ("active", CARD)],
               selectbackground=[("readonly", CARD)],
               selectforeground=[("readonly", INK2)],
               bordercolor=[("focus", "#c8a96e")])
        st.configure("TCheckbutton", background=BG, foreground=INK2, font=self.f["ui_sm"])
        st.map("TCheckbutton", background=[("active", BG)], foreground=[("active", INK)])
        st.configure("Vertical.TScrollbar", troughcolor=CARD, background=LINE2,
                     bordercolor=CARD, arrowcolor=CARD, darkcolor=LINE2, lightcolor=LINE2,
                     arrowsize=1, gripcount=0, width=9)
        st.map("Vertical.TScrollbar", background=[("active", "#cdbea3")])
        self.option_add("*TCombobox*Listbox.background", CARD)
        self.option_add("*TCombobox*Listbox.foreground", INK)
        self.option_add("*TCombobox*Listbox.selectBackground", SEL)
        self.option_add("*TCombobox*Listbox.selectForeground", INK)
        self.option_add("*TCombobox*Listbox.font", self.f["ui_sm"])

    # ---------- layout ----------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # ---- header
        head = tk.Frame(self, bg=BG)
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 0))
        head.grid_columnconfigure(2, weight=1)

        tk.Label(head, text="✦", bg=BG, fg=RED, font=self.f["serif"]).grid(row=0, column=0, sticky="w")
        tk.Label(head, text="法术检索", bg=BG, fg=INK, font=self.f["serif_brand"]).grid(
            row=0, column=1, sticky="w", padx=(8, 14))
        tk.Label(head, text="龙与地下城 5e · 玩家手册 PHB · 第 11 章 · %d 个法术" % len(self.spells),
                 bg=BG, fg=MUTED, font=self.f["ui_sm"]).grid(row=0, column=2, sticky="wsw", pady=(0, 4))

        # ---- search box
        wrap = tk.Frame(self, bg=BG)
        wrap.grid(row=1, column=0, sticky="ew", padx=24, pady=(14, 0))
        wrap.grid_columnconfigure(0, weight=1)

        self.box = tk.Frame(wrap, bg=CARD, highlightbackground=LINE2, highlightthickness=1)
        self.box.grid(row=0, column=0, sticky="ew")
        self.box.grid_columnconfigure(2, weight=1)

        self.icon = tk.Canvas(self.box, width=26, height=26, bg=CARD, highlightthickness=0)
        self.icon.grid(row=0, column=0, padx=(12, 0))
        self.icon.create_oval(6, 6, 16, 16, outline=MUTED, width=2)
        self.icon.create_line(15, 15, 20, 20, fill=MUTED, width=2, capstyle="round")

        self.var = tk.StringVar()
        self.entry = tk.Entry(self.box, textvariable=self.var, bd=0, bg=CARD, fg=INK,
                              insertbackground=INK, font=self.f["input"], highlightthickness=0)
        self.entry.grid(row=0, column=2, sticky="ew", padx=(6, 8), pady=11)
        self.entry.bind("<FocusIn>", self._on_entry_focus)
        self.entry.bind("<FocusOut>", self._on_entry_blur)
        self.var.trace_add("write", lambda *a: self._on_typed())

        self.placeholder = tk.Label(self.box, text="输入法术名的一部分：中文 / English / 拼音…",
                                    bg=CARD, fg=FAINT, font=self.f["input"])
        self.placeholder.place(x=48, rely=0.5, anchor="w")
        self.placeholder.bind("<Button-1>", lambda e: self.entry.focus_set())

        self.btn_clear = tk.Label(self.box, text="✕", bg=CARD, fg=MUTED, font=self.f["ui_sm"],
                                  cursor="hand2")
        self.btn_clear.bind("<Button-1>", lambda e: self.clear_query())
        self.btn_clear.bind("<Enter>", lambda e: self.btn_clear.configure(fg=INK))
        self.btn_clear.bind("<Leave>", lambda e: self.btn_clear.configure(fg=MUTED))

        self.hint = tk.Label(wrap, text="中文名 · 英文名 · 拼音全拼 · 拼音首字母（如 hqs → 火球术）都可搜，"
                                        "命中的字会标红", bg=BG, fg=MUTED, font=self.f["ui_xs"])
        self.hint.grid(row=1, column=0, sticky="w", pady=(6, 0))

        # ---- filters
        bar = tk.Frame(self, bg=BG)
        bar.grid(row=2, column=0, sticky="ew", padx=24, pady=(10, 10))
        bar.grid_columnconfigure(1, weight=1)

        chips = tk.Frame(bar, bg=BG)
        chips.grid(row=0, column=0, sticky="w")
        self.level_defs = [("all", "全部")] + [(i, "戏法" if i == 0 else "%d环" % i) for i in range(10)]
        self.chip_labels = {}
        for i, (val, text) in enumerate(self.level_defs):
            lb = tk.Label(chips, text=text, bg=CARD, fg=INK2, font=self.f["ui_sm"],
                          padx=10, pady=3, cursor="hand2",
                          highlightbackground=LINE2, highlightthickness=1)
            lb.grid(row=0, column=i, padx=(0, 5))
            lb.bind("<Button-1>", lambda e, v=val: self.set_level(v))
            self.chip_labels[val] = lb
        self._paint_chips()

        right = tk.Frame(bar, bg=BG)
        right.grid(row=0, column=2, sticky="e")

        self.school_var = tk.StringVar(value="全部学派")
        self.school_box = ttk.Combobox(right, textvariable=self.school_var, state="readonly",
                                       width=9, font=self.f["ui_sm"],
                                       values=["全部学派"] + self.schools)
        self.school_box.grid(row=0, column=0, padx=(0, 6))
        self.school_box.bind("<<ComboboxSelected>>", self._on_school)

        self.class_var = tk.StringVar(value="全部职业")
        self.class_box = ttk.Combobox(right, textvariable=self.class_var, state="readonly",
                                      width=10, font=self.f["ui_sm"],
                                      values=["全部职业"] + [c + "法术" for c in self.classes])
        self.class_box.grid(row=0, column=1, padx=(0, 10))
        self.class_box.bind("<<ComboboxSelected>>", self._on_class)

        self.ritual_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text="仅仪式", variable=self.ritual_var,
                        command=self._on_ritual).grid(row=0, column=2)

        # ---- main area
        main = tk.Frame(self, bg=BG)
        main.grid(row=4, column=0, sticky="nsew", padx=24, pady=(0, 20))
        main.grid_columnconfigure(0, minsize=396, weight=0)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # left: list
        left = tk.Frame(main, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self.count_lbl = tk.Label(left, text="", bg=CARD, fg=MUTED, font=self.f["ui_xs"],
                                  anchor="w", padx=14, pady=9)
        self.count_lbl.grid(row=0, column=0, sticky="ew")
        tk.Frame(left, bg=LINE, height=1).grid(row=0, column=0, sticky="sew")

        listwrap = tk.Frame(left, bg=CARD)
        listwrap.grid(row=1, column=0, sticky="nsew")
        listwrap.grid_columnconfigure(0, weight=1)
        listwrap.grid_rowconfigure(0, weight=1)

        self.list = tk.Text(listwrap, bg=CARD, bd=0, highlightthickness=0, wrap="none",
                            width=1, height=1, font=self.f["ui"], cursor="hand2",
                            padx=10, pady=6, spacing1=0, spacing3=0, takefocus=0)
        self.list.grid(row=0, column=0, sticky="nsew")
        sb1 = ttk.Scrollbar(listwrap, orient="vertical", command=self.list.yview,
                            style="Vertical.TScrollbar")
        sb1.grid(row=0, column=1, sticky="ns")
        self.list.configure(yscrollcommand=sb1.set)

        # right: detail
        right_pane = tk.Frame(main, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        right_pane.grid(row=0, column=1, sticky="nsew")
        right_pane.grid_rowconfigure(0, weight=1)
        right_pane.grid_columnconfigure(0, weight=1)

        self.detail = tk.Text(right_pane, bg=CARD, bd=0, highlightthickness=0, wrap="char",
                              width=1, height=1, font=self.f["ui"], padx=30, pady=24,
                              takefocus=1, spacing1=0, spacing3=0)
        self.detail.grid(row=0, column=0, sticky="nsew")
        sb2 = ttk.Scrollbar(right_pane, orient="vertical", command=self.detail.yview,
                            style="Vertical.TScrollbar")
        sb2.grid(row=0, column=1, sticky="ns")
        self.detail.configure(yscrollcommand=sb2.set)

        self._list_w = 0
        self._detail_w = 0
        self.list.bind("<Configure>", self._on_list_configure)
        self.detail.bind("<Configure>", self._on_detail_configure)
        self._init_text_tags()

        # ---- status bar
        self.status = tk.Label(self, text="", bg=BG, fg=MUTED, font=self.f["ui_xs"], anchor="w")
        self.status.grid(row=5, column=0, sticky="ew", padx=26, pady=(0, 6))

    def _on_list_configure(self, evt):
        if abs(evt.width - self._list_w) > 3:
            self._list_w = evt.width
            self.after_idle(self.render_list)

    def _on_detail_configure(self, evt):
        if abs(evt.width - self._detail_w) > 3:
            self._detail_w = evt.width
            self.after_idle(self.render_detail)

    def _init_text_tags(self):
        f = self.f
        L = self.list
        L.tag_configure("chip", background=CHIP_BG, foreground=CHIP_FG, font=f["mono_sm"])
        L.tag_configure("name", foreground=INK, font=f["serif_row"])
        L.tag_configure("hl", foreground=RED, font=f["serif_row_b"])
        L.tag_configure("en", foreground=MUTED, font=f["ui_xs"])
        L.tag_configure("hl_en", foreground=RED, font=f["ui_xs"])
        L.tag_configure("school", foreground=MUTED, font=f["ui_xs"])
        L.tag_configure("rowsel", background=SEL)
        L.tag_configure("rowhover", background=HOVER)
        L.tag_configure("space", font=f["ui_xs"])

        D = self.detail
        D.tag_configure("title", foreground=INK, font=f["serif_big"], spacing3=2)
        D.tag_configure("en", foreground=MUTED, font=f["ui_sm"])
        D.tag_configure("py", foreground=FAINT, font=f["mono_sm"])
        D.tag_configure("badge_lv", background=CHIP_BG, foreground=CHIP_FG, font=f["ui_xs"])
        D.tag_configure("badge_school", background=SCHOOL_BG, foreground=SCHOOL_FG, font=f["ui_xs"])
        D.tag_configure("badge_ritual", background=RIT_BG, foreground=RIT_FG, font=f["ui_xs"])
        D.tag_configure("badge_cls", background=CLS_BG, foreground=CLS_FG, font=f["ui_xs"])
        D.tag_configure("badge_page", foreground=MUTED, font=f["ui_xs"])
        D.tag_configure("rule", foreground=LINE, font=f["mono_sm"], spacing1=8, spacing3=12)
        D.tag_configure("mk", foreground=MUTED, font=f["ui_xs"])
        D.tag_configure("mv", foreground=INK, font=f["ui_sm"])
        D.tag_configure("body", foreground=INK2, font=f["ui"], lmargin1=26, lmargin2=0,
                        spacing3=9, justify="left")
        D.tag_configure("bullet", foreground=INK2, font=f["ui"], lmargin1=18, lmargin2=30,
                        spacing3=7)
        D.tag_configure("bmark", foreground=GOLD, font=f["ui"], lmargin1=18, lmargin2=30,
                        spacing3=7)
        D.tag_configure("bmark_w", foreground=GOLD, font=f["ui_sm"], lmargin1=14, lmargin2=26,
                        spacing3=5)
        D.tag_configure("upcast", foreground="#6f6555", font=f["ui_sm"], lmargin1=16, lmargin2=30,
                        spacing1=4, spacing3=10, background=UPCAST_BG)
        D.tag_configure("bar", foreground="#d8c49b", font=f["ui"])
        D.tag_configure("tblcap", foreground=INK, font=f["ui_sm"], spacing1=6, spacing3=4)
        D.tag_configure("table", foreground=INK2, font=f["mono"], spacing1=0, spacing3=0)
        D.tag_configure("thead", foreground=INK, font=f["mono"])
        D.tag_configure("tline", foreground=LINE2, font=f["mono_sm"])
        D.tag_configure("welcome_h", foreground=INK, font=f["serif"], spacing1=4, spacing3=10)
        D.tag_configure("welcome_p", foreground=INK2, font=f["ui_sm"], spacing3=8, lmargin1=0,
                        lmargin2=0)
        D.tag_configure("welcome_li", foreground=INK2, font=f["ui_sm"], lmargin1=14, lmargin2=26,
                        spacing3=5)
        D.tag_configure("welcome_src", foreground=MUTED, font=f["ui_xs"], spacing1=18)

    # ---------- small helpers ----------
    def _first_layout(self):
        self.render_list()
        self.render_detail()

    def _paint_chips(self):
        for val, lb in self.chip_labels.items():
            on = (val == self.level)
            lb.configure(bg=INK if on else CARD, fg="#fdfaf3" if on else INK2,
                         highlightbackground=INK if on else LINE2,
                         highlightcolor=INK if on else LINE2)

    def _on_entry_focus(self, _=None):
        self.box.configure(highlightbackground="#c8a96e", highlightcolor="#c8a96e")

    def _on_entry_blur(self, _=None):
        self.box.configure(highlightbackground=LINE2, highlightcolor=LINE2)

    def set_level(self, val):
        self.level = val
        self._paint_chips()
        self.refresh()

    def _on_school(self, _=None):
        self.school = "all" if self.school_var.get() == "全部学派" else self.school_var.get()
        self.refresh()

    def _on_class(self, _=None):
        v = self.class_var.get()
        self.cls = "all" if v == "全部职业" else v.replace("法术", "")
        self.refresh()

    def _on_ritual(self):
        self.ritual_only = bool(self.ritual_var.get())
        self.refresh()

    def clear_query(self):
        self.var.set("")
        self.entry.focus_set()

    # ---------- search ----------
    def _on_typed(self):
        self.query = self.var.get()
        self.after_idle(self.refresh)

    def refresh(self):
        self.apply_search(self.query)
        self.active = 0
        if self.results:
            self.select(self.results[0].s, scroll_detail=False)
        else:
            self.selected = None
        self.render_list()
        self.render_detail()

    def apply_search(self, q):
        rows = self.index.search(q)
        res = [m for m in rows if self._pass(m.s)]
        self.results = res
        self.placeholder.place_forget() if q else self.placeholder.place(
            x=48, rely=0.5, anchor="w")
        if q:
            self.btn_clear.place(relx=1.0, x=-14, rely=0.5, anchor="e")
        else:
            self.btn_clear.place_forget()

    def _pass(self, s):
        if self.level != "all" and s["level"] != self.level:
            return False
        if self.school != "all" and s["school"] != self.school:
            return False
        if self.cls != "all" and self.cls not in s["classes"]:
            return False
        if self.ritual_only and not s["ritual"]:
            return False
        return True

    # ---------- list rendering ----------
    def _fit(self, text, font, max_px):
        if max_px < 48:
            return ""
        if font.measure(text) <= max_px:
            return text
        ell = "…"
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + ell) <= max_px:
                lo = mid
            else:
                hi = mid - 1
        cut = text[:lo]
        if " " in cut.strip() and not cut.endswith(" "):
            cut = cut[:cut.rfind(" ")]
        return cut.rstrip() + ell

    def _insert_marked(self, text_widget, base_text, spans, base_tag, hl_tag):
        if not spans:
            text_widget.insert("end", base_text, base_tag)
            return
        prev = 0
        for a, b in spans:
            if a > prev:
                text_widget.insert("end", base_text[prev:a], base_tag)
            text_widget.insert("end", base_text[a:b], hl_tag)
            prev = b
        if prev < len(base_text):
            text_widget.insert("end", base_text[prev:], base_tag)

    def render_list(self):
        L = self.list
        L.configure(state="normal")
        L.delete("1.0", "end")
        width = max(L.winfo_width(), 300)
        pad = 26
        avail = width - pad

        # tab stop for the right-aligned school column
        school_w = self.f["ui_xs"].measure(" 幻术 · 仪式 ") + 4
        L.configure(tabs=())

        if not self.results:
            L.insert("end", "\n", "space")
            L.insert("end", "   没有找到匹配的法术。\n", "en")
            q = (self.query or "").strip()
            tip = "   试试只输入其中一个字，或改用英文名 / 拼音。"
            if q in self.schools:
                tip = "   「%s」是学派名 —— 可以用右上角的学派下拉筛选。" % q
            elif q in self.classes:
                tip = "   「%s」是职业名 —— 可以用右上角的职业下拉筛选。" % q
            L.insert("end", tip + "\n", "en")
            L.configure(state="disabled")
            self.count_lbl.configure(text="匹配 0 / %d 个法术" % len(self.spells))
            return

        name_font = self.f["serif_row"]
        en_font = self.f["ui_xs"]
        chip_w = max(self.f["mono_sm"].measure(chip_label(t)) for t in ("戏法", "9环"))
        space_px = max(1, self.f["ui_xs"].measure(" "))
        gap = self.f["ui"].measure("  ")

        for i, m in enumerate(self.results):
            s = m.s
            row_tag = "r%d" % i
            L.insert("end", chip_label(s["_lvl"]), ("chip", row_tag))
            L.insert("end", "  ")
            used = chip_w + gap

            rest = avail - used - school_w - 12
            zh_px = name_font.measure(s["zh"])
            en_txt = s["en"]
            if zh_px + gap + en_font.measure(en_txt) > rest:
                en_txt = self._fit(en_txt, en_font, max(40, rest - zh_px - gap))
            self._insert_marked(L, s["zh"], m.zh, ("name", row_tag), ("hl", row_tag))
            used += zh_px
            if en_txt:
                L.insert("end", "  ")
                self._insert_marked(L, en_txt, m.en if en_txt == s["en"] else [],
                                    ("en", row_tag), ("hl_en", row_tag))
                used += gap + en_font.measure(en_txt)
            right_txt = s["school"] + (" · 仪式" if s["ritual"] else "")
            pad_px = avail - used - self.f["ui_xs"].measure(right_txt)
            n_pad = max(1, int(pad_px / space_px)) if pad_px > 6 else 1
            L.insert("end", " " * n_pad + right_txt, ("school", row_tag))
            L.insert("end", "\n")

        L.tag_raise("rowsel")
        L.tag_raise("rowhover")
        L.tag_raise("hl")
        L.tag_raise("hl_en")

        self._paint_selection()
        L.configure(state="disabled")

        n = len(self.results)
        if not self.query:
            self.count_lbl.configure(text="全部 %d 个法术 · 按英文名排序" % n)
        else:
            self.count_lbl.configure(text="匹配 %d / %d 个法术" % (n, len(self.spells)))
        self.status.configure(text="↑↓ 在结果中移动 · Enter 进入正文 · Esc 清空 · Ctrl+Q 退出")

    def _row_line(self, idx):
        return idx + 1

    def _paint_selection(self):
        L = self.list
        L.tag_remove("rowsel", "1.0", "end")
        L.tag_remove("rowhover", "1.0", "end")
        if self.results and 0 <= self.active < len(self.results):
            ln = self._row_line(self.active)
            L.tag_add("rowsel", "%d.0" % ln, "%d.0" % (ln + 1))
        if self.hover_line:
            ln = self.hover_line
            if not (self.results and ln == self._row_line(self.active)):
                L.tag_add("rowhover", "%d.0" % ln, "%d.0" % (ln + 1))
        if self.results and 0 <= self.active < len(self.results):
            self.list.see("%d.0" % self._row_line(self.active))

    def _click_row(self, idx):
        if 0 <= idx < len(self.results):
            self.active = idx
            self.select(self.results[idx].s, scroll_detail=True)
            self._paint_selection()

    def _line_at(self, event):
        try:
            idx = self.list.index("@%d,%d" % (event.x, event.y))
        except tk.TclError:
            return 0
        return int(str(idx).split(".")[0])

    def _on_list_click(self, event):
        self._click_row(self._line_at(event) - 1)

    def _on_list_motion(self, event):
        ln = self._line_at(event)
        if ln != self.hover_line:
            self.hover_line = ln
            self._paint_selection()

    def _on_list_leave(self, _event=None):
        if self.hover_line:
            self.hover_line = 0
            self._paint_selection()

    # ---------- detail rendering ----------
    def select(self, spell, scroll_detail=False):
        if spell is None:
            return
        self.selected = spell
        if self.results:
            for i, m in enumerate(self.results):
                if m.s is spell:
                    self.active = i
                    break
        self.render_detail()
        if scroll_detail:
            self.detail.yview_moveto(0)

    def _badge(self, D, text, tag, last=False):
        D.insert("end", " %s " % text, tag)
        if not last:
            D.insert("end", "  ", "space")

    def render_detail(self):
        D = self.detail
        D.configure(state="normal")
        D.delete("1.0", "end")
        s = self.selected
        if s is None:
            self._render_welcome()
            D.configure(state="disabled")
            return

        # title
        D.insert("end", s["zh"] + "\n", "title")
        D.insert("end", s["en"], "en")
        py = " ".join(t for t in s["_toks"] if t)
        if py:
            D.insert("end", "    " + py, "py")
        D.insert("end", "\n")

        # badges
        self._badge(D, s["_lvl"], "badge_lv")
        self._badge(D, s["school"], "badge_school")
        if s["ritual"]:
            self._badge(D, "仪式", "badge_ritual")
        for c in s["classes"]:
            self._badge(D, c, "badge_cls")
        D.insert("end", "      PHB 第 %d 页" % s["page"], "badge_page")
        D.insert("end", "\n")
        pane0 = max(self.detail.winfo_width() - 70, 420)
        dash = max(1, self.f["mono_sm"].measure("─"))
        D.insert("end", "─" * max(20, int(pane0 / dash)) + "\n", "rule")

        # meta
        meta = s.get("meta") or {}
        pane = max(self.detail.winfo_width() - 70, 420)
        col2 = int(min(430, pane * 0.55))
        D.configure(tabs="112 %.0f %.0f" % (col2, col2 + 100))
        D.insert("end", "施法时间", "mk")
        D.insert("end", "\t" + (meta.get("施法时间") or "—"), "mv")
        D.insert("end", "\t施法距离", "mk")
        D.insert("end", "\t" + (meta.get("施法距离") or "—") + "\n", "mv")
        D.insert("end", "法术成分", "mk")
        D.insert("end", "\t" + (meta.get("法术成分") or "—") + "\n", "mv")
        D.insert("end", "持续时间", "mk")
        D.insert("end", "\t" + (meta.get("持续时间") or "—") + "\n", "mv")
        D.insert("end", "\n")
        D.configure(tabs=())

        # body
        for chunk in re.split(r"\n{2,}", s["desc"]):
            txt = chunk.strip()
            if not txt:
                continue
            mt = re.fullmatch(r"@@TABLE(\d+)@@", txt)
            if mt:
                tb = s["tables"][int(mt.group(1))] if int(mt.group(1)) < len(s["tables"]) else None
                if tb:
                    self._render_table(D, tb)
                continue
            if txt.startswith("•"):
                D.insert("end", "•  ", "bmark")
                D.insert("end", txt[1:].strip() + "\n", "bullet")
            elif txt.startswith("升环施法效应"):
                D.insert("end", "▎ " + txt + "\n", "upcast")
            else:
                D.insert("end", txt + "\n", "body")

        D.configure(state="disabled")

    def _render_table(self, D, tb):
        rows = [list(tb["header"])] + [list(r) for r in tb["rows"]]
        ncol = max(len(r) for r in rows)
        for r in rows:
            while len(r) < ncol:
                r.append("")

        # column widths in display units
        widths = []
        for c in range(ncol):
            widths.append(max(disp_width(r[c]) for r in rows))
        # last column may wrap
        pane_px = max(self.detail.winfo_width() - 80, 420)
        unit_px = max(1, self.f["mono"].measure("中")) / 2.0
        budget = int(pane_px / unit_px)
        fixed = sum(widths[:-1]) + 3 * (ncol - 1)
        last_max = max(10, budget - fixed)
        if widths[-1] > last_max:
            widths[-1] = last_max

        if tb.get("title"):
            D.insert("end", tb["title"] + "\n", "tblcap")

        def emit_row(cells, tag="table"):
            first = True
            wrapped = wrap_cells(cells, widths)
            for idx, line_cells in enumerate(wrapped):
                for ci, cell in enumerate(line_cells):
                    if cell is not None:
                        D.insert("end", cell)
                    if ci < ncol - 1:
                        pad = widths[ci] - disp_width(line_cells[ci] or "")
                        D.insert("end", " " * (pad + 2))
                D.insert("end", "\n", tag)
                first = False

        emit_row(rows[0], "thead")
        total = sum(widths) + 2 * (ncol - 1)
        D.insert("end", "─" * total + "\n", "tline")
        for r in rows[1:]:
            emit_row(r)
        D.insert("end", "\n")

    def _render_welcome(self):
        D = self.detail
        D.insert("end", "输入法术名的一部分即可开始\n", "welcome_h")
        D.insert("end", "这本书第 11 章按字母序列出了全部法术。在搜索框里敲下任意片段 —— 一个汉字、几个字母、"
                        "一段拼音都行，左侧会列出所有可能的法术，命中的字以红色标出。\n", "welcome_p")
        D.insert("end", "\n")
        for a, b in [("中文名 ", "火 → 火球术、火焰箭、火墙术…"),
                     ("英文名 ", "wall of → 力场墙、火墙术、冰墙术…"),
                     ("拼音全拼", "huoqiu → 火球术"),
                     ("拼音首字母", "hqs → 火球术"),
                     ("筛选", "按环阶、学派、职业逐层收窄结果")]:
            D.insert("end", "•  " + a, "bmark_w")
            D.insert("end", "    " + b + "\n", "welcome_li")
        D.insert("end", "\n数据来源：《玩家手册》中译 v1.72，第 11 章（第 211–289 页），共 %d 个法术。"
                 % len(self.spells), "welcome_src")

    # ---------- keys ----------
    def _bind_keys(self):
        self.entry.bind("<Down>", lambda e: self._move(1))
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Escape>", lambda e: self._on_esc())
        self.bind("<Control-f>", lambda e: (self.entry.focus_set(), self.entry.select_range(0, "end")))
        self.bind("<Control-q>", lambda e: self.destroy())
        self.bind("<F1>", lambda e: self._about())
        self.list.bind("<Button-4>", lambda e: self.list.yview_scroll(-2, "units"))
        self.list.bind("<Button-5>", lambda e: self.list.yview_scroll(2, "units"))
        self.list.bind("<MouseWheel>", lambda e: self.list.yview_scroll(int(-e.delta / 120) * 2, "units"))
        self.list.bind("<Button-1>", self._on_list_click)
        self.list.bind("<Motion>", self._on_list_motion)
        self.list.bind("<Leave>", self._on_list_leave)

    def _move(self, delta):
        if not self.results:
            return
        self.active = max(0, min(self.active + delta, len(self.results) - 1))
        self.select(self.results[self.active].s, scroll_detail=False)
        self._paint_selection()

    def _on_return(self, _=None):
        if self.results:
            self.select(self.results[self.active].s, scroll_detail=True)
            self.detail.focus_set()
            self.detail.yview_moveto(0)

    def _on_esc(self):
        if self.var.get():
            self.clear_query()
        else:
            self.detail.focus_set()

    def _about(self):
        messagebox.showinfo(
            "关于",
            "PHB 法术检索器 %s\n\n"
            "《龙与地下城》第五版《玩家手册》中译 v1.72\n"
            "第 11 章全部 %d 个法术的离线检索工具。\n\n"
            "数据版权归原作者与译者所有，仅供个人跑团查阅。" % (APP_VERSION, len(self.spells)))

    # ---------- misc ----------
    def on_resize(self, _evt=None):
        self.render_list()


def wrap_cells(cells, widths):
    """按列宽折行（末列可折，其余列不折）。返回多行单元格列表。"""
    out = [list(cells)]
    last = len(cells) - 1
    if widths[last] <= 0:
        return out
    line = list(cells)
    rest = line[last]
    if disp_width(rest) <= widths[last]:
        return out
    lines = []
    cur = ""
    for ch in rest:
        if disp_width(cur + ch) > widths[last]:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    out = []
    for i, part in enumerate(lines):
        row = [""] * len(cells)
        if i == 0:
            for j in range(last):
                row[j] = cells[j]
        row[last] = part
        out.append(row)
    return out


def main():
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = App()
    app.bind("<Configure>", lambda e: app.on_resize() if e.widget is app else None)
    app.mainloop()


if __name__ == "__main__":
    main()

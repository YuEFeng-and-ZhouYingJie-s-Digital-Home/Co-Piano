"""
tonnetz_kg.py — 钢琴乐理知识图谱(L4 LLM 反馈的前置,对位 Libretto / Tonnetz 思路)

设计:
- 节点类型: Note(音级) / Chord(和弦) / Key(调性) / Period(时期) / Composer(作曲家) / Piece(作品) / Progression(进行)
- 边类型: contains / leads_to / belongs_to / typical_of / composed_by / in_period
- 核心数据结构:邻接表 + 查询函数

为 LLM 反馈生成 RAG 用:
- 输入:用户弹的当前小节 + 错音
- 查询:这段常见错误模式 + 时期风格建议
- 返回:自然语言解释给 LLM 用

知识范围(初期,后续可扩展):
- 12 个音级 (C, C#, D, ..., B)
- 7 个三和弦 (I, ii, iii, IV, V, vi, vii°)
- 12 个调性 (C, G, D, A, E, B, F#, F, Bb, Eb, Ab, Db)
- 3 个时期(巴洛克/古典/浪漫)
- 5 个作曲家(每个时期代表)
- 5 首示范作品
- 10 个常见和声进行
- Tonnetz 图(12 音级,3 种关系:五度/大三度/小三度)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional


# === 基础数据 ===

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# 相对小调:把小调 i 用同名大调的 vi 表示,故 24 调 = 12 大调 + 12 小调

# 12 大调,顺序按五度圈
MAJOR_KEYS = ["C", "G", "D", "A", "E", "B", "F#", "F", "Bb", "Eb", "Ab", "Db"]
MINOR_KEYS = [k + "m" for k in MAJOR_KEYS]

# 三和弦功能(罗马数字)
ROMAN_NUMERALS = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]

# 时期
PERIODS = ["Baroque", "Classical", "Romantic"]

# 作曲家(每个时期 1-2 个代表)
COMPOSERS = {
    "Bach": ("Baroque", "1685-1750"),
    "Handel": ("Baroque", "1685-1759"),
    "Mozart": ("Classical", "1756-1791"),
    "Beethoven": ("Classical", "1760-1827"),
    "Chopin": ("Romantic", "1810-1849"),
    "Liszt": ("Romantic", "1811-1886"),
    "Schumann": ("Romantic", "1810-1856"),
}

# 示范作品(初学者常用)
PIECES = [
    {"name": "Prelude in C Major", "composer": "Bach", "key": "C", "period": "Baroque", "difficulty": 1, "form": "binary", "style_notes": "全音符级进,16 小节,和声极简,要均匀触键"},
    {"name": "Minuet in G", "composer": "Bach", "key": "G", "period": "Baroque", "difficulty": 2, "form": "AB", "style_notes": "三拍子优雅,带装饰音,弱起注意"},
    {"name": "Sonata K.545 1st Mvt", "composer": "Mozart", "key": "C", "period": "Classical", "difficulty": 3, "form": "sonata", "style_notes": "清晰结构,主-属-主对话,触键颗粒感"},
    {"name": "Für Elise", "composer": "Beethoven", "key": "a", "period": "Classical", "difficulty": 4, "form": "rondo", "style_notes": "A 段 a 小调,带弱起小节,主题标志性"},
    {"name": "Nocturne Op.9 No.2", "composer": "Chopin", "key": "Eb", "period": "Romantic", "difficulty": 5, "form": "ternary", "style_notes": "12/8 拍,左手持续低音,右手如歌,踏板要讲究"},
    {"name": "Étude Op.10 No.3 'Tristesse'", "composer": "Chopin", "key": "E", "period": "Romantic", "difficulty": 6, "form": "through-composed", "style_notes": "legato 连奏,情感深沉,音阶跑动要均匀"},
    {"name": "Liebestraum No.3", "composer": "Liszt", "key": "Ab", "period": "Romantic", "difficulty": 6, "form": "ABA", "style_notes": "多声部织体,踏板频繁,主旋律在中声部"},
    {"name": "Träumerei", "composer": "Schumann", "key": "F", "period": "Romantic", "difficulty": 4, "form": "song", "style_notes": "梦幻气质,弱奏为主,和声色彩丰富"},
]

# 常见和声进行
PROGRESSIONS = {
    "I-IV-V-I": "完美的古典终止,用于稳定段落",
    "I-V-vi-IV": "流行进行,19 世纪后期也常见(《Let It Be》) ",
    "I-vi-IV-V": "50 年代进行,清新,莫扎特常用",
    "ii-V-I": "爵士/古典核心进行,转调的桥梁",
    "I-V/V-V": "属七的属七,贝多芬发展段常用",
    "i-iv-V-i": "小调终止,巴赫小调作品主结构",
    "I-bVII-IV-I": "混合利底亚,浪漫时期色彩和弦",
    "I-vi-ii-V": "循环进行,常用作段落终止",
    "vi-IV-I-V": "悲伤但又上行,肖邦夜曲常用",
    "bVI-bVII-I": "弗里几亚,莫扎特土耳其进行常用",
}

# Tonnetz:12 音级之间的三种基本关系
# 5 度(完全五度,7 半音)、3 度(大三度,4 半音)、小三度(3 半音)
def build_tonnetz() -> dict:
    """Tonnetz:返回 (pc1, pc2) -> (关系名, 半音数)"""
    g = {}
    for pc1 in range(12):
        for pc2 in range(12):
            if pc1 == pc2:
                continue
            d = (pc2 - pc1) % 12
            if d == 7:  # 完全五度
                g[(pc1, pc2)] = ("P5", 7)
            elif d == 5:  # 完全四度
                g[(pc1, pc2)] = ("P4", 5)
            elif d == 4:  # 大三度
                g[(pc1, pc2)] = ("M3", 4)
            elif d == 3:  # 小三度
                g[(pc1, pc2)] = ("m3", 3)
            elif d == 8:  # 小六度
                g[(pc1, pc2)] = ("m6", 8)
            elif d == 9:  # 大六度
                g[(pc1, pc2)] = ("M6", 9)
    return g

TONNETZ = build_tonnetz()


# === KG 节点和边 ===

@dataclass
class Node:
    id: str
    type: str  # note/chord/key/period/composer/piece/progression
    attrs: dict = field(default_factory=dict)

@dataclass
class Edge:
    src: str
    dst: str
    rel: str  # contains / leads_to / belongs_to / typical_of / composed_by / in_period
    weight: float = 1.0


class MusicKG:
    """简单乐理 KG(纯 Python,无需图数据库)"""
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self._build()

    def _add(self, id: str, type: str, **attrs):
        self.nodes[id] = Node(id=id, type=type, attrs=attrs)
        return self.nodes[id]

    def _link(self, src: str, dst: str, rel: str, weight: float = 1.0):
        self.edges.append(Edge(src, dst, rel, weight))

    def _build(self):
        # 1. Note 节点(12 音级)
        for i, name in enumerate(NOTE_NAMES):
            self._add(f"note:{name}", "note", pc=i, name=name)

        # 2. Key 节点(24 调)
        for k in MAJOR_KEYS:
            self._add(f"key:{k}", "key", name=k, mode="major")
        for k in MINOR_KEYS:
            self._add(f"key:{k}", "key", name=k, mode="minor")

        # 3. Chord 节点(每个调 7 个罗马数字级)
        for k in MAJOR_KEYS + MINOR_KEYS:
            for r in ROMAN_NUMERALS:
                self._add(f"chord:{k}:{r}", "chord", key=k, roman=r)

        # 4. Period 节点
        for p in PERIODS:
            self._add(f"period:{p}", "period", name=p)

        # 5. Composer 节点
        for name, (period, dates) in COMPOSERS.items():
            n = self._add(f"composer:{name}", "composer", name=name, dates=dates)
            self._link(n.id, f"period:{period}", "in_period")

        # 6. Piece 节点
        for p in PIECES:
            n = self._add(f"piece:{p['name']}", "piece", **p)
            self._link(n.id, f"composer:{p['composer']}", "composed_by")
            self._link(n.id, f"period:{p['period']}", "in_period")
            self._link(n.id, f"key:{p['key']}", "in_key")

        # 7. Progression 节点
        for prog, desc in PROGRESSIONS.items():
            self._add(f"progression:{prog}", "progression", name=prog, desc=desc)

        # 8. 关键边: 时期 → 风格
        self._add("style:Baroque", "style", name="Baroque",
                  desc="通奏低音主导,对位严密,装饰音即兴,常用羽管键琴音色")
        self._add("style:Classical", "style", name="Classical",
                  desc="清晰句法,主-属调对话,动机发展,力度对比鲜明")
        self._add("style:Romantic", "style", name="Romantic",
                  desc="情感表达自由,和声色彩丰富,踏板讲究,织体复杂")
        for p in PERIODS:
            self._link(f"style:{p}", f"period:{p}", "typical_of")

        # 9. 边: 时期 → 常见错误
        self._add("err:Baroque:ornament", "error", period="Baroque", name="装饰音不规范",
                  desc="巴洛克装饰音(trill/mordent)无固定时值,需依风格加装饰")
        self._add("err:Baroque:voice", "error", period="Baroque", name="声部独立差",
                  desc="对位作品各声部须独立,常被压成单层旋律")
        self._add("err:Classical:articulation", "error", period="Classical", name="触键不清晰",
                  desc="古典奏鸣曲要求颗粒触键(staccato/legato 严格)")
        self._add("err:Classical:rhythm", "error", period="Classical", name="节奏自由过度",
                  desc="古典风格不应有太多 rubato,需稳定拍感")
        self._add("err:Romantic:pedal", "error", period="Romantic", name="踏板滥用",
                  desc="浪漫作品踏板频繁,初学者常踩太长导致和声浑浊")
        self._add("err:Romantic:dynamic", "error", period="Romantic", name="力度无变化",
                  desc="浪漫派需大幅力度对比,常被弹成单一力度")

        for eid in self.nodes:
            if eid.startswith("err:"):
                _, period, _ = eid.split(":")
                self._link(eid, f"period:{period}", "typical_of")

    # === 查询函数 ===

    def get_style_for_period(self, period: str) -> str:
        n = self.nodes.get(f"style:{period}")
        return n.attrs.get("desc", "") if n else ""

    def get_period_errors(self, period: str) -> list[dict]:
        out = []
        for eid, n in self.nodes.items():
            if n.type == "error" and n.attrs.get("period") == period:
                out.append({"name": n.attrs["name"], "desc": n.attrs["desc"]})
        return out

    def get_pieces_by_period(self, period: str, max_difficulty: int = 6) -> list[dict]:
        out = []
        for n in self.nodes.values():
            if n.type == "piece" and n.attrs.get("period") == period and n.attrs.get("difficulty", 99) <= max_difficulty:
                out.append(n.attrs)
        return out

    def suggest_practice_piece(self, current_difficulty: int, period: Optional[str] = None) -> list[dict]:
        """根据用户当前水平,推荐下一阶练习曲目"""
        candidates = []
        for n in self.nodes.values():
            if n.type != "piece":
                continue
            diff = n.attrs.get("difficulty", 99)
            if abs(diff - current_difficulty) > 1 or diff < current_difficulty:
                continue
            if period and n.attrs.get("period") != period:
                continue
            candidates.append(n.attrs)
        return candidates[:5]

    def explain_progression(self, prog: str) -> str:
        n = self.nodes.get(f"progression:{prog}")
        return n.attrs.get("desc", "未知进行") if n else "未知进行"

    def tonnetz_path(self, from_pc: int, to_pc: int) -> list[tuple[str, int]]:
        """Tonnetz 上从 from_pc 到 to_pc 的最短关系链(贪心)"""
        if from_pc == to_pc:
            return []
        path = []
        cur = from_pc
        while cur != to_pc:
            d = (to_pc - cur) % 12
            if d == 7: rel, step = "P5", 7
            elif d == 5: rel, step = "P4", -5
            elif d == 4: rel, step = "M3", 4
            elif d == 3: rel, step = "m3", 3
            elif d == 8: rel, step = "m6", -8
            elif d == 9: rel, step = "M6", -9
            elif d == 2: rel, step = "M2", 2
            elif d == 1: rel, step = "m2", 1
            elif d == 10: rel, step = "m7", -10
            elif d == 11: rel, step = "M7", -11
            elif d == 6: rel, step = "TT", 6  # 三全音
            else: rel, step = "?", d
            path.append((rel, step))
            cur = (cur + step) % 12
            if len(path) > 6:
                break
        return path

    def save(self, path: str = "notes/kg_export.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        out = {
            "n_nodes": len(self.nodes),
            "n_edges": len(self.edges),
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges],
        }
        Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def summary(self) -> dict:
        types = {}
        for n in self.nodes.values():
            types[n.type] = types.get(n.type, 0) + 1
        return {"n_nodes": len(self.nodes), "n_edges": len(self.edges), "node_types": types}


# === 演示 / 自检 ===
def demo():
    kg = MusicKG()
    s = kg.summary()
    print(f"KG 总览: {s['n_nodes']} 节点, {s['n_edges']} 边")
    print(f"节点类型: {s['node_types']}")

    print("\n[1] 巴洛克风格描述:")
    print(kg.get_style_for_period("Baroque"))

    print("\n[2] 浪漫时期常见错误:")
    for e in kg.get_period_errors("Romantic"):
        print(f"  - {e['name']}: {e['desc']}")

    print("\n[3] 当前难度 2 → 推荐练习曲目:")
    for p in kg.suggest_practice_piece(2):
        print(f"  - {p['name']} ({p['composer']}, 难度{p['difficulty']})")

    print("\n[4] 和声进行 ii-V-I 解释:")
    print(kg.explain_progression("ii-V-I"))

    print("\n[5] Tonnetz 路径: C → E (大三度):")
    print(kg.tonnetz_path(0, 4))
    print("Tonnetz 路径: C → G (五度):")
    print(kg.tonnetz_path(0, 7))

    print("\n[6] 导出 KG...")
    p = kg.save("/Users/yuefeng/.mavis/agents/mavis/workspace/piano-ai-corpus/notes/kg_export.json")
    print(f"  -> {p}")


if __name__ == "__main__":
    demo()

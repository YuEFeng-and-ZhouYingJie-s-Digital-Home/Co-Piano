"""
bandit_recommend.py — Contextual Bandit 推荐算法(L3 自适应推荐核心)

对位论文:
- 2501.10222 Integrated Expressive Piano(综合表现力 + 自适应)
- 2509.08800 PianoVAM(多模态表现力数据集,可用于 bandit 训练)

设计:
- 状态(context):当前用户 cluster_id + 曲目的 8 维特征
- 动作(arms):候选练习曲目(从 KG 中按难度递进筛)
- 奖励(reward):用户练新曲后的 score 提升
- 算法:UCB(Upper Confidence Bound) — 平衡探索与利用
  - 利用:推荐历史上表现好的
  - 探索:推荐不确定的(从未或很少推荐过的)

简化版(无真实数据):
- 用 cluster 画像作为状态(5 种之一)
- 用 KG 候选曲目作为动作
- 用"难度匹配"启发式作为奖励
- 历史推荐存 JSON,持续学习

应用:
- copiano.py --recommend(基于历史推荐下一首)
- copiano.py --update-history(用户练完更新奖励)
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from tonnetz_kg import PIECES  # noqa


# UCB 参数
UCB_C = 1.4  # 探索常数(越高越鼓励探索)


def get_candidate_pieces(current_piece: str, current_difficulty: int, period: Optional[str] = None) -> list[dict]:
    """根据用户当前水平,生成候选下一首"""
    candidates = []
    for p in PIECES:
        if p["name"] == current_piece:
            continue
        if period and p["period"] != period:
            continue
        # 难度匹配:当前 ± 1,优先 +1(略难)
        diff = p["difficulty"] - current_difficulty
        if diff < 0 or diff > 2:
            continue
        candidates.append(p)
    # 按难度递增排序
    candidates.sort(key=lambda x: x["difficulty"])
    return candidates


class ContextualBandit:
    """Contextual Bandit 推荐器
    状态 = cluster_id (0-4)
    动作 = candidate piece index
    奖励 = score 提升 + 错音减少 + 难度匹配
    """

    def __init__(self, history_path: str = "/tmp/copiano_bandit_history.json"):
        self.history_path = Path(history_path)
        self.history = self._load()
        # 状态-动作计数:Q[state][action] = count
        self.counts = {}  # {state: {action: count}}
        self.rewards = {}  # {state: {action: total_reward}}

    def _load(self) -> list:
        if self.history_path.exists():
            try:
                return json.loads(self.history_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save(self):
        self.history_path.write_text(json.dumps(self.history, indent=2, ensure_ascii=False), encoding="utf-8")

    def _ensure_state(self, state: int):
        if state not in self.counts:
            self.counts[state] = {}
            self.rewards[state] = {}

    def update(self, state: int, action: int, reward: float):
        """更新状态-动作对的计数和奖励"""
        self._ensure_state(state)
        self.counts[state].setdefault(action, 0)
        self.rewards[state].setdefault(action, 0.0)
        self.counts[state][action] += 1
        self.rewards[state][action] += reward
        # 存历史
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "state": state,
            "action": action,
            "reward": reward,
        })
        self._save()

    def ucb_score(self, state: int, action: int, total_pulls: int) -> float:
        """UCB 评分:利用 + 探索"""
        n = self.counts.get(state, {}).get(action, 0)
        if n == 0:
            return float("inf")  # 未拉过的优先
        avg = self.rewards[state][action] / n
        # 探索项:c * sqrt(ln(N) / n)
        bonus = UCB_C * math.sqrt(math.log(max(total_pulls, 2)) / n)
        return avg + bonus

    def recommend(self, state: int, candidates: list[dict], top_k: int = 3) -> list[dict]:
        """推荐 top_k 个候选
        返回:[(piece, score, action_index), ...]
        """
        self._ensure_state(state)
        total_pulls = sum(self.counts[state].values()) + 1
        scored = []
        for i, c in enumerate(candidates):
            score = self.ucb_score(state, i, total_pulls)
            scored.append((c, score, i))
        scored.sort(key=lambda x: -x[1])  # 降序
        return scored[:top_k]

    def save_model(self, path: str = "/tmp/copiano_bandit_model.json"):
        model = {
            "counts": self.counts,
            "rewards": self.rewards,
            "n_updates": len(self.history),
        }
        Path(path).write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_model(self, path: str = "/tmp/copiano_bandit_model.json"):
        if Path(path).exists():
            m = json.loads(Path(path).read_text(encoding="utf-8"))
            self.counts = m.get("counts", {})
            self.rewards = m.get("rewards", {})


# Cluster → 偏好映射
CLUSTER_TO_PREF = {
    0: {"difficulty_bias": 0, "style_bias": "Baroque"},   # 音准薄弱型:继续同难度
    1: {"difficulty_bias": -1, "style_bias": None},          # 节奏不稳型:降难度
    2: {"difficulty_bias": 1, "style_bias": "Romantic"},   # 表现力缺失:升难度练浪漫派
    3: {"difficulty_bias": -2, "style_bias": None},         # 全面待提升:降 2 难度
    4: {"difficulty_bias": 1, "style_bias": None},          # 良好可精进:升难度
}


def recommend_next_piece(current_piece: str, current_difficulty: int, cluster_id: int,
                         period: Optional[str] = None, top_k: int = 3) -> list[dict]:
    """主函数:基于 cluster + UCB 推荐下一首
    Returns: [{piece, score, reason}, ...]
    """
    pref = CLUSTER_TO_PREF.get(cluster_id, CLUSTER_TO_PREF[4])
    target_difficulty = max(1, current_difficulty + pref["difficulty_bias"])
    target_period = period or pref.get("style_bias")

    candidates = get_candidate_pieces(current_piece, target_difficulty, target_period)
    if not candidates:
        candidates = get_candidate_pieces(current_piece, current_difficulty)

    bandit = ContextualBandit()
    bandit.load_model()
    recs = bandit.recommend(cluster_id, candidates, top_k=top_k)

    out = []
    for piece, score, action in recs:
        reason = f"基于 cluster {cluster_id} ({pref}) 匹配难度 {piece['difficulty']} {piece['period']}"
        out.append({
            "piece": piece["name"],
            "composer": piece["composer"],
            "difficulty": piece["difficulty"],
            "period": piece["period"],
            "ucb_score": round(score, 3) if score != float("inf") else "inf",
            "reason": reason,
        })
    return out


def main():
    """demo:5 个 cluster_id 的推荐"""
    print("=" * 60)
    print("Contextual Bandit 推荐 demo")
    print("=" * 60)
    for cid in range(5):
        print(f"\n--- Cluster {cid} ---")
        recs = recommend_next_piece(
            current_piece="Minuet in G",
            current_difficulty=2,
            cluster_id=cid,
            top_k=3,
        )
        for r in recs:
            print(f"  {r['piece']} ({r['composer']}, {r['difficulty']}, {r['period']}) - score {r['ucb_score']} - {r['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

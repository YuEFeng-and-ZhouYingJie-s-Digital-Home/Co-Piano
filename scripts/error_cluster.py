"""
error_cluster.py — 错误模式聚类(L3 自适应推荐第一步)

对位论文:
- 2501.10222 Integrated Expressive Piano(综合错误分析)
- 2511.03425 SyMuPe(表现力错误聚类)

设计:
- 输入:多首曲子的评估结果(eval_pitch 数组)
- 特征工程:每首提取 8 维特征向量
  - pitch_accuracy, timing_std, timing_mean, velocity_corr
  - n_pitch_errors, n_timing_outliers, n_velocity_issues
  - period(Baroque=0, Classical=1, Romantic=2 编码)
- 聚类:KMeans(K 自动用 silhouette score 选)
  或 HDBSCAN(免预设 K,适合噪声多)
- 输出:每个曲子的 cluster_id + 错误画像 + 推荐练习

应用:
- 知道学生"经常犯同一类错"(聚类)
- 推荐类似练习(同 cluster 的曲子)
- 跟踪进步(从 cluster A → cluster B)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

try:
    import hdbscan
    HAS_HDBSCAN = True
except ImportError:
    HAS_HDBSCAN = False


# 错误画像 — 给每个 cluster 一个"教学标签"
CLUSTER_PROFILES = {
    0: {
        "name": "音准薄弱型",
        "description": "主要问题是错音(音准不准),节奏和力度基本稳定",
        "recommendation": "音阶+练习曲精练,慢速 60 BPM 准后再加速",
    },
    1: {
        "name": "节奏不稳型",
        "description": "节奏稳定性差(std 大),音准相对好",
        "recommendation": "节拍器从 60 BPM 练起,逐步加速到原速",
    },
    2: {
        "name": "表现力缺失型",
        "description": "力度相关性低,音准节奏 OK,但弹得机械",
        "recommendation": "听大师录音,模仿力度变化;练习时关注强弱对比",
    },
    3: {
        "name": "全面待提升型",
        "description": "音准、节奏、力度都需要加强",
        "recommendation": "回归基础,选难度-1 的曲子重新练",
    },
    4: {
        "name": "良好但可精进型",
        "description": "整体良好(score>85),但某些小节可精进",
        "recommendation": "针对错音热点小节重点练习",
    },
}


def extract_features(eval_results: list[dict], period_map: Optional[dict] = None) -> tuple[np.ndarray, list[str]]:
    """从评估结果数组提取特征矩阵
    Returns: (X[N, 8], piece_names[N])
    """
    period_map = period_map or {"Baroque": 0, "Classical": 1, "Romantic": 2}
    X = []
    names = []
    for r in eval_results:
        period = r.get("period", "Classical")
        period_code = period_map.get(period, 1)
        features = [
            r.get("pitch_accuracy", 0.5),
            r.get("timing_std_ms", 50) / 100.0,  # 归一化到 [0,1] 范围
            abs(r.get("timing_mean_ms", 0)) / 100.0,
            r.get("velocity_correlation", 0),
            min(r.get("n_pitch_errors", 0) / 10.0, 1.0),  # 归一化
            min(r.get("timing_std_ms", 0) / 100.0, 1.0),
            1.0 - r.get("velocity_correlation", 0),  # 力度缺失
            r.get("score", 0) / 100.0,
        ]
        X.append(features)
        names.append(r.get("piece", "unknown"))
    return np.array(X, dtype=np.float32), names


def find_optimal_k(X_scaled: np.ndarray, k_range: range = range(2, 6)) -> int:
    """用 silhouette score 找最优 K"""
    from sklearn.metrics import silhouette_score
    best_k, best_score = k_range[0], -1
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(X_scaled, labels)
        if score > best_score:
            best_k, best_score = k, score
    return best_k


def cluster_errors(eval_results: list[dict], n_clusters: Optional[int] = None, method: str = "kmeans") -> dict:
    """主函数:聚类错误模式
    Args:
        eval_results: 评估结果数组
        n_clusters: KMeans 用的 K(HDBSCAN 忽略)
        method: "kmeans" 或 "hdbscan"
    Returns: {
        cluster_ids: 每个曲子的 cluster,
        cluster_profiles: cluster 画像,
        silhouette: 评分,
        recommendations: 每个曲子的推荐
    }
    """
    if len(eval_results) < 2:
        return {"error": "需要至少 2 首曲子的评估"}

    X, names = extract_features(eval_results)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if method == "hdbscan" and HAS_HDBSCAN:
        # HDBSCAN: 免预设 K,自动选 eps 和 min_samples
        # min_cluster_size: 最小簇大小
        min_size = max(2, len(eval_results) // 3)
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_size, min_samples=1)
        cluster_ids = clusterer.fit_predict(X_scaled)
        n_clusters = len(set(cluster_ids)) - (1 if -1 in cluster_ids else 0)
        # HDBSCAN 有 outlier label -1,代表噪声
        n_noise = int(np.sum(cluster_ids == -1))
    else:
        # KMeans
        if n_clusters is None:
            max_k = min(len(eval_results) - 1, 5)
            if max_k < 2:
                n_clusters = 2
            else:
                n_clusters = find_optimal_k(X_scaled, range(2, max_k + 1))
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_ids = km.fit_predict(X_scaled)
        n_noise = 0

    # 评估
    from sklearn.metrics import silhouette_score
    if n_clusters >= 2 and n_noise < len(cluster_ids):
        # HDBSCAN 排除噪声算 silhouette
        if method == "hdbscan" and n_noise > 0:
            mask = cluster_ids != -1
            sil = float(silhouette_score(X_scaled[mask], cluster_ids[mask])) if len(set(cluster_ids[mask])) > 1 else 0.0
        else:
            sil = float(silhouette_score(X_scaled, cluster_ids))
    else:
        sil = 0.0

    # 给每首曲子加推荐(HDBSCAN 的 -1 噪声归 "良好可精进型")
    recommendations = []
    for i, (cid, name) in enumerate(zip(cluster_ids, names)):
        if cid == -1:
            profile = CLUSTER_PROFILES[4]  # 噪声默认
            profile = {**profile, "name": "特殊型(噪声/独特)"}
        else:
            profile = CLUSTER_PROFILES.get(int(cid), CLUSTER_PROFILES[4])
        rec = {
            "piece": name,
            "cluster_id": int(cid),
            "profile_name": profile["name"],
            "description": profile["description"],
            "recommendation": profile["recommendation"],
        }
        recommendations.append(rec)

    return {
        "n_pieces": len(eval_results),
        "n_clusters": int(n_clusters),
        "n_noise": n_noise,
        "silhouette_score": round(sil, 3),
        "method": method,
        "cluster_assignments": dict(zip(names, [int(c) for c in cluster_ids])),
        "recommendations": recommendations,
    }


def main():
    """demo:用 5 首虚拟曲子的评估结果聚类(KMeans vs HDBSCAN 对比)"""
    demo_evals = [
        {"piece": "Minuet in G", "period": "Baroque", "score": 93.5,
         "pitch_accuracy": 0.875, "timing_std_ms": 10.8, "timing_mean_ms": -6.3,
         "velocity_correlation": 0.0, "n_pitch_errors": 1},
        {"piece": "Sonata K.545", "period": "Classical", "score": 78.0,
         "pitch_accuracy": 0.80, "timing_std_ms": 60.0, "timing_mean_ms": -20.0,
         "velocity_correlation": 0.3, "n_pitch_errors": 3},
        {"piece": "Für Elise", "period": "Classical", "score": 88.0,
         "pitch_accuracy": 0.92, "timing_std_ms": 25.0, "timing_mean_ms": 5.0,
         "velocity_correlation": 0.1, "n_pitch_errors": 1},
        {"piece": "Nocturne Op.9", "period": "Romantic", "score": 65.0,
         "pitch_accuracy": 0.70, "timing_std_ms": 80.0, "timing_mean_ms": -50.0,
         "velocity_correlation": 0.2, "n_pitch_errors": 5},
        {"piece": "Träumerei", "period": "Romantic", "score": 82.0,
         "pitch_accuracy": 0.85, "timing_std_ms": 30.0, "timing_mean_ms": -10.0,
         "velocity_correlation": 0.4, "n_pitch_errors": 2},
    ]

    print("=" * 60)
    print("KMeans (预设 K)")
    print("=" * 60)
    km_result = cluster_errors(demo_evals, method="kmeans")
    print(json.dumps(km_result, indent=2, ensure_ascii=False))

    if HAS_HDBSCAN:
        print("\n" + "=" * 60)
        print("HDBSCAN (自动选 K)")
        print("=" * 60)
        hd_result = cluster_errors(demo_evals, method="hdbscan")
        print(json.dumps(hd_result, indent=2, ensure_ascii=False))
    else:
        print("\nHDBSCAN 不可用,跳过")

    # 导出 KMeans 结果(默认)
    out = Path(__file__).parent.parent / "notes" / "error_cluster_demo.json"
    out.write_text(json.dumps(km_result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ KMeans 结果导出到 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

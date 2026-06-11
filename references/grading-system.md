# 分级体系

> **✅ 实现状态**：`assign_grade()`、`assign_stars()`、`to_percentile()` 均已实现在 `full-engine.py` 中，阈值通过 `ScoringConfig` 数据类统一管理。评分完成后自动输出 `qualityGrade` 和 `stars` 字段。

## 默认阈值

```python
def assign_grade(avg_score):
    if avg_score >= 8.0:
        return "S"   # 卓越
    elif avg_score >= 6.5:
        return "A"   # 优秀
    elif avg_score >= 5.0:
        return "B"   # 良好
    else:
        return "C"   # 一般
```

## 阈值调优

实际分布应该接近这些比例：

| 等级 | 理想占比 | 调优建议 |
|------|---------|---------|
| S | 5~10% | < 3% 则降低阈值，> 15% 则提高 |
| A | 20~30% | 最宽区间，容纳大部分"好但不顶尖"的内容 |
| B | 30~40% | 最大区间，容纳大部分内容 |
| C | 20~30% | < 10% 则说明阈值太松，需要提高 |

## 调优公式

```python
def tune_grade_thresholds(projects):
    """根据实际分布建议阈值调整"""
    avgs = [p.get("avgScore", 0) for p in projects]
    avgs.sort()

    n = len(avgs)
    # 按理想占比取分位
    s_threshold = avgs[int(n * 0.90)]  # Top 10%
    a_threshold = avgs[int(n * 0.60)]  # Top 40%
    b_threshold = avgs[int(n * 0.30)]  # Top 70%

    print(f"Suggested thresholds:")
    print(f"  S: >= {round(s_threshold, 1)}")
    print(f"  A: >= {round(a_threshold, 1)}")
    print(f"  B: >= {round(b_threshold, 1)}")
    print(f"  C: < {round(b_threshold, 1)}")
```

## 五星制替代

```python
def assign_stars(avg_score):
    if avg_score >= 9.0:
        return 5
    elif avg_score >= 7.5:
        return 4
    elif avg_score >= 6.0:
        return 3
    elif avg_score >= 4.0:
        return 2
    else:
        return 1
```

## 百分制替代

```python
def to_percentile(avg_score, all_scores):
    """将分数映射到百分位"""
    rank = sum(1 for s in all_scores if s < avg_score)
    return round(rank / len(all_scores) * 100)
```
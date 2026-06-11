# 关键词策略

## 收集原则

每个维度 10~20 个关键词，按类别分组。同类关键词共享一个加分项，避免"关键词堆砌"刷分。

## 分组结构

```python
KEYWORDS = {
    "dimension_name": {
        "category_1": ["word1", "word2", "word3"],
        "category_2": ["word4", "word5", "word6"],
        "category_3": ["word7", "word8", "word9"],
    }
}
```

## 加分逻辑

```python
for category, words in KEYWORDS[dim].items():
    hit_count = sum(1 for w in words if w in text)
    if hit_count > 0:
        bonus = min(hit_count * 0.3, 1.5)  # 同类关键词共享上限
        score += bonus
```

## 关键词质量标准

1. **区分度**：好的关键词能区分"好内容"和"普通内容"。"功能"→ 区分度低，"流程图"→ 区分度高
2. **覆盖面**：同一概念的不同表述都要覆盖。如"api"、"接口"、"sdk"、"插件"
3. **避免泛化**：不要用"好"、"优秀"、"棒"等通用褒义词，它们无法区分内容质量
4. **大小写不敏感**：统一转小写后匹配

## 典型关键词库

### 功能完整度
```python
"functionality": {
    "core": ["核心功能", "功能模块", "主要功能", "feature", "module"],
    "advanced": ["api", "接口", "sdk", "插件", "扩展", "webhook", "自动化"],
    "process": ["流程图", "架构图", "技术方案", "实现方式", "使用方法"],
    "quality": ["开源", "github", "部署", "上线", "release", "测试"],
},
```

### 创新性
```python
"innovation": {
    "novelty": ["首创", "独特", "原创", "脑洞", "创新", "创意", "颠覆"],
    "uniqueness": ["差异化", "不同于", "自研", "特有", "专有"],
    "approach": ["新思路", "新方法", "新方案", "重新定义", "打破"],
    "ai": ["ai", "machine learning", "深度学习", "gpt", "llm", "大模型", "智能"],
},
```

### 交互体验
```python
"ux": {
    "design": ["ui", "ux", "用户体验", "交互设计", "界面设计", "原型"],
    "responsive": ["响应式", "自适应", "移动端", "多端", "适配"],
    "polish": ["动画", "过渡", "流畅", "丝滑", "直觉", "易用"],
    "demo": ["demo", "演示", "预览", "在线体验", "试用"],
},
```

### 视觉设计
```python
"visual": {
    "design": ["设计", "视觉", "美观", "配色", "主题", "风格"],
    "asset": ["图标", "插图", "动效", "品牌", "logo"],
    "tool": ["figma", "sketch", "design system", "组件库"],
},
```

### 技术难度
```python
"techDifficulty": {
    "backend": ["后端", "数据库", "server", "服务器", "api", "微服务", "分布式"],
    "frontend": ["前端", "react", "vue", "typescript", "webgl", "canvas"],
    "complex": ["架构", "并发", "性能优化", "缓存", "安全", "加密"],
    "infra": ["docker", "k8s", "ci/cd", "云", "部署", "运维"],
},
```

### 实用价值
```python
"practicality": {
    "problem": ["痛点", "需求", "场景", "解决", "问题", "实际"],
    "user": ["用户", "使用", "实用", "日常", "效率", "生产力"],
    "market": ["市场", "商业", "盈利", "变现", "目标用户", "人群"],
    "feedback": ["好评", "反馈", "投票", "star", "下载", "使用量"],
},
```

## 关键词效果评估

### 评估指标

1. **命中率（Hit Rate）**：维度内至少被命中 1 次的项目占比。理想值 30%~70%。低于 30% 说明关键词太偏，高于 70% 说明关键词太泛。
2. **区分度（Discrimination）**：高分项目的关键词命中数是否显著高于低分项目。计算方法：取 Top 20% 和 Bottom 20% 项目的平均命中数比值，理想值 > 2.0。
3. **类别覆盖率（Category Coverage）**：维度内每个类别至少被命中的项目数。如果某个类别命中为 0，说明该类别关键词与实际内容完全不匹配。

### 评估方法

**方法一：使用 `--dry-run` 快速验证**

```bash
python full-engine.py --input data.json --output /dev/null --dry-run --dry-run-size 20
```

输出包含每个维度的关键词命中率概览，帮助判断关键词库是否合理。

**方法二：手动分析分布**

```python
import json
from full_engine import score_project, KEYWORDS, SCORE_DIMS

with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
projects = data.get("projects", data) if isinstance(data, dict) else data

# 计算各维度命中率
for dim in SCORE_DIMS:
    kws = KEYWORDS.get(dim, {})
    all_words = [w for words in kws.values() for w in words]
    hit_count = sum(
        1 for p in projects
        if any(w in (p.get("title", "") + " " + p.get("rawText", "")).lower() for w in all_words)
    )
    print(f"{dim}: {hit_count}/{len(projects)} ({hit_count/len(projects)*100:.0f}%)")

# 计算区分度
scored = [score_project(p, KEYWORDS) for p in projects]
scored.sort(key=lambda x: x["avgScore"], reverse=True)
top_n = max(1, len(scored) // 5)
top_avg = sum(s["avgScore"] for s in scored[:top_n]) / top_n
bot_avg = sum(s["avgScore"] for s in scored[-top_n:]) / top_n
print(f"区分度 (Top/Bottom 20%): {top_avg/bot_avg:.1f}")
```

**方法三：单类别命中率**

```python
# 检查每个类别的命中情况
full_text = " ".join(p.get("rawText", "") + " " + p.get("title", "") for p in projects).lower()
for dim in SCORE_DIMS:
    for cat, words in KEYWORDS.get(dim, {}).items():
        hits = [w for w in words if w in full_text]
        print(f"  {dim}/{cat}: {len(hits)}/{len(words)} → {hits}")
```

## 关键词冲突处理

### 冲突类型

1. **跨维度冲突**：同一个关键词被多个维度使用。例如 "api" 同时出现在 `functionality` 和 `techDifficulty` 中。
   - **处理方式**：允许跨维度共享关键词，因为同一关键词可以从不同维度评价。但应确保每个维度的使用场景不同。
   - **示例**：`functionality` 中的 "api" 表示"提供了 API 接口"，`techDifficulty` 中的 "api" 表示"实现了复杂的 API 设计"。

2. **类别内冲突**：同一维度的不同类别包含相同关键词。
   - **处理方式**：**禁止**。同一维度内的类别应互斥，否则会导致重复计分。建议在加载关键词配置时进行去重校验。

3. **关键词歧义**：一个关键词可能匹配到不相关的内容。例如 "设计" 可能匹配到 "设计模式"（技术）而非 "视觉设计"。
   - **处理方式**：
     - 优先使用更具体的关键词替代通用词（如用 "视觉设计"、"配色方案" 替代 "设计"）
     - 对于多义词，使用复合关键词（如 "ui设计"、"界面设计"）
     - 在 `ScoringConfig` 中为歧义类别设置较低的上限

### 冲突校验

```python
def validate_keywords(kws: dict) -> list[str]:
    """校验关键词库，返回冲突列表"""
    warnings = []
    # 1. 检查类别内重复
    for dim, categories in kws.items():
        for cat, words in categories.items():
            dupes = [w for w in words if words.count(w) > 1]
            if dupes:
                warnings.append(f"[{dim}/{cat}] 类别内重复关键词: {list(set(dupes))}")

    # 2. 检查跨维度共享
    word_to_dims = {}
    for dim, categories in kws.items():
        for words in categories.values():
            for w in words:
                word_to_dims.setdefault(w, set()).add(dim)
    for w, dims in word_to_dims.items():
        if len(dims) > 1:
            warnings.append(f"[跨维度] '{w}' 出现在 {dims} 中")

    return warnings
```

### 冲突解决优先级

| 优先级 | 策略 | 适用场景 |
|--------|------|---------|
| 1 | 替换为更具体的关键词 | 通用词歧义 |
| 2 | 降低该类别加分上限 | 类别间需要共享关键词 |
| 3 | 从低权重维度中移除 | 跨维度共享且一方权重明显更低 |
| 4 | 保留并接受一定冗余 | 少量共享且不影响区分度 |
```
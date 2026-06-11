# 数据契约：Rule Scoring Engine

> **版本**: 1.0.0

## 输入格式

```json
{
  "version": "1.0.0",
  "projects": [{
    "topicId": "123",
    "title": "项目标题",
    "rawText": "完整正文内容...",
    "votes": 10,
    "imageCount": 3,
    "replyCount": 5
  }]
}
```

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `topicId` | string | 唯一标识 |
| `title` | string | 项目标题 |
| `rawText` | string | 正文内容（用于关键词匹配） |

### 可选字段（用于统计特征加分）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `votes` | number | 0 | 投票数 |
| `imageCount` | number | 0 | 图片数量 |
| `replyCount` | number | 0 | 回复数 |

> **⚠️ 字段映射说明**：数据契约中的字段名统一使用 `replyCount`。评分引擎内部 `score_project()` 函数通过 `project.get("replyCount", 0)` 从输入中读取该字段，并映射到内部 `engagement` 字典的 `replies` 键名。这一映射保证了输入字段名与上游（stealth-scraper 等）保持兼容，同时引擎内部使用更语义化的命名。

## 输出格式

在输入数据基础上追加以下字段：

```json
{
  "scores": {
    "functionality": 6.5,
    "innovation": 7.0,
    "ux": 5.5,
    "visual": 6.0,
    "techDifficulty": 7.5,
    "practicality": 8.0
  },
  "avgScore": 6.8,
  "qualityGrade": "A",
  "stars": 4,
  "strengths": ["功能完整，描述详尽"],
  "weaknesses": ["交互设计较薄弱"],
  "oneLiner": "以实用价值和创新性为亮点的产品"
}
```

### 评分维度

| 维度 | 键名 | 评分范围 | 默认权重 |
|------|------|---------|---------|
| 功能完整度 | `functionality` | 0-10 | 20% |
| 创新性 | `innovation` | 0-10 | 25% |
| 交互体验 | `ux` | 0-10 | 15% |
| 视觉设计 | `visual` | 0-10 | 15% |
| 技术难度 | `techDifficulty` | 0-10 | 15% |
| 实用价值 | `practicality` | 0-10 | 10% |

### 等级划分

| 等级 | 阈值 | 说明 |
|------|------|------|
| S | ≥ 8.0 | 卓越 |
| A | ≥ 6.5 | 优秀 |
| B | ≥ 5.0 | 良好 |
| C | < 5.0 | 一般 |

### 五星制评分

| 星级 | 阈值 |
|------|------|
| ★★★★★ | ≥ 9.0 |
| ★★★★ | ≥ 7.5 |
| ★★★ | ≥ 6.0 |
| ★★ | ≥ 4.0 |
| ★ | < 4.0 |

## 下游交接

参见 [SKILLS-INDEX.md](../SKILLS-INDEX.md#skill-2--skill-3-交接格式)
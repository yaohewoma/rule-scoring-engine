---
name: "rule-scoring-engine"
version: "1.2.0"
description: "Builds keyword-driven multi-dimensional scoring engines with auto-grading, weighted averages, traceable logic, CSV export, and keyword validation. Invoke when user needs to batch-evaluate content quality or score submissions without AI/ML."
---

# Rule Scoring Engine — 规则引擎自动评分

> **执行前必做：** 生成评分引擎前，必须先阅读 [`references/full-engine.py`](references/full-engine.py) 获取完整模板。
> **核心原则：** 基础分从 5.0 中点起步，每个维度独立计算，维度加权平均得出综合分，同类关键词共享加分上限防刷分。

## 0. 流水线位置

```
stealth-scraper → rule-scoring-engine → ai-batch-processor → data-audit-toolkit
                      ↑ 本 Skill              → [下游: AI洞察]
```

- **上游依赖**：[stealth-scraper](../stealth-scraper/SKILL.md) — 提供原始 HTML + JSON 数据
- **下游 Skill**：[ai-batch-processor](../ai-batch-processor/SKILL.md) — 基于评分结果生成 AI 洞察；[data-audit-toolkit](../data-audit-toolkit/SKILL.md) — 审计评分质量
- **输入格式**：`{ projects: [{ topicId, title, rawText, votes, imageCount }] }`（详见 [数据契约](references/data-contract.md)）
- **产出格式**：在原数据上追加 `scores`、`avgScore`、`qualityGrade`、`stars`、`strengths`、`weaknesses`、`oneLiner`
- **总索引**：[SKILLS-INDEX.md](../SKILLS-INDEX.md)

## 1. 何时使用本 Skill

### 1.1 触发条件

以下场景应使用本 skill：
- 需要对大批量文本内容做初步质量评级（百条以上）
- 作品评审、内容评估、简历筛选等场景
- 需要可解释的评分逻辑（每个维度分数来源透明可追溯）
- 作为 AI 评分前的初筛或补充
- 用户提到"评分"、"打分"、"评级"、"自动评估" 等关键词

以下场景不应使用本 skill：
- 需要深度语义理解 —— 用 AI 评分
- 只有几十条数据 —— 直接人工评审更快
- 文本是高度非结构化的对话 —— 关键词匹配效果差
- 需要实时评分 —— 规则引擎适合离线批处理

### 1.2 前置约束

1. 先读 [`references/full-engine.py`](references/full-engine.py)，理解评分架构
2. 评分维度 4~8 个，参考 [`references/dimension-design.md`](references/dimension-design.md) 选择
3. 每个维度 10~20 个关键词，按类别分组，参考 [`references/keyword-strategy.md`](references/keyword-strategy.md)
4. 基础分 5.0（中点），单次增量 0.3~0.8，类别内共享上限 `min(hit_count * increment, cap)`
5. 等级划分参考 [`references/grading-system.md`](references/grading-system.md)，默认 S ≥ 8.0, A ≥ 6.5, B ≥ 5.0
6. **统计特征权重 > 关键词权重**：字数、图片数等客观指标优先
7. **维度权重已实现**：`ScoringConfig.DIM_WEIGHTS` 控制加权平均，默认权重为功能完整度 20%、创新性 25%、UX 15%、视觉 15%、技术 15%、实用 10%
8. 评分完成后提醒用户用 `data-audit-toolkit` skill 做审计

## 2. 模块与命令导航

### 2.1 目录结构

```
rule-scoring-engine/
├── SKILL.md                          # 本文件
├── requirements.txt                  # Python 依赖（核心引擎零依赖）
├── examples/
│   └── basic-scoring.py              # 快速入门：导入 full-engine 核心函数演示评分
├── references/
│   ├── full-engine.py                # ★ 完整评分引擎模板（必读）— v1.2.0
│   ├── classification-rules.py       # 10 品类产品分类器（支持批量）
│   ├── data-contract.md              # 输入/输出数据契约
│   ├── dimension-design.md           # 维度设计指南
│   ├── keyword-strategy.md           # 关键词策略 + 效果评估
│   ├── grading-system.md             # 分级体系 + 阈值调优
│   ├── keyword-externalization.md    # 关键词 JSON/YAML 外部化
│   ├── weight-config.md              # 三级权重配置体系
│   └── troubleshooting.md            # 故障排查指南
└── tests/
    ├── test_runner.py                 # 自动化测试套件（30 项）
    ├── test_data.json                # 测试输入数据
    ├── test_kw.json                  # 测试关键词配置
    ├── test_cls.json                 # 测试分类配置
    └── test_scored.json              # 基准期望输出
```

### 2.2 模块地图

| 大模块 | 解决什么问题 | 参考文件 |
|------|------------|---------|
| 完整引擎模板 | 可直接运行的评分脚本，包含所有功能 | [`references/full-engine.py`](references/full-engine.py) |
| 快速入门示例 | 演示如何导入核心函数对少量项目评分 | [`examples/basic-scoring.py`](examples/basic-scoring.py) |
| 产品分类器 | 多维度关键词匹配的产品类型分类 | [`references/classification-rules.py`](references/classification-rules.py) |
| 数据契约 | 输入/输出格式定义，上下游交接规范 | [`references/data-contract.md`](references/data-contract.md) |
| 维度设计 | 如何定义评分维度、权重和场景模板 | [`references/dimension-design.md`](references/dimension-design.md) |
| 关键词策略 | 关键词收集、分类、增量设计、效果评估 | [`references/keyword-strategy.md`](references/keyword-strategy.md) |
| 分级体系 | 分数→等级的映射方法和阈值调优 | [`references/grading-system.md`](references/grading-system.md) |
| 关键词外部化 | 关键词库从代码分离，支持 JSON/YAML 配置 | [`references/keyword-externalization.md`](references/keyword-externalization.md) |
| 权重配置 | 维度、类别、关键词三级权重体系 | [`references/weight-config.md`](references/weight-config.md) |
| 故障排查 | 评分异常、分类错误、输出格式问题的解决方案 | [`references/troubleshooting.md`](references/troubleshooting.md) |
| 测试用例 | 基准测试数据和期望输出 | [`tests/`](tests/) |

### 2.3 完整引擎模板

**必读 reference**：[`references/full-engine.py`](references/full-engine.py)

完整的可运行 Python 脚本，包含：
- 6 个维度的评分函数 `score_one_dim()`
- 关键词库 `KEYWORDS`（6 个维度 × 3~4 个类别 × 4~6 个关键词）
- 加权平均计算 `avgScore`（`ScoringConfig.DIM_WEIGHTS`）
- 等级划分 `assign_grade()` + 五星制 `assign_stars()` + 百分位 `to_percentile()`
- 衍生分析：`identify_one_liner()` + `quick_swot()`
- CLI 接口：`--input` / `--output` / `--dry-run` / `--tune` / `--keywords` / `--quiet` / `--verbose` / `--version` / `--validate` / `--output-format`
- 统一错误码：0=成功, 1=参数错误, 2=数据错误, 3=运行时错误

### 2.4 产品分类器

**必读 reference**：[`references/classification-rules.py`](references/classification-rules.py)

独立可运行的脚本，根据文本内容自动分类产品类型。

| 分类 | 关键词数 | 典型关键词 |
|------|---------|-----------|
| 游戏 | 20 | 游戏、玩法、关卡、unity、godot |
| 教育 | 20 | 学习、教育、课程、答题、刷题 |
| 工具 | 20 | 工具、效率、自动化、搜索、计算器 |
| AI | 12 | AI、大模型、LLM、ChatGPT、智能体 |
| 健康 | 17 | 健康、医疗、心理、康复、睡眠 |
| 金融 | 11 | 理财、投资、股票、记账、贷款 |
| 设计 | 10 | 设计、figma、UI、UX、原型 |
| 社交 | 12 | 社交、聊天、匹配、交友、社区 |
| 求职 | 10 | 简历、面试、求职、offer、招聘 |
| 内容 | 15 | 博客、写作、笔记、markdown、翻译 |

分类策略：科技/创新关键词优先匹配（≥2 命中 → AI工具/科技工具），再匹配品类关键词，最后回退为"工具"。支持赛道加权（`--track Code` 传参）。

### 2.5 维度设计模块

**必读 reference**：[`references/dimension-design.md`](references/dimension-design.md)

| 场景 | 推荐维度 | 维度数 |
|------|---------|--------|
| 作品评审 | 功能完整度(20%)、创新性(25%)、交互体验(15%)、视觉设计(15%)、技术难度(15%)、实用价值(10%) | 6 |
| 简历筛选 | 经验匹配、技能广度、项目深度、教育背景、沟通表达 | 5 |
| 内容质量 | 准确性、深度、可读性、完整性、时效性 | 5 |
| 客服质检 | 响应速度、问题解决、服务态度、合规性 | 4 |

**路由提醒**：维度之间必须互斥，不能有交叉重叠。维度权重通过 `ScoringConfig.DIM_WEIGHTS` 配置。

## 3. 生成评分引擎的标准流程

1. **定义评分维度**：与用户确认评估维度，4~8 个为宜，参考 [`references/dimension-design.md`](references/dimension-design.md)
2. **收集关键词库**：每个维度 10~20 个关键词，按类别分组，参考 [`references/keyword-strategy.md`](references/keyword-strategy.md)
3. **确定统计特征**：字数、图片数、代码量、投票数等可量化指标
4. **设定基准分和增量**：基础分 5.0（中点起步），单次增量 0.3~0.8
5. **配置维度权重**：在 `ScoringConfig.DIM_WEIGHTS` 中设置，总和应为 1.0
6. **定义等级阈值**：参考 [`references/grading-system.md`](references/grading-system.md)
7. **生成代码**：基于 [`references/full-engine.py`](references/full-engine.py) 模板
8. **Dry-Run 验证**：`--dry-run --dry-run-size 20` 检查关键词命中率和分布
9. **关联审计**：提醒用户评分完成后用 `data-audit-toolkit` skill 做质量审计

## 4. 常见错误

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 基础分从 0 开始 | 大部分项目分数偏低，区分度不足 | 从 5.0 中点起步 |
| 每个关键词单独加分 | 100 个关键词 = 可能 +30 分，严重失衡 | 同类别共享一个加分项，设置上限 |
| 不设增量上限 | 某个特征过度影响总分 | 用 `min(hit_count * increment, cap)` |
| 关键词太泛 | "好"、"优秀"、"棒" 无法区分内容 | 用具体的技术术语、行业词汇 |
| 只靠关键词不靠统计特征 | 字数 10 但关键词多的项目拿高分 | 统计特征权重 > 关键词权重 |
| 不生成 SWOT | 只有分数没有可读的分析结论 | 衍生 `quick_swot()` 和 `identify_one_liner()` |
| 维度权重不归一 | 加权总分超出预期范围 | DIM_WEIGHTS 总和应为 1.0 |

## 5. 参数调优速查

| 参数 | 默认值 | 说明 | 何时调参 |
|------|--------|------|---------|
| 基础分 `base_score` | 5.0 | 评分起点 | 需要更严格或更宽松的评分时调整 |
| 增量 `increment` | 0.3 | 每次关键词匹配加分 | 关键词密度高时减小，稀疏时增大 |
| 增量上限 `cap` | 1.5 | 单类别最高加分 | 防止某个类别过度影响维度分 |
| 统计特征权重 | 1.5x | 统计特征相对关键词的权重倍率 | 统计特征与关键词的平衡 |
| S 级阈值 | 8.0 | 卓越等级分界线 | 根据实际分布自动建议 |
| A 级阈值 | 6.5 | 优秀等级分界线 | 根据实际分布自动建议 |
| 维度数 | 6 | 评分维度数量 | 场景不同可 4~8 个 |
| 维度权重 `DIM_WEIGHTS` | [见上表] | 各维度在加权平均中的权重 | 业务侧重点调整 |

## 6. Quick Start

```bash
# 1. 环境准备（零依赖，可选安装 tqdm 进度条）
pip install -r requirements.txt   # 仅安装 tqdm；不装也可运行

# 2. 快速入门 — 运行示例代码
cd examples
python basic-scoring.py
# 输出 3 个示例项目的六维度评分结果 + 保存 basic_scored.json

# 3. 用测试数据验证引擎
cd ../references
python full-engine.py --input ../tests/test_data.json --dry-run --dry-run-size 2
# 输出关键词命中率报告，检查关键词库是否合理

# 4. 全量评分
python full-engine.py --input ../tests/test_data.json --output scored.json

# 5. 自动建议阈值
python full-engine.py --input scored.json --tune

# 6. 静默模式（CI/CD 或脚本集成）
python full-engine.py --input data.json --output scored.json --quiet

# 7. 详细日志（调试关键词匹配）
python full-engine.py --input data.json --output scored.json --verbose

# 8. 产品分类（可选）
python classification-rules.py --text "一个AI驱动的学习助手" --track Code --verbose

# 9. 批量分类（管道集成）
python classification-rules.py --input scored.json --output classified.csv

# 10. 校验关键词配置（不评分，仅检查质量）
python full-engine.py --validate

# 11. 运行测试套件
cd .. && python tests/test_runner.py
```

## 7. 测试

### 7.1 运行自动化测试

```bash
python tests/test_runner.py
```

覆盖 30 项测试：模块导入、基准评分一致性、CSV 导出、批量分类、关键词校验、输入校验、分类器一致性、CLI 各模式可运行性。

### 7.2 运行基准测试

```bash
cd references
python full-engine.py --input ../tests/test_data.json --output ../tests/test_scored.json

# 验证输出与期望一致
python -c "
import json
actual = json.load(open('../tests/test_scored.json'))
expected = json.load(open('../tests/test_scored_expected.json'))
# 比较 avgScore 和 qualityGrade
for a, e in zip(actual, expected):
    assert a['avgScore'] == e['avgScore'], f'{a[\"title\"]}: {a[\"avgScore\"]} != {e[\"avgScore\"]}'
    assert a['qualityGrade'] == e['qualityGrade']
print('All tests passed')
"
```

### 7.3 测试文件说明

| 文件 | 用途 |
|------|------|
| `tests/test_runner.py` | 自动化测试入口（30 项检查） |
| `tests/test_data.json` | 2 项目输入：AI 助手 + 简单计算器 |
| `tests/test_kw.json` | 精简关键词配置（用于测试外部加载） |
| `tests/test_cls.json` | 精简分类配置（用于测试分类器） |
| `tests/test_scored.json` | 基准期望输出（每次更新引擎后需重新生成） |

## 8. 错误码

| 错误码 | 含义 | 场景 |
|--------|------|------|
| 0 | 成功 | 正常完成 |
| 1 | 参数错误 | 命令行参数缺失或无效 |
| 2 | 数据错误 | 文件不存在、JSON 格式错误、字段缺失 |
| 3 | 运行时错误 | 写入文件失败等系统错误 |
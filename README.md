# rule-scoring-engine

> **一句话**：零 API 成本，每个分数都能追溯

基于关键词驱动 + 统计特征的多维度自动评分引擎。不调用任何 LLM API，每个分数背后的评分逻辑完全可解释和可追溯。

## 快速开始

```bash
# 查看示例
python examples/basic-scoring.py

# 运行完整引擎
python references/full-engine.py --input data.json --output scored.json
```

## 模块地图

| 目录/文件 | 说明 |
|-----------|------|
| `SKILL.md` | Skill 主文档 |
| `examples/` | 使用示例 |
| `references/` | 参考实现（full-engine, classification-rules 等） |
| `tests/` | 测试固件 |
| `CHANGELOG.md` | 变更日志 |

## 核心能力

- 6 维度评分：功能完整度、创新性、交互体验、视觉设计、技术难度、实用价值
- 关键词分类规则（教育、工具、游戏等）
- 完全可追溯的评分逻辑
- 零 API 依赖，纯 Python 标准库

## 适用场景

- 项目 / 产品自动评分
- 竞品质量评估
- 需要可解释评估结果的场景

## GitHub

https://github.com/yaohewoma/rule-scoring-engine
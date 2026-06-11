# Rule Scoring Engine — 故障排查指南

## 运行错误

### `KeyError: 'scores'`

**症状**：运行 `full-engine.py` 时提示 `KeyError: 'scores'`。

**原因**：输入数据格式不符合数据契约，缺少必要字段。

**解决方案**：
1. 确保输入数据是上游 stealth-scraper 产出的 JSON 格式
2. 检查数据是否包含 `projects` 数组
3. 每个项目必须包含 `topicId`、`title`、`rawText` 字段

```bash
# 验证输入数据格式
python -c "import json; d=json.load(open('data.json')); print('projects' in d, len(d.get('projects',[])))"
```

### 所有项目评分相同

**症状**：运行后所有项目的 `avgScore` 完全相同，没有区分度。

**原因**：
1. 关键词库与文本内容不匹配（关键词太泛或太偏）
2. `rawText` 字段为空或只有极短文本
3. 基础分设置过高，增量无法产生区分

**解决方案**：
1. 检查 `rawText` 是否非空：`python -c "import json; d=json.load(open('data.json')); print([len(p['rawText']) for p in d['projects'][:5]])"`
2. 根据实际内容定制关键词库，参考 `keyword-strategy.md`
3. 降低基础分或增大增量

### `ValueError` 或评分异常

**症状**：运行评分时出现异常，或评分结果不符合预期。

**原因**：`assign_grade()` 函数不会主动抛出 `ValueError`，但以下情况可能导致评分异常：
1. 输入数据中 `rawText` 为空，导致所有项目得分均为 `BASE_SCORE`
2. 关键词库与文本内容完全不匹配
3. `ScoringConfig` 中的阈值设置不合理

**解决方案**：
- 检查输入数据是否包含有效正文：`python -c "import json; d=json.load(open('data.json')); print([len(p.get('rawText','')) for p in d.get('projects',[])][:5])"`
- 使用 `--dry-run` 验证关键词库效果
- 检查 `ScoringConfig` 中 `GRADE_S`、`GRADE_A`、`GRADE_B` 是否满足 `GRADE_S >= GRADE_A >= GRADE_B`
- 使用 `--tune` 根据实际分布自动建议阈值

## 评分质量问题

### S 级项目占比过高（> 30%）

**症状**：评分后 S 级项目过多，缺乏区分度。

**排查**：
1. 关键词是否过于宽泛（如"功能"、"系统"等通用词）
2. 增量上限是否过高
3. 统计特征权重是否过低

**解决方案**：
```python
# 在 full-engine.py 中调整 ScoringConfig 参数
config = ScoringConfig(
    KW_BONUS_PER_HIT=0.2,      # 降低关键词增量（默认 0.3）
    KW_BONUS_CAP=1.0,          # 降低关键词上限（默认 1.5）
    GRADE_S=8.5,               # 提高 S 级阈值（默认 8.0）
    GRADE_A=7.0,               # 提高 A 级阈值（默认 6.5）
)
```

### 关键词碰瓷项目得分过高

**症状**：标题堆砌关键词但正文无实质内容，评分却很高。

**解决方案**：
1. 提高统计特征权重（字数、图片数）
2. 降低关键词增量
3. 增加"标题正文一致性"检查维度
4. 评分后用 `data-audit-toolkit` 做碰瓷检测

### 分类结果不准确

**症状**：`classification-rules.py` 将项目分到错误的类别。

**原因**：关键词库与目标领域不匹配。

**解决方案**：
1. 检查 `classification-rules.py` 中的 `PRODUCT_TYPE_KEYWORDS` 关键词库
2. 根据实际数据分布调整关键词
3. 增加更具体的类别关键词，减少通用词

```python
PRODUCT_TYPE_KEYWORDS = {
    "AI": ["大模型", "LLM", "ChatGPT", "智能体", "机器学习", "深度学习"],
    # 使用更具体、更专业的关键词
}
```

## 输出问题

### 输出 JSON 文件为空或格式错误

**症状**：`--output` 指定的文件为空或无法解析。

**排查**：
1. 检查 `--input` 文件是否存在且格式正确
2. 检查是否有写入权限
3. 脚本是否正常完成（检查控制台输出）
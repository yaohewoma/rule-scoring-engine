# Changelog

All notable changes to this skill will be documented in this file.

## [1.2.0] - 2026-06-11

### Added
- `--version` 标志（`python full-engine.py --version` 输出版本号）
- `--validate` 模式（`python full-engine.py --validate` 校验关键词配置不评分）
- `validate_keywords()` 函数：检查类别内重复、跨维度共享、覆盖度、泛化关键词
- `export_to_csv()` 函数 + `--output-format csv`（CSV 输出，含 BOM 兼容 Excel）
- `classification-rules.py` 批量分类模式（`--input scored.json --output classified.csv`）
- `tests/test_runner.py` 自动化测试套件（30 项测试，覆盖导入/基准/CSV/分类/校验/CLI）
- `re` 模块：关键词匹配从 O(N*M) 字符串遍历优化为正则批量匹配 O(N)
- `csv` 模块：CSV 导出支持

### Changed
- 关键词匹配性能优化：`score_keywords()` 使用 `re.findall` 批量匹配
- `classification-rules.py` 关键词匹配同步优化为 `re.findall`
- `--text` 参数改为可选（配合 `--input` 批量模式）
- `--input` 参数改为可选（配合 `--version` / `--validate`）
- 错误码细化：`--validate` 发现有警告时 exit 1

### Fixed
- 重复 `--validate` 代码块移除
- `--version` 和 `--validate` 不需要 `--input` 即可运行

## [1.1.0] - 2026-06-11

### Added
- `ScoringConfig.DIM_WEIGHTS` 加权平均计算（替代等权平均）
- `--quiet` 静默模式（仅输出错误）
- `--verbose` 详细日志模式
- `requirements.txt`（可选 tqdm 依赖）
- `tests/` 目录（test_data, test_kw, test_cls, test_scored）
- 五星制评分 `assign_stars()` 已在数据契约中补充文档
- `basic-scoring.py` 重构为 thin wrapper，导入 full-engine 核心函数

### Changed
- 统一错误码：0=成功, 1=参数错误, 2=数据错误, 3=运行时错误
- `classification-rules.py` 同样支持 `--quiet` 和统一错误码
- `dimension-design.md` 移除"权重未实现"过时说明
- `data-contract.md` 补充维度权重和五星制评分说明
- SKILL.md 重构：增加目录结构总览、测试章节、错误码章节

### Fixed
- 清理 `references/__pycache__/`
- test fixtures 从 `references/` 移至 `tests/`

## [1.0.0] - 2026-06-11

### Added
- Initial release
- Complete SKILL.md with standardized structure
- Full references/ documentation
- Troubleshooting guide
- Examples and test fixtures
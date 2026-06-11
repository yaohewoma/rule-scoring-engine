# 关键词外部化模块

## 概述

将评分引擎的关键词库从 Python 代码中分离，存储为外部 JSON/YAML 文件，便于维护和动态更新。

## 配置文件格式

### JSON 格式 (keywords.json)

```json
{
  "version": "1.0.0",
  "updated_at": "2024-01-01",
  "dimensions": {
    "functionality": {
      "name": "功能完整度",
      "weight": 1.0,
      "base_score": 5.0,
      "increment": 0.5,
      "cap": 2.0,
      "categories": {
        "core_features": {
          "name": "核心功能",
          "keywords": ["功能", "特性", "模块", "组件", "系统"],
          "weight": 1.0
        },
        "api_integration": {
          "name": "API集成",
          "keywords": ["api", "接口", "sdk", "webhook", "集成"],
          "weight": 0.8
        },
        "data_processing": {
          "name": "数据处理",
          "keywords": ["数据", "处理", "分析", "统计", "报表"],
          "weight": 0.9
        }
      }
    },
    "innovation": {
      "name": "创新性",
      "weight": 1.2,
      "base_score": 5.0,
      "increment": 0.6,
      "cap": 2.5,
      "categories": {
        "novelty": {
          "name": "新颖性",
          "keywords": ["创新", "首创", "独特", "新颖", "突破"],
          "weight": 1.0
        },
        "differentiation": {
          "name": "差异化",
          "keywords": ["差异化", "区别", "特色", "亮点", "优势"],
          "weight": 0.9
        }
      }
    }
  }
}
```

### YAML 格式 (keywords.yaml)

```yaml
version: "1.0.0"
updated_at: "2024-01-01"
dimensions:
  functionality:
    name: "功能完整度"
    weight: 1.0
    base_score: 5.0
    increment: 0.5
    cap: 2.0
    categories:
      core_features:
        name: "核心功能"
        keywords:
          - "功能"
          - "特性"
          - "模块"
          - "组件"
          - "系统"
        weight: 1.0
      api_integration:
        name: "API集成"
        keywords:
          - "api"
          - "接口"
          - "sdk"
          - "webhook"
          - "集成"
        weight: 0.8
```

## 实现

```python
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class KeywordCategory:
    """关键词类别配置"""
    name: str
    keywords: List[str]
    weight: float = 1.0


@dataclass
class DimensionConfig:
    """评分维度配置"""
    name: str
    weight: float
    base_score: float
    increment: float
    cap: float
    categories: Dict[str, KeywordCategory]


@dataclass
class ScoringConfig:
    """评分配置"""
    version: str
    dimensions: Dict[str, DimensionConfig]
    updated_at: str


class KeywordManager:
    """关键词管理器"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Optional[ScoringConfig] = None
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        ext = os.path.splitext(self.config_path)[1].lower()
        
        if ext == ".json":
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif ext in (".yaml", ".yml"):
            import yaml
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"不支持的配置文件格式: {ext}")
        
        self.config = self._parse_config(data)
    
    def _parse_config(self, data: Dict[str, Any]) -> ScoringConfig:
        """解析配置数据"""
        dimensions = {}
        
        for dim_key, dim_data in data.get("dimensions", {}).items():
            categories = {}
            for cat_key, cat_data in dim_data.get("categories", {}).items():
                categories[cat_key] = KeywordCategory(
                    name=cat_data["name"],
                    keywords=cat_data["keywords"],
                    weight=cat_data.get("weight", 1.0)
                )
            
            dimensions[dim_key] = DimensionConfig(
                name=dim_data["name"],
                weight=dim_data.get("weight", 1.0),
                base_score=dim_data.get("base_score", 5.0),
                increment=dim_data.get("increment", 0.5),
                cap=dim_data.get("cap", 2.0),
                categories=categories
            )
        
        return ScoringConfig(
            version=data.get("version", "1.0.0"),
            dimensions=dimensions,
            updated_at=data.get("updated_at", "")
        )
    
    def get_dimension_config(self, dimension: str) -> Optional[DimensionConfig]:
        """获取维度配置"""
        return self.config.dimensions.get(dimension) if self.config else None
    
    def get_keywords(self, dimension: str, category: str) -> List[str]:
        """获取指定维度和类别的关键词"""
        dim_config = self.get_dimension_config(dimension)
        if dim_config and category in dim_config.categories:
            return dim_config.categories[category].keywords
        return []
    
    def get_all_keywords(self, dimension: str) -> Dict[str, List[str]]:
        """获取维度下所有类别的关键词"""
        dim_config = self.get_dimension_config(dimension)
        if not dim_config:
            return {}
        return {cat.name: cat.keywords for cat in dim_config.categories.values()}
    
    def reload(self):
        """重新加载配置文件"""
        self._load_config()
    
    def export_to_python(self, output_path: str):
        """导出为 Python 代码格式"""
        if not self.config:
            return
        
        lines = [
            '"""',
            '自动生成的关键词配置',
            f'版本: {self.config.version}',
            f'更新时间: {self.config.updated_at}',
            '"""',
            '',
            'from typing import Dict, List',
            '',
            '# 评分维度配置',
            'DIMENSIONS = {'
        ]
        
        for dim_name, dim_config in self.config.dimensions.items():
            lines.append(f'    "{dim_name}": {{')
            lines.append(f'        "name": "{dim_config.name}",')
            lines.append(f'        "weight": {dim_config.weight},')
            lines.append(f'        "base_score": {dim_config.base_score},')
            lines.append(f'        "increment": {dim_config.increment},')
            lines.append(f'        "cap": {dim_config.cap},')
            lines.append(f'        "categories": {{')
            
            for cat_name, cat_config in dim_config.categories.items():
                keywords_str = ', '.join(f'"{kw}"' for kw in cat_config.keywords)
                lines.append(f'            "{cat_name}": {{')
                lines.append(f'                "name": "{cat_config.name}",')
                lines.append(f'                "keywords": [{keywords_str}],')
                lines.append(f'                "weight": {cat_config.weight}')
                lines.append(f'            }},')
            
            lines.append('        }')
            lines.append('    },')
        
        lines.append('}')
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
```

## 使用示例

### 加载配置

```python
# 初始化关键词管理器
keyword_manager = KeywordManager("keywords.json")

# 获取维度配置
func_config = keyword_manager.get_dimension_config("functionality")
print(f"维度: {func_config.name}, 权重: {func_config.weight}")

# 获取关键词
core_keywords = keyword_manager.get_keywords("functionality", "core_features")
print(f"核心功能关键词: {core_keywords}")
```

### 集成到评分引擎

```python
class ScoringEngine:
    """评分引擎"""
    
    def __init__(self, keyword_manager: KeywordManager):
        self.keyword_manager = keyword_manager
    
    def score_dimension(self, text: str, dimension: str) -> float:
        """计算单个维度的分数"""
        dim_config = self.keyword_manager.get_dimension_config(dimension)
        if not dim_config:
            return 0.0
        
        score = dim_config.base_score
        total_increment = 0.0
        
        for cat_name, cat_config in dim_config.categories.items():
            # 计算关键词匹配
            matches = sum(1 for kw in cat_config.keywords if kw in text)
            if matches > 0:
                # 类别内增量
                cat_increment = min(
                    matches * dim_config.increment * cat_config.weight,
                    dim_config.cap * cat_config.weight
                )
                total_increment += cat_increment
        
        # 应用维度权重
        score += total_increment * dim_config.weight
        
        return min(score, 10.0)
    
    def score_all(self, text: str) -> Dict[str, float]:
        """计算所有维度的分数"""
        scores = {}
        for dimension in self.keyword_manager.config.dimensions:
            scores[dimension] = self.score_dimension(text, dimension)
        return scores
```

### 动态更新关键词

```python
# 添加新关键词
def add_keyword(keyword_manager: KeywordManager, dimension: str, 
                category: str, keyword: str):
    """动态添加关键词"""
    config_path = keyword_manager.config_path
    
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if dimension in data["dimensions"]:
        if category in data["dimensions"][dimension]["categories"]:
            keywords = data["dimensions"][dimension]["categories"][category]["keywords"]
            if keyword not in keywords:
                keywords.append(keyword)
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 重新加载配置
    keyword_manager.reload()
```

## 配置文件管理

### 版本控制

```json
{
  "version": "1.2.0",
  "changelog": [
    {
      "version": "1.2.0",
      "date": "2024-01-15",
      "changes": ["新增 AI 维度", "调整创新性权重"]
    },
    {
      "version": "1.1.0",
      "date": "2024-01-01",
      "changes": ["新增数据处理类别"]
    }
  ]
}
```

### 配置校验

```python
def validate_config(data: Dict[str, Any]) -> List[str]:
    """校验配置文件格式"""
    errors = []
    
    # 检查必填字段
    if "dimensions" not in data:
        errors.append("缺少 dimensions 字段")
        return errors
    
    for dim_name, dim_config in data["dimensions"].items():
        # 检查维度必填字段
        if "name" not in dim_config:
            errors.append(f"维度 {dim_name} 缺少 name 字段")
        
        if "categories" not in dim_config:
            errors.append(f"维度 {dim_name} 缺少 categories 字段")
            continue
        
        for cat_name, cat_config in dim_config["categories"].items():
            # 检查类别必填字段
            if "name" not in cat_config:
                errors.append(f"类别 {dim_name}.{cat_name} 缺少 name 字段")
            if "keywords" not in cat_config:
                errors.append(f"类别 {dim_name}.{cat_name} 缺少 keywords 字段")
            elif not isinstance(cat_config["keywords"], list):
                errors.append(f"类别 {dim_name}.{cat_name} 的 keywords 必须是数组")
    
    return errors
```

## 注意事项

1. **文件编码**：配置文件必须使用 UTF-8 编码
2. **热更新**：修改配置文件后调用 `reload()` 生效
3. **备份**：建议在修改前备份配置文件
4. **校验**：使用 `validate_config()` 校验配置格式
5. **版本管理**：记录配置变更历史

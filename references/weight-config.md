# 权重配置模块

## 概述

权重配置模块支持为不同关键词和维度设置差异化权重，实现更精细的评分控制。

## 权重类型

### 1. 维度权重

控制各维度对总分的影响程度：

```json
{
  "dimension_weights": {
    "functionality": 1.0,
    "innovation": 1.2,
    "user_experience": 1.1,
    "technical": 0.9,
    "market_value": 1.0
  }
}
```

### 2. 类别权重

控制同一维度内不同类别的影响程度：

```json
{
  "dimensions": {
    "functionality": {
      "categories": {
        "core_features": { "weight": 1.0 },
        "api_integration": { "weight": 0.8 },
        "data_processing": { "weight": 0.9 }
      }
    }
  }
}
```

### 3. 关键词权重

为特定关键词设置单独权重：

```json
{
  "keyword_weights": {
    "functionality": {
      "api": 1.5,
      "sdk": 1.3,
      "webhook": 1.2,
      "功能": 1.0,
      "特性": 0.9
    }
  }
}
```

## 实现

```python
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class WeightConfig:
    """权重配置"""
    dimension_weights: Dict[str, float] = field(default_factory=dict)
    category_weights: Dict[str, Dict[str, float]] = field(default_factory=dict)
    keyword_weights: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # 默认权重
    default_dimension_weight: float = 1.0
    default_category_weight: float = 1.0
    default_keyword_weight: float = 1.0


class WeightManager:
    """权重管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = WeightConfig()
        if config:
            self._load_config(config)
    
    def _load_config(self, config: Dict[str, Any]):
        """加载权重配置"""
        if "dimension_weights" in config:
            self.config.dimension_weights = config["dimension_weights"]
        
        if "category_weights" in config:
            self.config.category_weights = config["category_weights"]
        
        if "keyword_weights" in config:
            self.config.keyword_weights = config["keyword_weights"]
        
        # 默认权重
        self.config.default_dimension_weight = config.get("default_dimension_weight", 1.0)
        self.config.default_category_weight = config.get("default_category_weight", 1.0)
        self.config.default_keyword_weight = config.get("default_keyword_weight", 1.0)
    
    def get_dimension_weight(self, dimension: str) -> float:
        """获取维度权重"""
        return self.config.dimension_weights.get(
            dimension, 
            self.config.default_dimension_weight
        )
    
    def get_category_weight(self, dimension: str, category: str) -> float:
        """获取类别权重"""
        if dimension in self.config.category_weights:
            return self.config.category_weights[dimension].get(
                category,
                self.config.default_category_weight
            )
        return self.config.default_category_weight
    
    def get_keyword_weight(self, dimension: str, keyword: str) -> float:
        """获取关键词权重"""
        if dimension in self.config.keyword_weights:
            return self.config.keyword_weights[dimension].get(
                keyword,
                self.config.default_keyword_weight
            )
        return self.config.default_keyword_weight
    
    def set_dimension_weight(self, dimension: str, weight: float):
        """设置维度权重"""
        self.config.dimension_weights[dimension] = weight
    
    def set_category_weight(self, dimension: str, category: str, weight: float):
        """设置类别权重"""
        if dimension not in self.config.category_weights:
            self.config.category_weights[dimension] = {}
        self.config.category_weights[dimension][category] = weight
    
    def set_keyword_weight(self, dimension: str, keyword: str, weight: float):
        """设置关键词权重"""
        if dimension not in self.config.keyword_weights:
            self.config.keyword_weights[dimension] = {}
        self.config.keyword_weights[dimension][keyword] = weight
    
    def normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """归一化权重，使总和为 1"""
        total = sum(weights.values())
        if total == 0:
            return weights
        return {k: v / total for k, v in weights.items()}
    
    def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "dimension_weights": self.config.dimension_weights,
            "category_weights": self.config.category_weights,
            "keyword_weights": self.config.keyword_weights,
            "default_dimension_weight": self.config.default_dimension_weight,
            "default_category_weight": self.config.default_category_weight,
            "default_keyword_weight": self.config.default_keyword_weight
        }
```

## 带权重的评分引擎

```python
class WeightedScoringEngine:
    """带权重的评分引擎"""
    
    def __init__(self, keyword_manager, weight_manager):
        self.keyword_manager = keyword_manager
        self.weight_manager = weight_manager
    
    def score_dimension(self, text: str, dimension: str) -> float:
        """计算单个维度的分数"""
        dim_config = self.keyword_manager.get_dimension_config(dimension)
        if not dim_config:
            return 0.0
        
        score = dim_config.base_score
        total_increment = 0.0
        
        # 获取维度权重
        dim_weight = self.weight_manager.get_dimension_weight(dimension)
        
        for cat_name, cat_config in dim_config.categories.items():
            # 获取类别权重
            cat_weight = self.weight_manager.get_category_weight(dimension, cat_name)
            
            # 计算关键词匹配（带权重）
            cat_increment = 0.0
            for keyword in cat_config.keywords:
                if keyword in text:
                    # 获取关键词权重
                    kw_weight = self.weight_manager.get_keyword_weight(dimension, keyword)
                    cat_increment += dim_config.increment * kw_weight
            
            # 应用类别权重和上限
            cat_increment = min(cat_increment * cat_weight, dim_config.cap * cat_weight)
            total_increment += cat_increment
        
        # 应用维度权重
        score += total_increment * dim_weight
        
        return min(score, 10.0)
    
    def score_all(self, text: str) -> Dict[str, float]:
        """计算所有维度的分数"""
        scores = {}
        for dimension in self.keyword_manager.config.dimensions:
            scores[dimension] = self.score_dimension(text, dimension)
        return scores
    
    def calculate_weighted_average(self, scores: Dict[str, float]) -> float:
        """计算加权平均分"""
        total_weight = 0.0
        weighted_sum = 0.0
        
        for dimension, score in scores.items():
            weight = self.weight_manager.get_dimension_weight(dimension)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
```

## 权重调优策略

### 1. 基于业务目标

```python
# 重视创新的场景
INNOVATION_FOCUSED = {
    "dimension_weights": {
        "functionality": 0.8,
        "innovation": 1.5,  # 创新权重最高
        "user_experience": 1.0,
        "technical": 0.9,
        "market_value": 1.0
    }
}

# 重视稳定性的场景
STABILITY_FOCUSED = {
    "dimension_weights": {
        "functionality": 1.3,  # 功能权重最高
        "innovation": 0.7,
        "user_experience": 1.0,
        "technical": 1.2,  # 技术权重较高
        "market_value": 0.8
    }
}
```

### 2. 基于数据分布

```python
def auto_adjust_weights(scores_data: List[Dict[str, float]], 
                       target_distribution: Dict[str, float]) -> Dict[str, float]:
    """根据目标分布自动调整权重"""
    # 计算当前分布
    current_distribution = {}
    for dimension in scores_data[0].keys():
        values = [s[dimension] for s in scores_data]
        current_distribution[dimension] = sum(values) / len(values)
    
    # 计算调整系数
    adjusted_weights = {}
    for dimension, target in target_distribution.items():
        current = current_distribution.get(dimension, 5.0)
        # 权重与目标/当前比值成正比
        adjusted_weights[dimension] = target / current
    
    # 归一化
    total = sum(adjusted_weights.values())
    return {k: v / total * len(adjusted_weights) for k, v in adjusted_weights.items()}
```

### 3. 基于专家反馈

```python
def calibrate_with_expert_feedback(
    engine: WeightedScoringEngine,
    expert_scores: List[Dict[str, Any]],
    learning_rate: float = 0.1
) -> Dict[str, float]:
    """根据专家反馈校准权重"""
    weight_adjustments = {}
    
    for item in expert_scores:
        text = item["text"]
        expert_score = item["expert_score"]
        
        # 计算当前分数
        current_scores = engine.score_all(text)
        current_avg = engine.calculate_weighted_average(current_scores)
        
        # 计算误差
        error = expert_score - current_avg
        
        # 调整权重
        for dimension, score in current_scores.items():
            if dimension not in weight_adjustments:
                weight_adjustments[dimension] = 0.0
            # 误差越大，调整越多
            weight_adjustments[dimension] += error * score * learning_rate
    
    # 应用调整
    for dimension, adjustment in weight_adjustments.items():
        current_weight = engine.weight_manager.get_dimension_weight(dimension)
        new_weight = max(0.1, current_weight + adjustment)
        engine.weight_manager.set_dimension_weight(dimension, new_weight)
    
    return engine.weight_manager.config.dimension_weights
```

## 配置文件示例

```json
{
  "weight_profiles": {
    "default": {
      "description": "默认均衡权重",
      "dimension_weights": {
        "functionality": 1.0,
        "innovation": 1.0,
        "user_experience": 1.0,
        "technical": 1.0,
        "market_value": 1.0
      }
    },
    "innovation_focused": {
      "description": "创新导向",
      "dimension_weights": {
        "functionality": 0.8,
        "innovation": 1.5,
        "user_experience": 1.0,
        "technical": 0.9,
        "market_value": 1.0
      }
    },
    "enterprise": {
      "description": "企业级应用",
      "dimension_weights": {
        "functionality": 1.2,
        "innovation": 0.8,
        "user_experience": 1.0,
        "technical": 1.3,
        "market_value": 1.0
      }
    }
  },
  "active_profile": "default"
}
```

## 注意事项

1. **权重范围**：建议权重在 0.5-2.0 之间，过大或过小会导致评分失衡
2. **归一化**：使用前建议归一化权重，避免总分超出范围
3. **校准**：使用专家数据校准权重，提高评分准确性
4. **版本管理**：记录权重调整历史，便于回溯
5. **A/B 测试**：重大权重调整前进行 A/B 测试

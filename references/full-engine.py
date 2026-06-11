"""
通用规则引擎自动评分
基于关键词匹配 + 统计特征的多维度自动评分

用法:
    python full-engine.py --input data.json --output scored.json
    python full-engine.py --input data.json --output scored.json --dry-run
    python full-engine.py --input data.json --output scored.json --keywords custom_kw.json
    python full-engine.py --input data.json --output scored.json --tune
    python full-engine.py --input data.json --output scored.json --output-format csv
    python full-engine.py --keywords custom_kw.json --validate
    python full-engine.py --version

依赖: 仅 Python 标准库（json, argparse, os, logging, collections, dataclasses）
     可选: pip install tqdm  # 进度条支持
"""
import json
import argparse
import csv
import os
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional, Union

__version__ = "1.2.0"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# 可选依赖
try:
    from tqdm import tqdm  # type: ignore

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    logger.info("tqdm 未安装，将使用简易进度提示。安装: pip install tqdm")


# =============================================================================
# 评分配置
# =============================================================================

@dataclass
class ScoringConfig:
    """评分配置数据类——集中管理所有魔法数字"""

    # 基础分与上限
    BASE_SCORE: float = 5.0          # 评分起点（中点）
    MAX_SCORE: float = 10.0          # 评分上限

    # 关键词加分系数
    KW_BONUS_PER_HIT: float = 0.3    # 每个命中关键词的加分
    KW_BONUS_CAP: float = 1.5        # 同类关键词加分上限

    # 维度权重（用于加权平均计算 avgScore）
    DIM_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "functionality": 0.20,
        "innovation": 0.25,
        "ux": 0.15,
        "visual": 0.15,
        "techDifficulty": 0.15,
        "practicality": 0.10,
    })

    # 特殊类别加分系数（如 AI 相关关键词给予更高加成）
    SPECIAL_CATEGORIES: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "ai": (0.5, 2.0),  # (per_hit, cap)
    })

    # 统计特征加分参数
    STAT_FUNC_WC_THRESHOLD: int = 1000   # 功能维度字数阈值
    STAT_FUNC_WC_BONUS_CAP: float = 1.5
    STAT_FUNC_IMGS_THRESHOLD: int = 5
    STAT_FUNC_IMGS_BONUS_CAP: float = 1.0
    STAT_VISUAL_IMGS_BONUS_CAP: float = 2.0
    STAT_TECH_WC_THRESHOLD: int = 2000
    STAT_TECH_WC_BONUS_CAP: float = 1.0
    STAT_TECH_CODE_BONUS_CAP: float = 1.5
    STAT_PRACT_VOTES_BONUS_CAP: float = 1.0
    STAT_PRACT_REPLIES_BONUS_CAP: float = 0.5

    # 等级阈值
    GRADE_S: float = 8.0
    GRADE_A: float = 6.5
    GRADE_B: float = 5.0

    # 调优分位
    TUNE_S_PERCENTILE: float = 0.90   # S 级取 Top 10%
    TUNE_A_PERCENTILE: float = 0.60   # A 级取 Top 40%
    TUNE_B_PERCENTILE: float = 0.30   # B 级取 Top 70%

    # 五星制阈值
    STAR_5: float = 9.0
    STAR_4: float = 7.5
    STAR_3: float = 6.0
    STAR_2: float = 4.0


# 默认配置实例
DEFAULT_CONFIG = ScoringConfig()


# =============================================================================
# 评分维度定义
# =============================================================================

SCORE_DIMS: List[str] = [
    "functionality", "innovation", "ux", "visual", "techDifficulty", "practicality"
]

# 维度中文标签
DIM_LABELS: Dict[str, str] = {
    "functionality": "功能完整度",
    "innovation": "创新性",
    "ux": "交互体验",
    "visual": "视觉设计",
    "techDifficulty": "技术难度",
    "practicality": "实用价值",
}


# =============================================================================
# 关键词库（用户自定义）
# =============================================================================

KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "functionality": {
        "core": ["核心功能", "功能模块", "主要功能", "feature", "module"],
        "advanced": ["api", "接口", "sdk", "插件", "扩展", "webhook", "自动化"],
        "process": ["流程图", "架构图", "技术方案", "实现方式", "使用方法"],
        "quality": ["开源", "github", "部署", "上线", "release", "测试"],
    },
    "innovation": {
        "novelty": ["首创", "独特", "原创", "脑洞", "创新", "创意", "颠覆"],
        "uniqueness": ["差异化", "不同于", "自研", "特有", "专有"],
        "approach": ["新思路", "新方法", "新方案", "重新定义", "打破"],
        "ai": ["ai", "machine learning", "深度学习", "gpt", "llm", "大模型", "智能"],
    },
    "ux": {
        "design": ["ui", "ux", "用户体验", "交互设计", "界面设计", "原型"],
        "responsive": ["响应式", "自适应", "移动端", "多端", "适配"],
        "polish": ["动画", "过渡", "流畅", "丝滑", "直觉", "易用"],
        "demo": ["demo", "演示", "预览", "在线体验", "试用"],
    },
    "visual": {
        "design": ["设计", "视觉", "美观", "配色", "主题", "风格"],
        "asset": ["图标", "插图", "动效", "品牌", "logo"],
        "figma": ["figma", "sketch", "design system", "组件库"],
    },
    "techDifficulty": {
        "backend": ["后端", "数据库", "server", "服务器", "api", "微服务", "分布式"],
        "frontend": ["前端", "react", "vue", "typescript", "webgl", "canvas"],
        "complex": ["架构", "并发", "性能优化", "缓存", "安全", "加密"],
        "infra": ["docker", "k8s", "ci/cd", "云", "部署", "运维"],
    },
    "practicality": {
        "problem": ["痛点", "需求", "场景", "解决", "问题", "实际"],
        "user": ["用户", "使用", "实用", "日常", "效率", "生产力"],
        "market": ["市场", "商业", "盈利", "变现", "目标用户", "人群"],
        "feedback": ["好评", "反馈", "投票", "star", "下载", "使用量"],
    },
}


def load_keywords_from_file(filepath: str) -> Dict[str, Dict[str, List[str]]]:
    """从外部 JSON 文件加载关键词库

    Args:
        filepath: 关键词配置文件路径（JSON 格式）

    Returns:
        关键词库字典，格式与 KEYWORDS 一致

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式错误
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            kws = json.load(f)
    except FileNotFoundError:
        logger.error("关键词配置文件不存在: %s", filepath)
        raise
    except json.JSONDecodeError as e:
        logger.error("关键词配置文件 JSON 格式错误: %s", e)
        raise

    # 校验结构
    if not isinstance(kws, dict):
        raise ValueError("关键词配置必须是 JSON 对象（dict）")
    for dim_name, categories in kws.items():
        if not isinstance(categories, dict):
            raise ValueError(f"维度 '{dim_name}' 的值必须是对象（dict）")
        for cat_name, words in categories.items():
            if not isinstance(words, list):
                raise ValueError(
                    f"维度 '{dim_name}' 的类别 '{cat_name}' 的值必须是数组（list）"
                )
    logger.info("已从 %s 加载 %d 个维度的关键词库", filepath, len(kws))
    return kws


def validate_keywords(kws: Dict[str, Dict[str, List[str]]]) -> List[str]:
    """校验关键词库，返回冲突列表

    检查项：
    1. 类别内重复关键词
    2. 跨维度共享关键词（允许但需提示）
    3. 关键词覆盖度（每个维度至少 5 个关键词）
    4. 关键词长度过短（≤2 字符可能过于泛化）

    Args:
        kws: 关键词库字典

    Returns:
        警告/错误信息列表，空列表表示校验通过
    """
    warnings: List[str] = []

    # 1. 类别内重复
    for dim, categories in kws.items():
        for cat, words in categories.items():
            seen: Dict[str, int] = {}
            for w in words:
                seen[w] = seen.get(w, 0) + 1
            dupes = [w for w, cnt in seen.items() if cnt > 1]
            if dupes:
                warnings.append(f"[重复] {dim}/{cat} 类别内重复关键词: {dupes}")

    # 2. 跨维度共享
    word_to_dims: Dict[str, set] = {}
    for dim, categories in kws.items():
        for words in categories.values():
            for w in words:
                word_to_dims.setdefault(w, set()).add(dim)
    for w, dims in word_to_dims.items():
        if len(dims) > 1:
            warnings.append(f"[跨维度] '{w}' 同时出现在 {dims} 中")

    # 3. 覆盖度检查
    for dim, categories in kws.items():
        total = sum(len(words) for words in categories.values())
        if total < 5:
            warnings.append(f"[覆盖度] {dim} 仅 {total} 个关键词（建议 ≥5）")

    # 4. 泛化关键词检测
    for dim, categories in kws.items():
        for cat, words in categories.items():
            overly_generic = [w for w in words if len(w) <= 2]
            if overly_generic:
                warnings.append(
                    f"[泛化] {dim}/{cat} 含短关键词: {overly_generic}（≤2 字符可能太泛）"
                )

    return warnings


def export_to_csv(projects: List[Dict[str, Any]], output_path: str) -> None:
    """将评分结果导出为 CSV 文件

    输出列：topicId, title, avgScore, qualityGrade, stars,
           functionality, innovation, ux, visual, techDifficulty, practicality,
           oneLiner, strengths, weaknesses

    Args:
        projects: 已评分的项目列表
        output_path: 输出 CSV 文件路径
    """
    fieldnames = [
        "topicId", "title", "avgScore", "qualityGrade", "stars",
        "functionality", "innovation", "ux", "visual", "techDifficulty",
        "practicality", "oneLiner", "strengths", "weaknesses",
    ]
    try:
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for p in projects:
                row: Dict[str, Any] = {
                    "topicId": p.get("topicId", ""),
                    "title": p.get("title", ""),
                    "avgScore": p.get("avgScore", ""),
                    "qualityGrade": p.get("qualityGrade", ""),
                    "stars": p.get("stars", ""),
                    "oneLiner": p.get("oneLiner", ""),
                    "strengths": " | ".join(p.get("strengths", [])),
                    "weaknesses": " | ".join(p.get("weaknesses", [])),
                }
                scores = p.get("scores", {})
                for dim in SCORE_DIMS:
                    row[dim] = scores.get(dim, "")
                writer.writerow(row)
        logger.info("CSV 已导出至 %s（%d 行）", output_path, len(projects))
    except OSError as e:
        logger.error("写入 CSV 失败: %s", e)
        raise SystemExit(3)


# =============================================================================
# 统计特征评分
# =============================================================================

def score_stat_features(
    text: str,
    wc: int,
    imgs: int,
    dim: str,
    engagement: Dict[str, int],
    config: ScoringConfig = DEFAULT_CONFIG,
) -> float:
    """计算统计特征维度的加分

    根据维度不同，基于字数、图片数、代码块数、投票/回复数
    等可量化客观指标计算加分。

    Args:
        text: 项目正文（小写）
        wc: 正文字数
        imgs: 图片数量
        dim: 评分维度名
        engagement: 互动数据字典，包含 votes 和 replies
        config: 评分配置

    Returns:
        统计特征加分（0 ~ 最大值）
    """
    bonus = 0.0

    if dim == "functionality":
        if wc > config.STAT_FUNC_WC_THRESHOLD:
            bonus += min(
                (wc - config.STAT_FUNC_WC_THRESHOLD) / 1000,
                config.STAT_FUNC_WC_BONUS_CAP,
            )
        if imgs > config.STAT_FUNC_IMGS_THRESHOLD:
            bonus += min(
                (imgs - config.STAT_FUNC_IMGS_THRESHOLD) / 20,
                config.STAT_FUNC_IMGS_BONUS_CAP,
            )
    elif dim == "visual":
        if imgs > 0:
            bonus += min(imgs / 10, config.STAT_VISUAL_IMGS_BONUS_CAP)
    elif dim == "techDifficulty":
        code_blocks = text.count("```") // 2
        if code_blocks > 0:
            bonus += min(code_blocks / 5, config.STAT_TECH_CODE_BONUS_CAP)
        if wc > config.STAT_TECH_WC_THRESHOLD:
            bonus += min(
                (wc - config.STAT_TECH_WC_THRESHOLD) / 2000,
                config.STAT_TECH_WC_BONUS_CAP,
            )
    elif dim == "practicality":
        votes = engagement.get("votes", 0)
        if votes > 0:
            bonus += min(votes / 30, config.STAT_PRACT_VOTES_BONUS_CAP)
        # 注意：数据契约中字段名为 replyCount，但在评分引擎内部统一映射为 replies
        replies = engagement.get("replies", 0)
        if replies > 0:
            bonus += min(replies / 10, config.STAT_PRACT_REPLIES_BONUS_CAP)

    return bonus


# =============================================================================
# 关键词评分
# =============================================================================

def score_keywords(
    text: str,
    dim: str,
    kws: Dict[str, Dict[str, List[str]]],
    config: ScoringConfig = DEFAULT_CONFIG,
) -> float:
    """计算关键词匹配维度的加分

    遍历维度下的所有类别，每个类别独立计分，
    同类关键词共享一个加分上限，防止关键词堆砌刷分。
    特殊类别（如 AI）按配置给予更高加成。

    使用正则批量匹配（将同类别所有关键词编译为一个正则），
    复杂度从 O(N*M) 降至 O(N)，M 为关键词总数。

    Args:
        text: 项目正文（小写）
        dim: 评分维度名
        kws: 关键词库
        config: 评分配置

    Returns:
        关键词加分（0 ~ 各维度上限之和）
    """
    bonus = 0.0
    dim_kws = kws.get(dim, {})

    for category, words in dim_kws.items():
        if not words:
            continue
        # 批量正则匹配：将同类关键词用 | 连接，匹配所有命中
        pattern = "|".join(re.escape(w) for w in words)
        hit_count = len(re.findall(pattern, text))
        if hit_count > 0:
            # 检查是否为特殊类别
            if category in config.SPECIAL_CATEGORIES:
                per_hit, cap = config.SPECIAL_CATEGORIES[category]
            else:
                per_hit = config.KW_BONUS_PER_HIT
                cap = config.KW_BONUS_CAP
            bonus += min(hit_count * per_hit, cap)

    return bonus


# =============================================================================
# 单维度评分
# =============================================================================

def score_one_dim(
    text: str,
    wc: int,
    imgs: int,
    dim: str,
    engagement: Dict[str, int],
    kws: Dict[str, Dict[str, List[str]]],
    config: ScoringConfig = DEFAULT_CONFIG,
) -> float:
    """计算单个维度的综合分数

    统合统计特征加分与关键词加分，从基础分出发，
    累加两类加分后限制在评分上限内。

    Args:
        text: 项目正文（小写）
        wc: 正文字数
        imgs: 图片数量
        dim: 评分维度名
        engagement: 互动数据字典，包含 votes 和 replies
        kws: 关键词库
        config: 评分配置

    Returns:
        维度得分（四舍五入到一位小数，0 ~ MAX_SCORE）
    """
    score = config.BASE_SCORE
    score += score_stat_features(text, wc, imgs, dim, engagement, config)
    score += score_keywords(text, dim, kws, config)
    return round(min(config.MAX_SCORE, score), 1)


# =============================================================================
# 项目评分
# =============================================================================

def score_project(
    project: Dict[str, Any],
    kws: Dict[str, Dict[str, List[str]]],
    config: ScoringConfig = DEFAULT_CONFIG,
) -> Dict[str, Any]:
    """对单个项目进行六维度评分

    注意：数据契约中的 replyCount 字段在引擎内部统一映射为 replies。
    该映射仅用于接收外部数据，内部均以 replies 为键名。

    Args:
        project: 项目数据字典
        kws: 关键词库
        config: 评分配置

    Returns:
        包含 scores 和 avgScore 的字典
    """
    text = (project.get("title", "") + " " + project.get("rawText", "")).lower()
    wc = len(project.get("rawText", ""))
    imgs = project.get("imageCount", 0)

    # 数据契约中字段名为 replyCount，引擎内部统一映射为 replies
    engagement: Dict[str, int] = {
        "votes": project.get("votes", 0),
        "replies": project.get("replyCount", 0),
    }

    scores: Dict[str, float] = {}
    for dim in SCORE_DIMS:
        scores[dim] = score_one_dim(text, wc, imgs, dim, engagement, kws, config)

    # 加权平均（按 DIM_WEIGHTS 配置的权重）
    avg = round(sum(
        scores[d] * config.DIM_WEIGHTS.get(d, 1.0 / len(SCORE_DIMS))
        for d in SCORE_DIMS
    ), 1)
    return {"scores": scores, "avgScore": avg}


# =============================================================================
# 等级划分
# =============================================================================

def assign_grade(avg_score: float, config: ScoringConfig = DEFAULT_CONFIG) -> str:
    """根据均分自动划分等级

    Args:
        avg_score: 平均得分
        config: 评分配置

    Returns:
        等级字符串: "S" / "A" / "B" / "C"
    """
    if avg_score >= config.GRADE_S:
        return "S"
    elif avg_score >= config.GRADE_A:
        return "A"
    elif avg_score >= config.GRADE_B:
        return "B"
    else:
        return "C"


def assign_stars(avg_score: float, config: ScoringConfig = DEFAULT_CONFIG) -> int:
    """将均分转换为五星制评分

    Args:
        avg_score: 平均得分
        config: 评分配置

    Returns:
        星级数（1~5）
    """
    if avg_score >= config.STAR_5:
        return 5
    elif avg_score >= config.STAR_4:
        return 4
    elif avg_score >= config.STAR_3:
        return 3
    elif avg_score >= config.STAR_2:
        return 2
    else:
        return 1


def to_percentile(avg_score: float, all_scores: List[float]) -> int:
    """将分数映射到百分位

    Args:
        avg_score: 目标分数
        all_scores: 所有项目的分数列表

    Returns:
        百分位值（0~100）
    """
    if not all_scores:
        return 0
    rank = sum(1 for s in all_scores if s < avg_score)
    return round(rank / len(all_scores) * 100)


# =============================================================================
# 输入数据校验
# =============================================================================

def validate_project(project: Dict[str, Any], index: int) -> List[str]:
    """校验单个项目数据的必填字段

    Args:
        project: 项目数据字典
        index: 项目在列表中的索引（从 0 开始）

    Returns:
        错误信息列表，为空表示校验通过
    """
    errors: List[str] = []
    for field in ("topicId", "title", "rawText"):
        if field not in project or not project[field]:
            errors.append(f"项目 #{index + 1} 缺少必填字段 '{field}'")
    return errors


def validate_input(projects: List[Dict[str, Any]]) -> bool:
    """校验全部输入数据，打印错误并返回是否通过

    Args:
        projects: 项目数据列表

    Returns:
        True 如果所有项目校验通过
    """
    all_errors: List[str] = []
    for i, p in enumerate(projects):
        all_errors.extend(validate_project(p, i))

    if all_errors:
        logger.error("输入数据校验失败，共 %d 个错误:", len(all_errors))
        for err in all_errors:
            logger.error("  - %s", err)
        return False

    logger.info("输入数据校验通过，共 %d 个项目", len(projects))
    return True


# =============================================================================
# 衍生分析
# =============================================================================

def identify_one_liner(project: Dict[str, Any], scores: Dict[str, float]) -> str:
    """根据最高分维度生成一句话描述

    Args:
        project: 项目数据字典（保留以兼容扩展）
        scores: 各维度得分

    Returns:
        一句话描述字符串
    """
    high_dims = sorted(SCORE_DIMS, key=lambda d: scores.get(d, 0), reverse=True)
    top = [DIM_LABELS[d] for d in high_dims[:2]]
    return f"以{'和'.join(top)}为亮点的产品"


def quick_swot(
    project: Dict[str, Any], scores: Dict[str, float]
) -> Tuple[List[str], List[str]]:
    """快速 SWOT 分析

    Args:
        project: 项目数据字典（保留以兼容扩展）
        scores: 各维度得分

    Returns:
        (strengths, weaknesses) 元组
    """
    strengths: List[str] = []
    weaknesses: List[str] = []

    thresholds: Dict[str, Tuple[int, str, str]] = {
        "functionality": (7, "功能完整，描述详尽", "功能描述不够具体"),
        "innovation": (7, "概念新颖，有独创性", "创新点不够突出"),
        "ux": (7, "重视用户体验设计", "交互设计较薄弱"),
        "visual": (7, "视觉设计出色", "视觉呈现较粗糙"),
        "techDifficulty": (7, "技术实现复杂，有深度", "技术实现较简单"),
        "practicality": (7, "实用价值突出，解决真实问题", "实用价值待验证"),
    }

    for dim, (t, s_text, w_text) in thresholds.items():
        if scores.get(dim, 0) >= t:
            strengths.append(s_text)
        elif scores.get(dim, 0) < 5:
            weaknesses.append(w_text)

    return strengths, weaknesses


# =============================================================================
# 阈值调优
# =============================================================================

def tune_grade_thresholds(
    projects: List[Dict[str, Any]], config: ScoringConfig = DEFAULT_CONFIG
) -> None:
    """根据实际分布建议阈值调整

    Args:
        projects: 已评分项目列表
        config: 评分配置
    """
    avgs = [p.get("avgScore", 0) for p in projects]
    avgs.sort()

    n = len(avgs)
    if n == 0:
        logger.warning("无数据，无法建议阈值")
        return

    s_threshold = avgs[min(int(n * config.TUNE_S_PERCENTILE), n - 1)]
    a_threshold = avgs[min(int(n * config.TUNE_A_PERCENTILE), n - 1)]
    b_threshold = avgs[min(int(n * config.TUNE_B_PERCENTILE), n - 1)]

    logger.info("根据 %d 个项目分布，建议阈值:", n)
    logger.info("  S: >= %.1f", round(s_threshold, 1))
    logger.info("  A: >= %.1f", round(a_threshold, 1))
    logger.info("  B: >= %.1f", round(b_threshold, 1))
    logger.info("  C: <  %.1f", round(b_threshold, 1))


# =============================================================================
# 抽样验证（dry-run）
# =============================================================================

def dry_run_sample(
    projects: List[Dict[str, Any]],
    kws: Dict[str, Dict[str, List[str]]],
    config: ScoringConfig = DEFAULT_CONFIG,
    sample_size: int = 5,
) -> None:
    """抽样评分以验证关键词库效果

    对前 sample_size 个项目实际评分并打印详细结果，
    帮助用户判断关键词库是否合理。

    Args:
        projects: 项目数据列表
        kws: 关键词库
        config: 评分配置
        sample_size: 抽样数量
    """
    sample = projects[:sample_size]
    logger.info("=== Dry-Run 抽样验证（前 %d 条）===", len(sample))

    for i, p in enumerate(sample):
        result = score_project(p, kws, config)
        logger.info("--- 项目 #%d: %s ---", i + 1, p.get("title", "无标题")[:50])
        logger.info("  字数: %d, 图片: %d", len(p.get("rawText", "")), p.get("imageCount", 0))
        for dim in SCORE_DIMS:
            logger.info("  %s: %.1f", DIM_LABELS.get(dim, dim), result["scores"].get(dim, 0))
        logger.info("  均分: %.1f, 等级: %s", result["avgScore"], assign_grade(result["avgScore"], config))

    # 关键词命中统计
    logger.info("=== 关键词命中率概览 ===")
    full_text = " ".join(p.get("rawText", "") + " " + p.get("title", "") for p in sample).lower()
    for dim in SCORE_DIMS:
        total_kw = 0
        hit_kw = 0
        for cat, words in kws.get(dim, {}).items():
            for w in words:
                total_kw += 1
                if w in full_text:
                    hit_kw += 1
        hit_rate = hit_kw / total_kw * 100 if total_kw > 0 else 0
        logger.info("  %s: %d/%d 关键词命中 (%.0f%%)",
                    DIM_LABELS.get(dim, dim), hit_kw, total_kw, hit_rate)

    logger.info("=== Dry-Run 结束，请根据命中率调整关键词库 ===")


# =============================================================================
# 主流程
# =============================================================================

def run(
    input_path: str,
    output_path: str,
    kws: Dict[str, Dict[str, List[str]]],
    tune: bool = False,
    output_format: str = "json",
    config: ScoringConfig = DEFAULT_CONFIG,
) -> None:
    """主评分流程

    Args:
        input_path: 输入 JSON 文件路径
        output_path: 输出文件路径
        kws: 关键词库
        tune: 是否输出阈值调优建议
        output_format: 输出格式 ("json" 或 "csv")
        config: 评分配置
    """
    # 读取输入数据
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("输入文件不存在: %s", input_path)
        raise SystemExit(2)
    except json.JSONDecodeError as e:
        logger.error("输入文件 JSON 格式错误: %s", e)
        raise SystemExit(2)

    # 解析项目列表
    if isinstance(data, list):
        projects: List[Dict[str, Any]] = data
    else:
        projects = data.get("projects", [])

    logger.info("加载 %d 个项目", len(projects))

    if not projects:
        logger.warning("没有可评分的项目")
        return

    # 输入校验
    if not validate_input(projects):
        logger.warning("存在数据缺陷，继续评分但结果可能不完整")

    # 评分循环
    progress_iter: Any
    if HAS_TQDM:
        progress_iter = tqdm(projects, desc="评分中", unit="item")
    else:
        progress_iter = projects

    for i, p in enumerate(progress_iter):
        result = score_project(p, kws, config)
        p["scores"] = result["scores"]
        p["avgScore"] = result["avgScore"]
        p["qualityGrade"] = assign_grade(result["avgScore"], config)
        p["stars"] = assign_stars(result["avgScore"], config)
        p["oneLiner"] = identify_one_liner(p, result["scores"])

        strengths, weaknesses = quick_swot(p, result["scores"])
        p["strengths"] = strengths
        p["weaknesses"] = weaknesses

        # 简易进度提示（无 tqdm 时）
        if not HAS_TQDM and (i + 1) % 100 == 0:
            logger.info("已评分 %d/%d", i + 1, len(projects))

    # 统计分布
    grades = Counter(p.get("qualityGrade", "?") for p in projects)
    logger.info("评分完成: %d 个项目", len(projects))
    for grade in ["S", "A", "B", "C"]:
        count = grades.get(grade, 0)
        pct = count / len(projects) * 100 if projects else 0
        logger.info("  %s: %d (%.1f%%)", grade, count, pct)

    # 百分位参考（基于全量分数）
    all_avgs = [p.get("avgScore", 0) for p in projects]
    all_avgs.sort()
    logger.info("分数分布: min=%.1f, p25=%.1f, p50=%.1f, p75=%.1f, max=%.1f",
                all_avgs[0] if all_avgs else 0,
                all_avgs[len(all_avgs)//4] if all_avgs else 0,
                all_avgs[len(all_avgs)//2] if all_avgs else 0,
                all_avgs[len(all_avgs)*3//4] if all_avgs else 0,
                all_avgs[-1] if all_avgs else 0)

    # 建议阈值
    if tune:
        tune_grade_thresholds(projects, config)

    # 写入输出
    try:
        if output_format == "csv":
            export_to_csv(projects, output_path)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(projects, f, ensure_ascii=False, indent=2)
            logger.info("JSON 已保存至 %s", output_path)
    except OSError as e:
        logger.error("写入输出文件失败: %s", e)
        raise SystemExit(3)


# =============================================================================
# CLI 入口
# =============================================================================

def main() -> None:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="Rule Scoring Engine - 基于关键词匹配+统计特征的多维度自动评分引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python %(prog)s --input data.json --output scored.json
  python %(prog)s --input data.json --output scored.json --tune
  python %(prog)s --input data.json --output scored.json --dry-run
  python %(prog)s --input data.json --output scored.json --keywords custom_kw.json
        """.strip(),
    )
    parser.add_argument(
        "--input", default=None,
        help="Path to input JSON file (projects list)",
    )
    parser.add_argument(
        "--output", default="scored.json",
        help="Path to output JSON file (default: scored.json)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview scoring on a sample of projects to validate keyword effectiveness",
    )
    parser.add_argument(
        "--tune", action="store_true",
        help="Suggest grade thresholds based on score distribution",
    )
    parser.add_argument(
        "--keywords", default=None,
        help="Path to external keyword config file (JSON format). "
             "If not provided, uses built-in default keywords.",
    )
    parser.add_argument(
        "--dry-run-size", type=int, default=5,
        help="Number of projects to sample in dry-run mode (default: 5)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress all output except errors (exit code only)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable debug-level logging output",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Print version and exit",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate keyword config and exit without scoring",
    )
    parser.add_argument(
        "--output-format", default="json", choices=["json", "csv"],
        help="Output format: json (default) or csv",
    )
    args = parser.parse_args()

    # --version 优先
    if args.version:
        logger.info("rule-scoring-engine v%s", __version__)
        return

    # 配置日志级别
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 加载关键词库（--version 外均需要）
    if args.keywords:
        try:
            kws = load_keywords_from_file(args.keywords)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.error("加载关键词配置失败: %s", e)
            raise SystemExit(2)
    else:
        kws = KEYWORDS
        logger.info("使用内置默认关键词库")

    # --validate：仅校验关键词，不需要 --input
    if args.validate:
        warnings = validate_keywords(kws)
        if warnings:
            logger.warning("关键词配置校验发现 %d 个问题:", len(warnings))
            for w in warnings:
                logger.warning("  - %s", w)
            raise SystemExit(1)
        else:
            logger.info("关键词配置校验通过，无问题")
        return

    # 其他模式需要 --input
    if not args.input:
        logger.error("缺少必需参数 --input（除 --version 和 --validate 外均需要）")
        raise SystemExit(1)

    config = DEFAULT_CONFIG

    if args.dry_run:
        # 读取输入数据进行抽样
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error("输入文件不存在: %s", args.input)
            raise SystemExit(2)
        except json.JSONDecodeError as e:
            logger.error("输入文件 JSON 格式错误: %s", e)
            raise SystemExit(2)

        if isinstance(data, list):
            projects = data
        else:
            projects = data.get("projects", [])

        if not projects:
            logger.warning("没有可抽样的项目")
            return

        logger.info("评分维度: %s", SCORE_DIMS)
        for dim in SCORE_DIMS:
            total_kw = sum(len(words) for words in kws.get(dim, {}).values())
            logger.info("  %s: %d 个关键词，%d 个类别",
                        DIM_LABELS.get(dim, dim), total_kw, len(kws.get(dim, {})))

        dry_run_sample(projects, kws, config, sample_size=args.dry_run_size)
    else:
        run(args.input, args.output, kws, tune=args.tune, output_format=args.output_format, config=config)


if __name__ == "__main__":
    main()
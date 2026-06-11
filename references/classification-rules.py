#!/usr/bin/env python3
"""
通用产品分类规则模块
为规则评分引擎提供开箱即用的分类能力

用法（作为模块导入）:
    from classification_rules import (
        classify_product_type, classify_batch,
        PRODUCT_TYPE_KEYWORDS, load_classification_config,
    )

用法（独立运行）:
    python classification_rules.py --text "这是一款AI绘画工具" --track Code
    python classification_rules.py --text "在线教育平台" --config custom_classification.json
    python classification_rules.py --text "在线教育平台" --verbose
    python classification_rules.py --input scored.json --output classified.csv
"""
import argparse
import csv
import json
import logging
import re
from typing import Dict, List, Tuple, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# 赛道映射
# =============================================================================

TRACK_MAP: Dict[str, str] = {
    # 将输入的赛道标签映射到统一格式
    "AI应用": "AI-Application",
    "前端": "Frontend",
    "后端": "Backend",
    "全栈": "Fullstack",
    "移动端": "Mobile",
    "桌面端": "Desktop",
    "游戏": "Game",
    "工具": "Tool",
    "公益": "Public-Welfare",
    "数据": "Data",
    "DevOps": "DevOps",
    "安全": "Security",
}

# 赛道→分类加权：某些赛道下特定分类的优先级更高
TRACK_CLASSIFICATION_BOOST: Dict[str, Dict[str, float]] = {
    "Game": {"游戏": 0.3},
    "AI-Application": {"AI": 0.3},
    "Frontend": {"设计": 0.2},
    "Backend": {"工具": 0.2},
    "Mobile": {"工具": 0.1, "社交": 0.1},
    "Data": {"工具": 0.2, "金融": 0.1},
    "Security": {"工具": 0.2},
}


# =============================================================================
# 产品类型关键词
# =============================================================================

PRODUCT_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "游戏": [
        "游戏", "game", "玩法", "关卡", "角色", "player", "闯关", "boss",
        "rpg", "像素", "冒险", "棋牌", "解谜", "模拟经营", "养成", "卡牌",
        "unity", "unreal", "godot", "cocos",
    ],
    "教育": [
        "学习", "教育", "课程", "教学", "培训", "知识", "答题", "考试",
        "student", "learn", "edu", "题目", "老师", "学生", "记忆",
        "课堂", "刷题", "背单词", "编程入门",
    ],
    "工具": [
        "工具", "tool", "效率", "自动化", "生成", "管理", "插件", "转换",
        "分析", "查询", "助手", "辅助", "calendar", "浏览器", "搜索",
        "计算器", "检测", "扫描", "清理", "优化",
    ],
    "求职": [
        "简历", "面试", "求职", "招聘", "职业", "career", "job", "resume",
        "offer", "工作",
    ],
    "内容": [
        "博客", "内容", "写作", "文案", "content", "blog", "阅读", "news",
        "文章", "笔记", "日记", "社区", "文档", "翻译", "markdown",
    ],
    "健康": [
        "健康", "医疗", "医院", "心理", "health", "康复", "药物", "患者",
        "疾病", "doctor", "养老", "睡眠", "运动", "饮食", "养生", "冥想",
    ],
    "社交": [
        "社交", "聊天", "通讯", "匹配", "交友", "social", "chat", "朋友",
        "社区", "论坛", "评论", "互动",
    ],
    "金融": [
        "理财", "投资", "股票", "基金", "保险", "金融", "finance",
        "交易", "支付", "预算", "记账", "贷款",
    ],
    "设计": [
        "设计", "design", "figma", "sketch", "原型", "prototype",
        "UI", "UX", "界面", "视觉", "品牌", "logo",
    ],
    "AI": [
        "AI", "人工智能", "机器学习", "深度学习", "大模型", "LLM",
        "ChatGPT", "GPT", "Agent", "智能体", "神经网络",
    ],
}

# 科技/创新关键词 —— 优先级最高
TECH_INNOVATION_KW: List[str] = [
    "AI", "智能", "agent", "机器人", "大模型", "LLM", "GPT", "ChatGPT",
    "自动化", "神经网络", "深度学习", "NLP", "CV", "RAG", "向量",
    "语音识别", "图像识别", "AR", "VR", "IoT", "物联网",
]

# 工具/效率关键词 —— 默认类型
TOOL_KW: List[str] = [
    "工具", "助手", "管理", "分析", "生成", "转换",
    "搜索", "计算", "查询", "监控", "检测", "优化",
    "日历", "待办", "笔记", "提醒",
]


# =============================================================================
# 配置加载
# =============================================================================

def load_classification_config(
    filepath: str,
) -> Dict[str, List[str]]:
    """从外部 JSON 文件加载分类关键词配置

    Args:
        filepath: 配置文件路径（JSON 格式）

    Returns:
        分类关键词字典，格式与 PRODUCT_TYPE_KEYWORDS 一致

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式错误
        ValueError: 结构校验失败
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        logger.error("分类配置文件不存在: %s", filepath)
        raise
    except json.JSONDecodeError as e:
        logger.error("分类配置文件 JSON 格式错误: %s", e)
        raise

    if not isinstance(cfg, dict):
        raise ValueError("分类配置必须是 JSON 对象（dict）")

    for cat_name, keywords in cfg.items():
        if not isinstance(keywords, list):
            raise ValueError(
                f"分类 '{cat_name}' 的关键词必须是数组（list）"
            )

    logger.info("已从 %s 加载 %d 个分类的关键词配置", filepath, len(cfg))
    return cfg


# =============================================================================
# 分类函数
# =============================================================================

def _compute_confidence(
    hits: int, total_keywords: int, tech_boost: float = 0.0, track_boost: float = 0.0
) -> float:
    """计算分类置信度

    Args:
        hits: 命中的关键词数
        total_keywords: 该分类的总关键词数
        tech_boost: 科技/创新加分
        track_boost: 赛道加权加分

    Returns:
        置信度分值（0.0 ~ 1.0）
    """
    if total_keywords == 0:
        return 0.0
    base = min(hits / total_keywords, 1.0)
    return round(min(base + tech_boost + track_boost, 1.0), 2)


def classify_product_type(
    text: str, track: str = "", verbose: bool = False
) -> Tuple[str, float]:
    """根据文本内容分类产品类型，返回分类结果和置信度

    分类策略：
    1. 优先匹配科技/创新类关键词（≥2 个命中即为科技工具/AI工具）
    2. 匹配各品类关键词
    3. 匹配工具类关键词
    4. 默认回退为"工具"
    5. 赛道信息用于加权特定分类的置信度

    Args:
        text: 文本内容（已转换为小写）
        track: 赛道信息（可选），用于辅助分类加权
        verbose: 是否输出命中详情

    Returns:
        (产品类型名称, 置信度) 元组
    """
    # 解析赛道到统一格式
    normalized_track = TRACK_MAP.get(track, track) if track else ""
    track_boosts: Dict[str, float] = TRACK_CLASSIFICATION_BOOST.get(
        normalized_track, {}
    )

    if verbose:
        logger.info("=== 分类命中详情 ===")
        logger.info("文本长度: %d 字符", len(text))
        if normalized_track:
            logger.info("赛道: %s → %s", track, normalized_track)
            if track_boosts:
                logger.info("赛道加权: %s", track_boosts)

    # 优先匹配科技/创新类
    tech_pattern = "|".join(re.escape(kw.lower()) for kw in TECH_INNOVATION_KW)
    tech_hits = len(re.findall(tech_pattern, text))
    if verbose:
        tech_matched = [kw for kw in TECH_INNOVATION_KW if kw.lower() in text]
        logger.info("科技/创新关键词命中 %d/%d: %s", tech_hits, len(TECH_INNOVATION_KW), tech_matched)
    if tech_hits >= 2:
        is_ai = any(kw.lower() in text for kw in ["ai", "gpt", "大模型", "agent"])
        category = "AI工具" if is_ai else "科技工具"
        confidence = _compute_confidence(
            tech_hits,
            len(TECH_INNOVATION_KW),
            tech_boost=0.3,
            track_boost=track_boosts.get("AI", 0.0),
        )
        if verbose:
            logger.info("→ 科技优先匹配: %s (置信度: %.0f%%)", category, confidence * 100)
        return (category, confidence)

    # 匹配各品类
    best_category = ""
    best_hits = 0
    best_total = 0
    all_hits: Dict[str, int] = {}

    for ptype, keywords in PRODUCT_TYPE_KEYWORDS.items():
        kw_pattern = "|".join(re.escape(kw.lower()) for kw in keywords)
        hits = len(re.findall(kw_pattern, text))
        all_hits[ptype] = hits
        if hits > best_hits:
            best_category = ptype
            best_hits = hits
            best_total = len(keywords)

    if verbose:
        for ptype, hits in sorted(all_hits.items(), key=lambda x: -x[1]):
            if hits > 0:
                matched = [kw for kw in PRODUCT_TYPE_KEYWORDS[ptype] if kw.lower() in text]
                logger.info("  %s: %d/%d 命中 → %s", ptype, hits, len(PRODUCT_TYPE_KEYWORDS[ptype]), matched[:8])

    if best_category and best_hits > 0:
        confidence = _compute_confidence(
            best_hits,
            best_total,
            track_boost=track_boosts.get(best_category, 0.0),
        )
        if verbose:
            logger.info("→ 品类匹配: %s (置信度: %.0f%%)", best_category, confidence * 100)
        return (best_category, confidence)

    # 匹配工具类
    tool_pattern = "|".join(re.escape(kw.lower()) for kw in TOOL_KW)
    tool_hits = len(re.findall(tool_pattern, text))
    if verbose:
        tool_matched = [kw for kw in TOOL_KW if kw.lower() in text]
        logger.info("工具类关键词命中 %d/%d: %s", tool_hits, len(TOOL_KW), tool_matched)
    if tool_hits > 0:
        confidence = _compute_confidence(
            tool_hits,
            len(TOOL_KW),
            track_boost=track_boosts.get("工具", 0.0),
        )
        if verbose:
            logger.info("→ 工具类匹配 (置信度: %.0f%%)", confidence * 100)
        return ("工具", confidence)

    # 默认
    if verbose:
        logger.info("→ 无关键词命中，默认分类为\"工具\"")
    return ("工具", 0.0)


def classify_batch(
    texts: List[str], track: str = ""
) -> List[Tuple[str, float]]:
    """批量分类多条文本

    Args:
        texts: 文本列表（应为小写）
        track: 赛道信息（可选），应用于所有文本

    Returns:
        [(分类, 置信度), ...] 列表
    """
    results: List[Tuple[str, float]] = []
    for text in texts:
        results.append(classify_product_type(text, track))
    return results


# =============================================================================
# 独立运行
# =============================================================================

def main() -> None:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="Rule Scoring Engine / Classification - 多维度关键词匹配的产品类型分类器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python %(prog)s --text "这是一款AI绘画工具" --track Code
  python %(prog)s --text "在线教育平台"
  python %(prog)s --text "在线教育平台" --config custom_classification.json
  python %(prog)s --text "在线教育平台" --verbose
  python %(prog)s --input scored.json --output classified.csv
        """.strip(),
    )
    parser.add_argument(
        "--text", default=None,
        help="Text to classify (product description). "
             "Use --input for batch mode instead.",
    )
    parser.add_argument(
        "--input", default=None,
        help="Path to JSON input file for batch classification. "
             "Expects projects list or {projects: [...]} format.",
    )
    parser.add_argument(
        "--output", default=None,
        help="Path to output file for batch results. "
             "Auto-detects format: .csv = CSV, else JSON (default).",
    )
    parser.add_argument(
        "--track", default="",
        help="Track label for context (e.g., Code, Game, AI应用). "
             "Used to boost classification confidence for certain categories.",
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to external classification keyword config file (JSON format). "
             "If not provided, uses built-in default keywords.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Output detailed keyword hit information for debugging (single mode only)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress all output except errors (exit code + classification result only)",
    )
    args = parser.parse_args()

    # 配置日志级别
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 加载分类关键词配置
    if args.config:
        try:
            kws = load_classification_config(args.config)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.error("加载分类配置失败: %s", e)
            raise SystemExit(2)
        global PRODUCT_TYPE_KEYWORDS
        PRODUCT_TYPE_KEYWORDS = kws
        logger.info("已替换内置分类关键词配置")
    else:
        logger.info("使用内置默认分类关键词配置")

    # 批量模式
    if args.input:
        # 读取输入
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

        logger.info("批量分类 %d 个项目", len(projects))

        # 执行分类
        for p in projects:
            text = (p.get("title", "") + " " + p.get("rawText", "")).lower()
            ptype, confidence = classify_product_type(text, args.track)
            p["productType"] = ptype
            p["classificationConfidence"] = confidence

        # 输出统计
        from collections import Counter
        type_counts = Counter(p.get("productType", "?") for p in projects)
        logger.info("分类完成:")
        for t, cnt in type_counts.most_common():
            logger.info("  %s: %d (%.1f%%)", t, cnt, cnt / len(projects) * 100)

        # 保存结果
        if args.output:
            output_path = args.output
            try:
                if output_path.endswith(".csv"):
                    # CSV 导出
                    fieldnames = [
                        "topicId", "title", "productType",
                        "classificationConfidence",
                    ]
                    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                        writer.writeheader()
                        for p in projects:
                            writer.writerow({
                                "topicId": p.get("topicId", ""),
                                "title": p.get("title", ""),
                                "productType": p.get("productType", ""),
                                "classificationConfidence": p.get("classificationConfidence", ""),
                            })
                else:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(projects, f, ensure_ascii=False, indent=2)
                logger.info("结果已保存至 %s", output_path)
            except OSError as e:
                logger.error("写入输出文件失败: %s", e)
                raise SystemExit(3)
        return

    # 单文本模式（需要 --text）
    if not args.text:
        logger.error("缺少必需参数：请提供 --text（单文本模式）或 --input（批量模式）")
        raise SystemExit(1)

    ptype, confidence = classify_product_type(
        args.text.lower(), args.track, verbose=args.verbose
    )
    logger.info("分类结果: %s (置信度: %.0f%%)", ptype, confidence * 100)
    logger.info("可用分类: %s", ", ".join(PRODUCT_TYPE_KEYWORDS.keys()))

    if args.track:
        normalized = TRACK_MAP.get(args.track, args.track)
        logger.info("赛道: %s → %s", args.track, normalized)


if __name__ == "__main__":
    main()
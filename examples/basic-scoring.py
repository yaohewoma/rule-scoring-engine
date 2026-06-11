#!/usr/bin/env python3
"""
Rule Scoring Engine — 快速入门示例
演示最简用法：导入 full-engine 核心函数，对少量项目进行评分

用法: python basic-scoring.py
依赖: Python 3.8+ (与 full-engine.py 同目录运行)
"""
import sys
import os
import json
import importlib.util

# 将 references/ 加入路径，通过 importlib 加载带连字符的模块名
_ref_dir = os.path.join(os.path.dirname(__file__), "..", "references")
_full_engine_path = os.path.join(_ref_dir, "full-engine.py")
spec = importlib.util.spec_from_file_location("full_engine", _full_engine_path)
full_engine = importlib.util.module_from_spec(spec)
sys.modules["full_engine"] = full_engine
spec.loader.exec_module(full_engine)


# ==================== 示例数据 ====================

SAMPLE_PROJECTS = [
    {
        "topicId": "001",
        "title": "AI 智能助手",
        "rawText": "这是一个基于大模型的 AI 智能助手，支持自然语言对话、代码生成、文档写作等功能。"
                   "系统采用微服务架构，支持分布式部署，具有高性能和高可用性。"
                   "UI 设计简洁直观，响应式布局适配多种设备。",
        "votes": 150,
        "imageCount": 5,
        "replyCount": 20,
    },
    {
        "topicId": "002",
        "title": "简单计算器",
        "rawText": "一个简单的计算器应用，支持基本的加减乘除运算。",
        "votes": 20,
        "imageCount": 1,
        "replyCount": 2,
    },
    {
        "topicId": "003",
        "title": "在线教育平台",
        "rawText": "创新的在线教育平台，首创互动式教学模式。"
                   "平台采用 AI 技术实现个性化学习路径推荐，支持视频课程、在线测验、学习社区等功能。"
                   "技术栈包括 React、Node.js、MongoDB，支持高并发访问。",
        "votes": 300,
        "imageCount": 10,
        "replyCount": 45,
    },
]


# ==================== 主程序 ====================

def main():
    """使用 full-engine 核心函数对示例项目进行评分并输出结果"""
    print("=" * 60)
    print("  Rule Scoring Engine — 快速入门示例")
    print("=" * 60)

    results = []
    for project in SAMPLE_PROJECTS:
        print(f"\n--- {project['title']} ---")

        # 调用 full-engine 的核心评分函数
        scored = full_engine.score_project(project, full_engine.KEYWORDS, full_engine.DEFAULT_CONFIG)
        grade = full_engine.assign_grade(scored["avgScore"], full_engine.DEFAULT_CONFIG)
        stars = full_engine.assign_stars(scored["avgScore"], full_engine.DEFAULT_CONFIG)
        one_liner = full_engine.identify_one_liner(project, scored["scores"])
        strengths, weaknesses = full_engine.quick_swot(project, scored["scores"])

        # 输出结果
        print(f"  综合分数: {scored['avgScore']}  |  等级: {grade}  |  星级: {'★' * stars}")
        print(f"  一句话: {one_liner}")
        for dim, score in scored["scores"].items():
            print(f"    {dim}: {score}")
        if strengths:
            print(f"  优势: {', '.join(strengths)}")
        if weaknesses:
            print(f"  劣势: {', '.join(weaknesses)}")

        results.append({
            **project,
            "scores": scored["scores"],
            "avgScore": scored["avgScore"],
            "qualityGrade": grade,
            "stars": stars,
            "oneLiner": one_liner,
            "strengths": strengths,
            "weaknesses": weaknesses,
        })

    # 保存结果到 tests/ 目录
    output_dir = os.path.join(os.path.dirname(__file__), "..", "tests")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "basic_scored.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  结果已保存: {output_path}")
    print(f"  下一步: cd references && python full-engine.py --input test_data.json --output scored.json --dry-run")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
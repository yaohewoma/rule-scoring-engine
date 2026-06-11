#!/usr/bin/env python3
"""
Rule Scoring Engine — 自动化测试套件

运行: python tests/test_runner.py

测试项目：
  T1 - 模板可导入性（full-engine + classification-rules）
  T2 - 基准评分一致性（新引擎输出 vs 基准 test_scored.json）
  T3 - CSV 导出正确性
  T4 - 批量分类正确性
  T5 - 关键词校验
  T6 - 输入校验（必填字段缺失）
  T7 - 分类器一致性（同输入多次跑结果相同）
  T8 - CLI 各模式可运行性
"""
import sys
import os
import json
import csv
import io
import importlib.util
import subprocess

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(ROOT, "references")
TEST_DIR = os.path.join(ROOT, "tests")

# 颜色输出
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0


def _load_module(name: str, path: str):
    """通过 importlib 加载模块（支持带连字符的文件名）"""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def check(name: str, condition: bool, detail: str = ""):
    """单条测试断言"""
    global passed, failed
    if condition:
        print(f"  {GREEN}✓{RESET} {name}")
        passed += 1
    else:
        print(f"  {RED}✗{RESET} {name} {YELLOW}{detail}{RESET}")
        failed += 1


def test_module_import():
    """T1: 验证模块可正常导入"""
    print(f"\n{BOLD}T1: 模块可导入性{RESET}")
    try:
        fe = _load_module("full_engine", os.path.join(REF_DIR, "full-engine.py"))
        check("full-engine 导入成功", hasattr(fe, "score_project"))
        check("__version__ 存在", hasattr(fe, "__version__"))
        check("validate_keywords 函数存在", hasattr(fe, "validate_keywords"))
        check("export_to_csv 函数存在", hasattr(fe, "export_to_csv"))
    except Exception as e:
        check("full-engine 导入", False, str(e))
        return None

    try:
        cr = _load_module("cls_rules", os.path.join(REF_DIR, "classification-rules.py"))
        check("classification-rules 导入成功", hasattr(cr, "classify_product_type"))
        check("classify_batch 函数存在", hasattr(cr, "classify_batch"))
    except Exception as e:
        check("classification-rules 导入", False, str(e))
        return None

    return fe, cr


def test_scoring_baseline(fe):
    """T2: 基准评分一致性"""
    print(f"\n{BOLD}T2: 基准评分一致性{RESET}")

    with open(os.path.join(TEST_DIR, "test_data.json"), "r", encoding="utf-8") as f:
        projects = json.load(f)

    with open(os.path.join(TEST_DIR, "test_scored.json"), "r", encoding="utf-8") as f:
        expected = json.load(f)

    for i, (project, exp) in enumerate(zip(projects["projects"], expected)):
        scored = fe.score_project(project, fe.KEYWORDS, fe.DEFAULT_CONFIG)
        check(
            f"项目 {i+1} avgScore: {scored['avgScore']} == {exp['avgScore']}",
            scored["avgScore"] == exp["avgScore"],
        )
        grade = fe.assign_grade(scored["avgScore"], fe.DEFAULT_CONFIG)
        check(
            f"项目 {i+1} grade: {grade} == {exp['qualityGrade']}",
            grade == exp["qualityGrade"],
        )


def test_csv_export(fe):
    """T3: CSV 导出正确性"""
    print(f"\n{BOLD}T3: CSV 导出正确性{RESET}")

    with open(os.path.join(TEST_DIR, "test_data.json"), "r", encoding="utf-8") as f:
        projects = json.load(f)["projects"]

    # 评分
    for p in projects:
        scored = fe.score_project(p, fe.KEYWORDS, fe.DEFAULT_CONFIG)
        p["scores"] = scored["scores"]
        p["avgScore"] = scored["avgScore"]
        p["qualityGrade"] = fe.assign_grade(scored["avgScore"], fe.DEFAULT_CONFIG)
        p["stars"] = fe.assign_stars(scored["avgScore"], fe.DEFAULT_CONFIG)
        p["oneLiner"] = fe.identify_one_liner(p, scored["scores"])
        s, w = fe.quick_swot(p, scored["scores"])
        p["strengths"] = s
        p["weaknesses"] = w

    # 导出 CSV
    csv_path = os.path.join(TEST_DIR, "test_auto.csv")
    fe.export_to_csv(projects, csv_path)

    check("CSV 文件已生成", os.path.exists(csv_path))

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        check(f"CSV 行数: {len(reader)} == 2", len(reader) == 2)
        check("CSV 含 avgScore 列", "avgScore" in reader[0])
        check("CSV 含 functionality 列", "functionality" in reader[0])

    os.remove(csv_path)


def test_batch_classification(cr):
    """T4: 批量分类正确性"""
    print(f"\n{BOLD}T4: 批量分类正确性{RESET}")

    texts = [
        "这是一个ai驱动的学习助手，基于大模型技术",
        "一个简单的计算器工具",
        "在线教育平台，支持视频课程",
    ]

    results = cr.classify_batch(texts)
    check(f"分类结果数: {len(results)} == 3", len(results) == 3)
    check("每个结果都是 (str, float) 元组", all(isinstance(r, tuple) and len(r) == 2 for r in results))

    # AI 文本应被分类为 AI工具/科技工具
    ai_result = results[0][0]
    check(
        f"AI 文本分类为 {ai_result}（期望 AI工具 或 科技工具）",
        ai_result in ("AI工具", "AI", "科技工具"),
    )


def test_keyword_validation(fe):
    """T5: 关键词校验"""
    print(f"\n{BOLD}T5: 关键词校验{RESET}")

    # 正常配置应有跨维度警告
    warnings = fe.validate_keywords(fe.KEYWORDS)
    check("内置 KEYWORDS 校验产生警告（预期：跨维度共享提示）", len(warnings) > 0)

    # 空配置
    empty_warnings = fe.validate_keywords({})
    check("空关键词配置校验无警告", len(empty_warnings) == 0)

    # 重复关键词
    dup_kws = {"functionality": {"core": ["api", "api"]}}
    dup_warnings = fe.validate_keywords(dup_kws)
    check("重复关键词被检测", any("重复" in w for w in dup_warnings))


def test_input_validation(fe):
    """T6: 输入校验"""
    print(f"\n{BOLD}T6: 输入校验{RESET}")

    # 缺少必填字段
    bad = [{"title": "no id", "rawText": "test"}]
    ok = fe.validate_input(bad)
    check("缺少 topicId 应不通过", not ok)

    # 正常数据
    good = [{"topicId": "1", "title": "test", "rawText": "test"}]
    ok = fe.validate_input(good)
    check("正常数据应通过", ok)

    # 空列表
    ok = fe.validate_input([])
    check("空列表应通过", ok)


def test_classification_consistency(cr):
    """T7: 分类器一致性"""
    print(f"\n{BOLD}T7: 分类器一致性{RESET}")

    text = "这是一个AI驱动的学习助手，基于大模型技术"
    results = [cr.classify_product_type(text.lower(), "")[0] for _ in range(5)]
    all_same = all(r == results[0] for r in results)
    check(f"5 次分类结果一致: {results[0]}", all_same)


def test_cli_invocation():
    """T8: CLI 各模式可运行"""
    print(f"\n{BOLD}T8: CLI 各模式可运行{RESET}")

    fe_path = os.path.join(REF_DIR, "full-engine.py")
    data_path = os.path.join(TEST_DIR, "test_data.json")
    out_path = os.path.join(TEST_DIR, "test_cli.json")

    modes = [
        (["python", fe_path, "--version"], "version"),
        (["python", fe_path, "--validate", "--quiet"], "validate"),
        (["python", fe_path, "--input", data_path, "--dry-run", "--dry-run-size", "1"], "dry-run"),
        (["python", fe_path, "--input", data_path, "--output", out_path, "--quiet"], "score"),
    ]

    for cmd, label in modes:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # validate 模式可能 exit 1（有警告），其余应 exit 0
            expected_code = 1 if "validate" in label else 0
            passed_local = result.returncode == expected_code or (
                "validate" in label and result.returncode == 0
            )
            check(f"CLI {label} exit={result.returncode}", passed_local,
                  result.stderr[:80] if result.returncode else "")
        except Exception as e:
            check(f"CLI {label}", False, str(e))

    # Cleanup
    if os.path.exists(out_path):
        os.remove(out_path)

    # 测试 CSV 导出
    csv_out = os.path.join(TEST_DIR, "test_cli.csv")
    try:
        result = subprocess.run(
            ["python", fe_path, "--input", data_path, "--output", csv_out,
             "--output-format", "csv", "--quiet"],
            capture_output=True, text=True, timeout=30,
        )
        check("CLI CSV 导出", result.returncode == 0)
        if os.path.exists(csv_out):
            os.remove(csv_out)
    except Exception as e:
        check("CLI CSV 导出", False, str(e))

    # 测试分类器批量模式
    cls_path = os.path.join(REF_DIR, "classification-rules.py")
    cls_out = os.path.join(TEST_DIR, "test_cli_cls.csv")
    try:
        result = subprocess.run(
            ["python", cls_path, "--input", data_path, "--output", cls_out, "--quiet"],
            capture_output=True, text=True, timeout=30,
        )
        check("CLI 批量分类 CSV", result.returncode == 0)
        if os.path.exists(cls_out):
            os.remove(cls_out)
    except Exception as e:
        check("CLI 批量分类 CSV", False, str(e))


def main():
    global passed, failed
    print(f"{BOLD}Rule Scoring Engine — 自动化测试{RESET}")
    print(f"版本: {__import__('full_engine').__version__ if 'full_engine' in sys.modules else 'N/A'}")
    print("=" * 50)

    modules = test_module_import()
    if modules is None:
        print(f"\n{RED}模块导入失败，终止测试{RESET}")
        return 1

    fe, cr = modules
    test_scoring_baseline(fe)
    test_csv_export(fe)
    test_batch_classification(cr)
    test_keyword_validation(fe)
    test_input_validation(fe)
    test_classification_consistency(cr)
    test_cli_invocation()

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    total = passed + failed
    print(f"总计: {total}  通过: {GREEN}{passed}{RESET}  失败: {RED}{failed}{RESET}")
    print(f"通过率: {passed / total * 100:.0f}%")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    # 确保可以导入 full_engine
    sys.path.insert(0, REF_DIR)
    sys.exit(main())
#!/usr/bin/env python3
"""
Automated evaluation runner for Nexus RAG accuracy.
Loads golden_dataset.json, sends queries to the API, and scores results.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, List, Tuple
from datetime import datetime

GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "golden_dataset.json")
API_BASE = os.environ.get("NEXUS_API_URL", "http://localhost:8002")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "evaluations")


def load_golden_dataset(path: str) -> List[Dict]:
    with open(path) as f:
        data = json.load(f)
    return data["test_cases"], data.get("evaluation_params", {})


def query_api(question: str) -> Dict:
    payload = json.dumps({"question": question, "top_k": 5}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/query",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}", "sources": [], "confidence": 0.0}
    except Exception as e:
        return {"error": str(e), "sources": [], "confidence": 0.0}


def check_answer_contains(answer: str, expected_phrases: List[str]) -> Tuple[bool, List[str], List[str]]:
    if not expected_phrases:
        return True, [], []
    found = [p for p in expected_phrases if p.lower() in answer.lower()]
    missing = [p for p in expected_phrases if p.lower() not in answer.lower()]
    return len(missing) == 0, found, missing


def check_sources_count(sources: List, expected: int) -> Tuple[bool, int]:
    actual = len(sources)
    if expected == 0:
        return actual == 0, actual
    return actual >= 1 if expected >= 1 else actual == expected, actual


def check_gate_blocked(result: Dict, expected_blocked: bool) -> Tuple[bool, bool]:
    is_blocked = result.get("confidence", 0) == 0.0 and len(result.get("sources", [])) == 0
    if "error" in result:
        is_blocked = True
    passed = is_blocked == expected_blocked
    return passed, is_blocked


def check_confidence(confidence: float, min_confidence: float) -> Tuple[bool, float]:
    if min_confidence == 0.0:
        return True, confidence
    return confidence >= min_confidence, confidence


def evaluate_test_case(tc: Dict) -> Dict:
    question = tc["question"]
    start = time.time()
    result = query_api(question)
    elapsed = time.time() - start

    checks = {}

    # Answer content check
    ans_ok, ans_found, ans_missing = check_answer_contains(
        result.get("answer", ""), tc.get("expected_answer_contains", [])
    )
    checks["answer_contains"] = {"passed": ans_ok, "found": ans_found, "missing": ans_missing}

    # Sources count check
    src_ok, src_actual = check_sources_count(result.get("sources", []), tc.get("expected_sources", 0))
    checks["sources_count"] = {"passed": src_ok, "expected": tc.get("expected_sources", 0), "actual": src_actual}

    # Gate block check
    gate_ok, gate_actual = check_gate_blocked(result, tc.get("expected_gate_blocked", False))
    checks["gate_blocked"] = {"passed": gate_ok, "expected": tc["expected_gate_blocked"], "actual": gate_actual}

    # Confidence check
    conf_ok, conf_actual = check_confidence(result.get("confidence", 0), tc.get("min_confidence", 0))
    checks["confidence"] = {"passed": conf_ok, "min_expected": tc.get("min_confidence", 0), "actual": conf_actual}

    # Response time check
    checks["response_time_ms"] = {"actual": round(elapsed * 1000, 2)}

    all_passed = all(c["passed"] for c in checks.values() if "passed" in c)

    return {
        "id": tc["id"],
        "category": tc.get("category", "unknown"),
        "question": question,
        "passed": all_passed,
        "checks": checks,
        "response": result,
        "tags": tc.get("tags", []),
    }


def print_report(results: List[Dict], params: Dict) -> None:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    print(f"\n{'='*60}")
    print("  NEXUS RAG EVALUATION REPORT")
    print(f"  {datetime.now().isoformat()}")
    print(f"  API: {API_BASE}")
    print(f"{'='*60}")
    print(f"  Total test cases : {total}")
    print(f"  Passed           : {passed}")
    print(f"  Failed           : {failed}")
    if total > 0:
        print(f"  Pass rate        : {passed/total*100:.1f}%")
    print(f"{'='*60}\n")

    # Summary by category
    categories = {}
    for r in results:
        cat = r.get("category", "unknown")
        categories.setdefault(cat, {"total": 0, "passed": 0})
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1

    print("  Results by category:")
    for cat, stats in sorted(categories.items()):
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] else 0
        print(f"    {cat:20s}  {stats['passed']}/{stats['total']} ({rate:.0f}%)")
    print()

    # Failed cases detail
    failed_cases = [r for r in results if not r["passed"]]
    if failed_cases:
        print("  FAILED CASES:")
        for r in failed_cases:
            print(f"    [{r['id']}] ({r['category']}) {r['question'][:60]}")
            for check_name, check_result in r["checks"].items():
                if "passed" in check_result and not check_result["passed"]:
                    print(f"      - {check_name}: expected={check_result.get('expected')}, "
                          f"actual={check_result.get('actual')}")
            print()
    else:
        print("  All test cases passed! \n")


def save_report(results: List[Dict], params: Dict) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORT_DIR, f"eval_report_{timestamp}.json")
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_base": API_BASE,
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1) if total else 0,
        "results": results,
        "params": params,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Report saved to: {report_path}")
    return report_path


def main():
    if not os.path.exists(GOLDEN_DATASET_PATH):
        print(f"ERROR: Golden dataset not found at {GOLDEN_DATASET_PATH}")
        sys.exit(1)

    test_cases, params = load_golden_dataset(GOLDEN_DATASET_PATH)
    print(f"Loaded {len(test_cases)} test cases from golden dataset\n")

    results = []
    for i, tc in enumerate(test_cases):
        label = f"[{i+1}/{len(test_cases)}]"
        print(f"  {label} {tc['category']:15s} {tc['question'][:50]}", end="")
        result = evaluate_test_case(tc)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status}")
        results.append(result)

    print_report(results, params)
    save_report(results, params)
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

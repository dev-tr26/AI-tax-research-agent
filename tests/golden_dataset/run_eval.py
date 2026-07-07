"""
Golden dataset evaluation — runs all 10 queries, measures latency, reports results.
Usage: python -m tests.golden_dataset.run_eval
"""
import asyncio
import json
import time
import statistics
from typing import Dict
import httpx

API_BASE = "http://localhost:8000"

GOLDEN_QUERIES = [
    {
        "id": "DT-01",
        "complexity": "Foundational",
        "query": (
            "Is exemption under Section 54 available if the new residential property "
            "is purchased before the date of sale of the original property? "
            "Cite the relevant proviso and any CBDT clarification."
        ),
    },
    {
        "id": "DT-02",
        "complexity": "Foundational",
        "query": (
            "What are the conditions for claiming deduction under Section 80C? "
            "List qualifying instruments and the investment ceiling. "
            "Has the ceiling changed across Finance Acts?"
        ),
    },
    {
        "id": "DT-03",
        "complexity": "Intermediate",
        "query": (
            "Explain the set-off and carry-forward rules for capital losses. "
            "Can a long-term capital loss be set off against short-term capital gains? "
            "What is the carry-forward period?"
        ),
    },
    {
        "id": "DT-04",
        "complexity": "Intermediate",
        "query": (
            "What is the difference between Section 54 and Section 54F? "
            "A taxpayer sells a plot of land (not a residential house) and wants to claim "
            "exemption on purchase of a new residential house. Which section applies and "
            "what are the additional conditions?"
        ),
    },
    {
        "id": "DT-05",
        "complexity": "Advanced",
        "query": (
            "LCo. gave a loan to BCo. on 2 April 2023 and the same was repaid on 6 June 2023. "
            "BCo. is a shareholder of LCo. and LCo. has sufficient accumulated reserves. "
            "As on 31 March 2024, no loan is outstanding. Whether deemed dividend provisions "
            "under Section 2(22)(e) will apply? Explain with the help of relevant case laws."
        ),
    },
    {
        "id": "DT-06",
        "complexity": "Advanced",
        "query": (
            "A company pays management fees to its foreign parent at 15% of revenue. "
            "The Assessing Officer invokes Section 40A(2)(b) to disallow the excess. "
            "What is the standard for determining 'fair market value' of such services under "
            "Section 40A(2)? How does this interact with Transfer Pricing provisions under Chapter X?"
        ),
    },
    {
        "id": "DT-07",
        "complexity": "Advanced",
        "query": (
            "An individual receives a cash gift of Rs. 8 lakhs from a non-relative friend. "
            "He also receives a plot of land (stamp duty value Rs. 12 lakhs, consideration paid "
            "Rs. 5 lakhs) from another friend. Compute the total income taxable under "
            "Section 56(2)(x) and explain each applicable clause."
        ),
    },
    {
        "id": "DT-08",
        "complexity": "Advanced",
        "query": (
            "Explain the concept of 'substantial question of law' under Section 260A. "
            "Can an appeal lie to the High Court on a question of fact? What is the difference "
            "between an appeal under Section 260A and a writ under Article 226 of the Constitution "
            "in the context of income tax disputes?"
        ),
    },
    {
        "id": "DT-09",
        "complexity": "Advanced",
        "query": (
            "A private limited company has been making losses for 5 consecutive years. "
            "The Assessing Officer proposes to invoke Section 68 to treat unexplained cash credits "
            "in the books as income. The company argues it has maintained books of account and the "
            "source is known. What is the burden of proof under Section 68 and what must the "
            "assessee demonstrate? Cite relevant Supreme Court and High Court precedents."
        ),
    },
    {
        "id": "DT-10-T1",
        "complexity": "Multi-Turn T1",
        "query": "Explain the reassessment framework under Section 147.",
        "session_key": "DT-10",
    },
    {
        "id": "DT-10-T2",
        "complexity": "Multi-Turn T2",
        "query": (
            "What is the time limit for issuing notice under Section 148 after the "
            "Finance Act 2021 amendments? Is there a distinction between escaped income "
            "above and below Rs. 50 lakhs?"
        ),
        "session_key": "DT-10",
    },
    {
        "id": "DT-10-T3",
        "complexity": "Multi-Turn T3",
        "query": (
            "Can the assessee challenge the validity of the reassessment notice at the "
            "threshold without waiting for the assessment to be completed? "
            "Cite the Supreme Court ruling in this regard."
        ),
        "session_key": "DT-10",
    },
]


async def run_query(client: httpx.AsyncClient, query_info: Dict, session_id: str = None) -> Dict:
    """Run a single query and return results with latency."""
    t0 = time.monotonic()
    resp = await client.post(
        f"{API_BASE}/query",
        json={"query": query_info["query"], "session_id": session_id},
        timeout=30.0,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    resp.raise_for_status()
    data = resp.json()

    response_obj = data.get("response", {})
    citations = response_obj.get("citations", [])
    verified = sum(1 for c in citations if c.get("verified"))
    unverified = response_obj.get("unverified_count", 0)

    return {
        "id": query_info["id"],
        "complexity": query_info["complexity"],
        "query_preview": query_info["query"][:80],
        "latency_ms": latency_ms,
        "server_latency_ms": response_obj.get("latency_ms", 0),
        "confidence": response_obj.get("confidence", "UNKNOWN"),
        "citations_total": len(citations),
        "citations_verified": verified,
        "unverified_count": unverified,
        "vector_retrieval_ms": data.get("timings", {}).get("vector_retrieval_ms", 0),
        "citation_validation_ms": data.get("timings", {}).get("citation_validation_ms", 0),
        "answer_preview": response_obj.get("final_answer", "")[:200],
        "session_id": data.get("session_id"),
    }


async def run_evaluation():
    print("=" * 70)
    print("TaxAI Golden Dataset Evaluation")
    print("=" * 70)

    results = []
    sessions = {}  # session_key → session_id

    async with httpx.AsyncClient() as client:
        for q in GOLDEN_QUERIES:
            session_key = q.get("session_key")
            session_id = sessions.get(session_key) if session_key else None

            print(f"\n[{q['id']}] {q['complexity']}")
            print(f"  Query: {q['query'][:70]}...")

            try:
                result = await run_query(client, q, session_id)

                # Track session for multi-turn
                if session_key and result.get("session_id"):
                    sessions[session_key] = result["session_id"]

                results.append(result)
                print(f"  ✓ Latency: {result['latency_ms']}ms | "
                      f"Confidence: {result['confidence']} | "
                      f"Citations: {result['citations_verified']}/{result['citations_total']} verified")
                print(f"  Answer: {result['answer_preview'][:100]}...")

            except Exception as e:
                print(f"  ✗ FAILED: {e}")
                results.append({
                    "id": q["id"], "complexity": q["complexity"],
                    "latency_ms": 0, "error": str(e)
                })

    # ── Latency Statistics ──────────────────────────────────────────────────
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms", 0) > 0]
    vec_latencies = [r.get("vector_retrieval_ms", 0) for r in results if r.get("vector_retrieval_ms", 0) > 0]
    citation_latencies = [r.get("citation_validation_ms", 0) for r in results if r.get("citation_validation_ms", 0) > 0]

    print("\n" + "=" * 70)
    print("LATENCY REPORT")
    print("=" * 70)
    print(f"{'Query ID':<15} {'Latency (ms)':<15} {'Vec (ms)':<12} {'Cite (ms)':<12} {'Confidence':<12} {'Verified'}")
    print("-" * 70)
    for r in results:
        print(
            f"{r['id']:<15} "
            f"{r.get('latency_ms', 'ERR'):<15} "
            f"{r.get('vector_retrieval_ms', '-'):<12} "
            f"{r.get('citation_validation_ms', '-'):<12} "
            f"{r.get('confidence', '-'):<12} "
            f"{r.get('citations_verified', '-')}/{r.get('citations_total', '-')}"
        )

    if latencies:
        latencies_sorted = sorted(latencies)
        p50 = latencies_sorted[len(latencies_sorted) // 2]
        p95_idx = int(len(latencies_sorted) * 0.95)
        p95 = latencies_sorted[min(p95_idx, len(latencies_sorted) - 1)]
        avg_vec = statistics.mean(vec_latencies) if vec_latencies else 0
        avg_cite = statistics.mean(citation_latencies) if citation_latencies else 0

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"P50 end-to-end latency:       {p50} ms (target: <5000ms)")
        print(f"P95 end-to-end latency:       {p95} ms (target: <10000ms)")
        print(f"Avg vector retrieval:          {avg_vec:.0f} ms (target: <800ms)")
        print(f"Avg citation validation:       {avg_cite:.0f} ms (target: <1000ms)")
        print(f"P50 {'✅ PASS' if p50 < 5000 else '❌ FAIL'} | "
              f"P95 {'✅ PASS' if p95 < 10000 else '❌ FAIL'} | "
              f"Vec {'✅ PASS' if avg_vec < 800 else '❌ FAIL'} | "
              f"Cite {'✅ PASS' if avg_cite < 1000 else '❌ FAIL'}")

    # Save results
    with open("golden_dataset_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to: golden_dataset_results.json")


if __name__ == "__main__":
    asyncio.run(run_evaluation())

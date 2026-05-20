import json

d = json.load(
    open("nmaiex_tuning/output/ground_truth_matrix.json", "r", encoding="utf-8")
)
jobs = set(k.split("_")[0] for k in d.keys())
print(f"Unique jobs: {len(jobs)}")

for j in sorted(jobs, key=lambda x: int(x[1:])):
    pairs = {k: v for k, v in d.items() if k.startswith(j + "_")}
    count = len(pairs)
    scores = [v["score"] for v in pairs.values()]
    avg = sum(scores) / count if count else 0
    ge3 = sum(1 for s in scores if s >= 3)
    print(f"  {j}: count={count}, avg={avg:.2f}, ge3={ge3}")

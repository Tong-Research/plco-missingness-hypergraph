"""Score the steering probes (prereg/STEER.md) from results/steer/*.csv; one summary per probe, verdict against the declared line."""
import csv, glob, collections, pathlib, sys, numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[1]; R = ROOT / "results/steer"
def rows(probe): 
    out = []
    for f in sorted(glob.glob(str(R / f"{probe}_*.csv"))):
        if ".v1." in f: continue   # superseded first-version outputs
        out += list(csv.DictReader(open(f)))
    return out
def abstain():
    rs = rows("abstain"); by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rs: by[r["dataset"]][(r["coverage"], r["rule"])].append(float(r.get("auroc", "nan")))
    conf_wins = 0; print("abstain: mean AUROC of retained set, tree predictions; rule = ranking score")
    for ds, d in by.items():
        line = []; allcov = True
        for cov in ["0.5", "0.7", "0.9"]:
            c, s, dp, rnd = (np.mean(d[(cov, k)]) for k in ["tree_confidence", "lattice_support", "pattern_depth", "random"]); line.append(f"@{cov}: conf {c:.3f} support {s:.3f} depth {dp:.3f} random {rnd:.3f}"); allcov &= c > s   # AUROC of the retained set (v2); AUPRC was prevalence-confounded
        conf_wins += allcov; print(f"  {ds:20s} " + " | ".join(line) + ("  [confidence > support at every coverage]" if allcov else ""))
    print(f"  verdict: confidence beats support at every coverage on {conf_wins}/{len(by)}; declared expectation NEGATIVE needs >= 6 -> {'as expected: NEGATIVE' if conf_wins >= 6 else 'unexpected; look'}")
def smalln():
    rs = rows("smalln"); by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rs: by[r["dataset"]][(int(r["n"]), r["arm"])].append(float(r["auprc"]))
    win = 0; tree_all = 0; print("smalln: mean AUPRC over 3 reps")
    for ds, d in by.items():
        ns = sorted({n for n, _ in d}); line = []; small_win = False; tree_every = True
        for n in ns:
            f, t, i = (np.mean(d[(n, a)]) if (n, a) in d else np.nan for a in ["family_cv", "histgb_native", "mean_indicator"]); line.append(f"n={n}: hier {f:.3f} tree {t:.3f} ind {i:.3f}")
            if n <= 1000 and f >= t + 0.01: small_win = True
            if not (t > f): tree_every = False
        win += small_win; tree_all += tree_every; print(f"  {ds:20s} " + " | ".join(line))
    print(f"  verdict: hierarchy >= tree + 0.01 at n <= 1000 on {win}/{len(by)} (needs >= 4); tree ahead at every n on {tree_all}/{len(by)} (kill >= 6)")
def worstpat():
    rs = rows("worstpat"); by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rs:
        for m in ["worst_logloss", "median_logloss", "worst_auprc", "small_mean_logloss", "small_mean_auprc", "pooled_auprc"]: by[r["dataset"]][(r["arm"], m)].append(float(r[m]) if r[m] not in ("", "nan") else np.nan)
    best_worst = 0; small_better = 0; tree_best = 0; print("worstpat: mean over 3 folds")
    for ds, d in by.items():
        g = lambda a, m: np.nanmean(d[(a, m)]); line = " | ".join(f"{a}: worst ll {g(a,'worst_logloss'):.3f} small ll {g(a,'small_mean_logloss'):.3f} worst au {g(a,'worst_auprc'):.3f} pooled {g(a,'pooled_auprc'):.3f}" for a in ["family_cv", "histgb_native", "mean_indicator"])
        wl = {a: g(a, "worst_logloss") for a in ["family_cv", "histgb_native", "mean_indicator"]}; b = min(wl, key=wl.get); best_worst += b == "family_cv"; tree_best += b == "histgb_native"
        small_better += g("family_cv", "small_mean_logloss") < g("histgb_native", "small_mean_logloss"); print(f"  {ds:20s} {line}  [best worst-ll: {b}]")
    print(f"  verdict: hierarchy best worst-pattern log-loss on {best_worst}/{len(by)} (needs >= 4); better small-pattern log-loss than tree on {small_better}/{len(by)} (needs >= 5); tree best on {tree_best} (kill >= 5)")
def drift():
    rs = rows("drift"); by = collections.defaultdict(list)
    for r in rs: by[(r["dataset"], r["stat"])].append(int(r["delay_windows"]))
    print("drift: detection delay in windows (-1 = never) per dropped variable")
    for k, v in sorted(by.items()): print(f"  {k[0]:20s} {k[1]:17s} delays {v}")
    lat = [d for (ds, s), v in by.items() if s == "lattice_unfitted" for d in v]; ps = [d for (ds, s), v in by.items() if s != "lattice_unfitted" for d in v]
    print(f"  verdict: lattice delay 0 on {sum(d == 0 for d in lat)}/{len(lat)} variables; prediction-shift delay >= 2 or never on {sum(d >= 2 or d < 0 for d in ps)}/{len(ps)} (needs >= half)")
def blend():
    rs = rows("blend"); by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rs: by[r["dataset"]][r["arm"]].append(float(r["auprc"]))
    clear = collections.Counter(); worse = collections.Counter(); print("blend: mean AUPRC over 3 folds, delta vs tree")
    for ds, d in by.items():
        t = np.mean(d["histgb_native"]); line = " ".join(f"{a} {np.mean(v) - t:+.4f}" for a, v in d.items() if a != "histgb_native"); print(f"  {ds:20s} tree {t:.4f} | {line}")
        for a in ["blend50", "blend_cv", "stack_tree_on_hier", "hier_on_tree_logit"]:
            if a in d: clear[a] += np.mean(d[a]) - t >= 0.003; worse[a] += np.mean(d[a]) - t < -0.003
    print(f"  verdict: clears +0.003 -> {dict(clear)}; below -0.003 -> {dict(worse)}; needs blend_cv or hier_on_tree_logit on >= 4 and never worse")
def robust():
    rs = rows("robust"); by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rs: by[r["dataset"]][(float(r["extra_missing"]), r["arm"])].append(float(r["auprc"]))
    hier_less = 0; tree_less = 0; print("robust: AUPRC at 0 / 0.1 / 0.3 extra missingness, and loss at 0.3")
    for ds, d in by.items():
        line = []; loss = {}
        for a in ["family_cv", "histgb_native", "mean_indicator"]:
            v = [np.mean(d[(f, a)]) for f in [0.0, 0.1, 0.3]]; loss[a] = v[0] - v[2]; line.append(f"{a}: {v[0]:.3f}/{v[1]:.3f}/{v[2]:.3f} (loss {loss[a]:+.3f})")
        hier_less += loss["family_cv"] < loss["histgb_native"]; tree_less += loss["histgb_native"] < loss["family_cv"]; print(f"  {ds:20s} " + " | ".join(line))
    print(f"  verdict: hierarchy loses less than tree on {hier_less}/{len(by)} (needs >= 5); tree loses less on {tree_less} (kill >= 5)")
def transfer():
    rs = rows("transfer"); by = collections.defaultdict(dict)
    for r in rs: by[r["site"]][r["arm"]] = (float(r["auprc_transfer"]), float(r["auprc_insite_cv"]))
    hs = 0; ts = 0; print("transfer (mimic4 sites): transfer AUPRC / in-site CV AUPRC, gap = in-site - transfer")
    for s, d in by.items():
        gaps = {a: v[1] - v[0] for a, v in d.items()}; hs += gaps["family_cv"] < gaps["histgb_native"]; ts += gaps["histgb_native"] < gaps["family_cv"]
        print(f"  site {s:4s} " + " | ".join(f"{a}: {v[0]:.3f}/{v[1]:.3f} gap {v[1]-v[0]:+.3f}" for a, v in d.items()))
    print(f"  verdict: hierarchy's gap smaller on {hs}/{len(by)} sites (needs >= 6); tree's smaller on {ts} (kill >= 6)")
if __name__ == "__main__":
    for p in (sys.argv[1:] or ["abstain", "smalln", "worstpat", "drift", "blend", "robust", "transfer"]):
        if glob.glob(str(R / f"{p}_*.csv")): globals()[p](); print()

"""Figure: what H_exc summarises, pattern by pattern, on the four PLCO cohorts.

For each cohort (baseline feature set, the main table's 40,000-record subsample, seed 0) and each
of the forty largest patterns with support >= MIN_SUPPORT, the divergence of the pattern's local
coefficients from the pooled coefficients (Eq. het) is computed on the real mask and on the
row-permuted mask (the null of Eq. hetexc). The per-pattern loop is a copy of
run_real_suite._het_statistic that returns the parts; its support-weighted mean is ASSERTED equal
to the frozen function to 1e-12 before anything is written, so the figure cannot drift from the
number in the table.

Writes figures/hexc_lens_summary.csv (H, H_null mean/sd over 5 permutation seeds, H_exc mean/sd)
and figures/hexc_lens.csv (per-pattern aggregates only: support, divergence real, divergence
null -- no record-level data) and figures/hexc_lens.pdf.
"""
from __future__ import annotations
import os, pathlib, sys, time
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "experiments")); sys.path.insert(0, str(HERE.parent / "src"))
from run_real_suite import _het_statistic, _pattern_rows, MIN_SUPPORT   # noqa: E402
from run_h1_h4 import _subsample, FULL_MAX_N                            # noqa: E402
from hgmiss.data.plco import load_cohort                                 # noqa: E402
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

_REPO = HERE.parents[2]
ROOT = pathlib.Path(os.environ.get("PLCO_ROOT", _REPO / "datasets" / "plco"))
COHORTS = ["colorectal", "lung", "ovarian", "prostate"]
# MIMIC-IV panel: added only after prereg/MIMIC.md is scored (pass --mimic); the ICU matrix, full n as in M1
MIMIC_NPZ = pathlib.Path(os.environ.get("MIMIC_NPZ", pathlib.Path.home() / ".cache" / "phd-matrices" / "mimic4_sites.npz"))


def per_pattern(X, y, max_patterns=40):
    """Same arithmetic as _het_statistic, returning (support, divergence) per pattern."""
    Xi = SimpleImputer(strategy="mean", keep_empty_features=True).fit_transform(X)
    Z = StandardScaler().fit_transform(Xi)
    pooled = LogisticRegression(max_iter=2000).fit(Z, y).coef_.ravel()
    items = sorted(_pattern_rows(X, MIN_SUPPORT).items(), key=lambda kv: -len(kv[1]))[:max_patterns]
    out = []
    for cols, rows in items:
        yy = y[rows]
        if len(np.unique(yy)) < 2:
            continue
        cols = list(cols)
        local = LogisticRegression(max_iter=2000).fit(Z[np.ix_(rows, cols)], yy).coef_.ravel()
        ref = pooled[cols]
        out.append((len(rows), float(np.linalg.norm(local - ref) / (np.linalg.norm(ref) + 1e-9)), len(cols)))
    return out


def permuted(X, seed=0):
    """The null of diagnostics(): mean-fill, then move each row's mask to another row."""
    rng = np.random.default_rng(seed)
    Xh = X.copy(); cm = np.nanmean(X, axis=0); cm = np.where(np.isfinite(cm), cm, 0.0)
    idx = np.where(np.isnan(Xh)); Xh[idx] = np.take(cm, idx[1])
    perm = rng.permutation(len(X)); Xp = Xh.copy(); Xp[~(~np.isnan(X))[perm]] = np.nan
    return Xp


def main():
    rows, summary = [], []
    cohorts = COHORTS + (["mimic4"] if "--mimic" in sys.argv else [])
    for c in cohorts:
        t0 = time.time()
        if c == "mimic4":
            z = np.load(MIMIC_NPZ, allow_pickle=True); X, y = np.asarray(z["X"], float), np.asarray(z["y"]).ravel().astype(int)
        else:
            co = load_cohort(c, ROOT, feature_set="baseline")
            X, y = _subsample(co, seed=0, max_n=FULL_MAX_N)
            X, y = np.asarray(X, float), np.asarray(y).ravel().astype(int)
        H = {}
        # seed-0 real and null feed the figure; null seeds 1-4 give the +/- for the summary table
        for kind, XX, seed in [("real", X, 0)] + [("null", permuted(X, s), s) for s in range(5)]:
            parts = per_pattern(XX, y)
            w = np.array([p[0] for p in parts], float); d = np.array([p[1] for p in parts])
            mine = float((w * d).sum() / w.sum())
            ref = _het_statistic(XX, y)
            assert abs(mine - ref) < 1e-12, f"{c}/{kind}/{seed}: per-pattern mean {mine} != frozen {ref}"
            H.setdefault(kind, []).append(mine)
            if seed == 0:
                for s_, dv, k in parts:
                    rows.append((c, kind, s_, k, dv))
        hn = np.array(H["null"]); hexc = H["real"][0] - hn
        summary.append((c, len(parts), H["real"][0], hn.mean(), hn.std(), hexc.mean(), hexc.std()))
        print(f"  {c}: {len(parts)} patterns, H real {H['real'][0]:.3f} null {hn.mean():.3f}+/-{hn.std():.3f} "
              f"H_exc {hexc.mean():+.3f}+/-{hexc.std():.3f} ({time.time()-t0:.0f}s)", flush=True)
    import csv
    with open(HERE / "hexc_lens.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["cohort", "kind", "support", "n_cols", "divergence"]); w.writerows(rows)
    with open(HERE / "hexc_lens_summary.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["cohort", "n_patterns", "H_real", "H_null_mean", "H_null_sd", "H_exc_mean", "H_exc_sd"])
        w.writerows([(c, k, f"{a:.4f}", f"{b:.4f}", f"{s:.4f}", f"{e:.4f}", f"{es:.4f}") for c, k, a, b, s, e, es in summary])
    plot(rows)


def plot(rows):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter, LogLocator
    cohorts = [c for c in dict.fromkeys(r[0] for r in rows)]
    fig, axes = plt.subplots(1, len(cohorts), figsize=(2.75 * len(cohorts), 2.9), sharey=True)
    for ax, c in zip(axes, cohorts):
        R = [(s, d) for (cc, k, s, _, d) in rows if cc == c and k == "real"]
        N = [(s, d) for (cc, k, s, _, d) in rows if cc == c and k == "null"]
        for data, col, lab, mk in ((N, "0.6", "permuted mask", "o"), (R, "C3", "real mask", "o")):
            s = np.array([p[0] for p in data]); d = np.array([p[1] for p in data])
            ax.scatter(s, d, s=14, c=col, marker=mk, label=lab, alpha=0.85, linewidths=0)
        wr = np.array([p[0] for p in R]); dr = np.array([p[1] for p in R]); wn = np.array([p[0] for p in N]); dn = np.array([p[1] for p in N])
        Hr = (wr*dr).sum()/wr.sum(); Hn = (wn*dn).sum()/wn.sum()
        ax.axhline(Hr, color="C3", lw=0.8); ax.axhline(Hn, color="0.5", lw=0.8, ls="--")
        ax.set_xscale("log"); ax.xaxis.set_minor_formatter(NullFormatter()); ax.xaxis.set_major_locator(LogLocator(base=10, numticks=4)); ax.set_title(f"{('MIMIC-IV' if c == 'mimic4' else c.capitalize())}   $H_{{\\mathrm{{exc}}}}={Hr-Hn:+.3f}$", fontsize=9)
        ax.set_xlabel("pattern support $|S(e)|$", fontsize=8); ax.tick_params(labelsize=7)
    axes[0].set_ylabel("divergence from pooled\ncoefficients (Eq. het)", fontsize=8)
    axes[0].legend(fontsize=7, frameon=False, loc="upper right")
    fig.tight_layout(); fig.savefig(HERE / "hexc_lens.pdf"); print("  wrote figures/hexc_lens.pdf")


if __name__ == "__main__":
    if "--plot-only" in sys.argv:
        import csv as _csv
        with open(HERE / "hexc_lens.csv") as fh:
            rows = [(r["cohort"], r["kind"], int(r["support"]), int(r["n_cols"]), float(r["divergence"]))
                    for r in _csv.DictReader(fh)]
        plot(rows); print("  replotted from csv")
    else:
        main()

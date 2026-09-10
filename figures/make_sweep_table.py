"""tables/sweep.tex and tables/sweep_counts.tex: the rule-based sweep (prereg/SWEEP.md) plus the three mechanism-chosen
candidates, one row per dataset with a complete comparison file in results/cand/.

Two WIN criteria are reported, because the second was adopted after the SWEEP file was written (amendment of
2026-09-04 05:30 records the timeline):
  registered  the estimator AS PUBLISHED beats tuned imputation by >= 0.002 (paired median, Wilcoxon p < 0.05) and its
              real - permuted-mask null excess is >= 0.002;
  widened     the same for the cross-validated hierarchy (family_cv; exact_cv on the Higgs amendment slice). The CV
              hierarchy had no permuted-mask run of its own when this was written, so its control is the LARGER of the two fitting rules' null
              gains (on a permuted mask the inner CV would take whichever rule looks better), which is the conservative
              choice and is stated in the caption.
LOSS: the CV hierarchy is below imputation by >= 0.002 with p < 0.05.
Higgs: the holdout run (prereg/HIGGS.md) predates the CV arm; the pre-registered amendment ran every arm on an untouched
development slice (Result 175). The Higgs row is taken ENTIRELY from that slice and marked; its win is counted
separately in the macros (\SweepHiggsSlice).
"""
import json, re, pathlib
import numpy as np, pandas as pd
from scipy import stats
ROOT = pathlib.Path(__file__).resolve().parent.parent; FLOOR = 0.002
names = {f"sweep_{x['did']}": x["name"] for x in json.load(open(ROOT / "results/sweep_list.json"))}
names.update({"cand_higgs": "ATLAS Higgs", "cand_porto": "Porto Seguro", "cand_acs_income": "ACS income", "cand_airbnb": "Airbnb listings", "cand_nhanes": "NHANES mortality", "cand_mimic4_regime": "MIMIC-IV regimes", "cand_eicu_regime": "eICU regimes"})
scr = pd.read_csv(ROOT / "results/screen_candidates.csv").drop_duplicates("dataset", keep="last").set_index("dataset")

def outcome(f, need, cv_arm="family_cv"):
    d = pd.read_csv(f); real = d[d.permuted == 0].pivot_table(index=["seed", "fold"], columns="arm", values="auprc"); null = d[d.permuted == 1].pivot_table(index=["seed", "fold"], columns="arm", values="auprc")
    if len(real) < need or cv_arm not in real.columns: return None
    def pm(a, b): x = (real[a] - real[b]).dropna(); return float(x.median()), (float(stats.wilcoxon(x).pvalue) if x.abs().sum() > 0 else 1.0)
    def null_gain(arm): return (null[arm] - null["mean_impute"]) if arm in null.columns else None
    def excess(arm, ng): return float(((real[arm] - real["mean_impute"]) - ng).dropna().median()) if ng is not None else float("nan")
    m_pub, p_pub = pm("ours", "mean_impute"); ex_pub = excess("ours", null_gain("ours"))
    gains = [x for x in [null_gain("ours"), null_gain("exact_submodels")] if x is not None]; ng_cv = pd.concat(gains, axis=1).max(axis=1) if gains else None
    m_cv, p_cv = pm(cv_arm, "mean_impute"); ex_cv = excess(cv_arm, ng_cv)
    return dict(n=len(real), imp=real["mean_impute"].mean(), ind=real["mean_indicator"].mean(), inter=real["mask_interaction"].mean(), ours=real["ours"].mean(), fam=real[cv_arm].mean(), tree=real["histgb_native"].mean(),
                m_pub=m_pub, win_pub=bool(m_pub >= FLOOR and p_pub < .05 and ex_pub >= FLOOR), m_cv=m_cv, ex_cv=ex_cv, win_cv=bool(m_cv >= FLOOR and p_cv < .05 and ex_cv >= FLOOR),
                loss_cv=bool(m_cv <= -FLOOR and p_cv < .05), cv_ind=pm(cv_arm, "mean_indicator")[0], cv_inter=pm(cv_arm, "mask_interaction")[0], tree_cv=pm("histgb_native", cv_arm)[0])

rows = []
for f in sorted((ROOT / "results/cand").glob("*.csv")):
    # A dataset key is cand_<name> or sweep_<did> and never contains a dot, so any
    # dotted stem is an artefact: a per-seed partial (.s<k>, merged by
    # merge_seed_files.py), a development slice (.devrem), a superseded 10-cell
    # file, or a machine-suffixed copy the collector renamed to avoid a clash.
    # The old rule named the first three, so sweep_42093.trevally.csv became an
    # eighteenth "dataset" with n_pat -1 and H_exc NaN.
    if "." in f.stem: continue
    key = f.stem; s = scr.loc[key] if key in scr.index else None
    o = outcome(f, 15 if key.startswith("cand_") else 10); note = ""
    if o is None and key == "cand_higgs":   # before the 14:50 amendment the holdout file had no CV arm; fall back to the slice, marked
        o = outcome(ROOT / "results/cand/cand_higgs.devrem.csv", 15, cv_arm="exact_cv"); note = "slice"
    flag = bool(s is not None and s.het_excess >= 0.15 and s.cov30 >= 0.9 and s.iota >= 0.05)
    rows.append(dict(key=key, name=names.get(key, key), flag=flag, n_pat=int(s.n_pat) if s is not None else -1, hexc=float(s.het_excess) if s is not None else np.nan, iota=float(s.iota) if s is not None else np.nan,
                     src="mechanism" if key.startswith("cand_") else "rule", note=note, **(o or {})))
df = pd.DataFrame(rows); done = df[df["n"].notna()] if "n" in df.columns else df.iloc[0:0]
def counts(sub, col):
    return int((sub.flag & sub[col]).sum()), int((sub.flag & ~sub[col].astype(bool)).sum()), int((~sub.flag & sub[col]).sum()), int((~sub.flag & ~sub[col].astype(bool)).sum())
fw, fn, uw, un = counts(done, "win_cv"); pfw, pfn, puw, pun = counts(done, "win_pub"); rule = done[done.src == "rule"]; rfw, rfn, ruw, run = counts(rule, "win_cv")
higgs_win = int(done[(done.key == "cand_higgs")]["win_cv"].sum()) if "win_cv" in done.columns else 0
print(f"  widened (CV hierarchy): flagged {fw}/{fw+fn}, unflagged {uw}/{uw+un}; registered (published arm): flagged {pfw}/{pfw+pfn}, unflagged {puw}/{puw+pun}; rule-only widened: flagged {rfw}/{rfw+rfn}, unflagged {ruw}/{ruw+run}; Higgs slice win {higgs_win}")
beat_both = done[(done.win_cv) & (done.cv_ind >= 0.005) & (done.cv_inter >= 0.005)]; print("  CV wins that also beat indicator and interaction by >= 0.005:", list(beat_both.name), "; tree ahead of CV on all:", bool((done.tree_cv > 0).all()))
lines = ["% GENERATED by figures/make_sweep_table.py --- do not edit by hand.", r"\begin{table}[t]", r"\centering", r"\scriptsize",
         r"\caption{Diagnostic flag on the development half against outcome, for the rule-based sweep (\texttt{prereg/SWEEP.md}; holdout half, "
         r"$100{,}000$-record subsample, 2 seeds $\times$ 5 folds) and the three mechanism-chosen candidates ($\dagger$; holdout half, 3 $\times$ 5; "
         r"ACS on a $200{,}000$ subsample). $\ddagger$: the Higgs row is taken entirely from the pre-registered amendment on an untouched "
         r"development slice (Result 175), because its holdout run predates the cross-validated arm. Imput.\ tuned mean imputation, Indic.\ tuned "
         r"indicator, Inter.\ mask-interaction expansion, Publ.\ the estimator as published, CV the cross-validated hierarchy (AUPRC means); "
         r"$\Delta$ the CV hierarchy's paired median over imputation. Win requires a gain of at least $0.002$ over imputation with $p<0.05$ and the "
         r"same margin over the permuted-mask control; the published arm wins nowhere under that criterion (registered), so the column reports "
         r"the CV hierarchy (widened criterion, see the amendment of 05:30). The control reported here is the larger of the two fitting rules' "
         r"null gains, the CV hierarchy having had no permuted run of its own when the table was built. It has since been given one on seeds "
         r"0--1 (\texttt{prereg/SWEEPNULL.md}, five permutations per cell): the substitution is anti-conservative on 8 of the 17 datasets "
         r"rather than conservative as assumed, inflating an excess by at most $0.0086$, and all nine wins clear the $0.002$ floor against the "
         r"hierarchy's own null. Loss: below imputation by at least $0.002$ with $p<0.05$. No correction for the "
         r"number of datasets is applied. The tree's means are in the released results; it is ahead of the CV hierarchy on every dataset.}",
         r"\label{tab:sweep}", r"\setlength{\tabcolsep}{2.5pt}", r"\begin{tabular}{lcrrrrrrrrl}", r"\toprule",
         r"Dataset & Flag & $|\mathcal{E}|$ & $H_{\mathrm{exc}}$ & Imput. & Indic. & Inter. & Publ. & CV & $\Delta$ & Outcome \\", r"\midrule"]
for _, r in df.sort_values(["src", "flag", "name"], ascending=[False, False, True]).iterrows():
    nm = r["name"][:20].replace("_", r"\_") + (r"$^\dagger$" if r.src == "mechanism" else "") + (r"$^\ddagger$" if r.note == "slice" else "")
    if pd.notna(r.get("n")):
        out = "win" if r.win_cv else ("loss" if r.loss_cv else "no")
        lines.append(f"{nm} & {'yes' if r.flag else 'no'} & {r.n_pat} & {r.hexc:+.2f} & {r.imp:.3f} & {r.ind:.3f} & {r.inter:.3f} & {r.ours:.3f} & {r.fam:.3f} & {r.m_cv:+.3f} & {out} \\\\")
    else:
        lines.append(f"{nm} & {'yes' if r.flag else 'no'} & {r.n_pat} & {r.hexc:+.2f} & \\multicolumn{{7}}{{l}}{{pending}} \\\\")
lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
(ROOT / "tables/sweep.tex").write_text("\n".join(lines) + "\n")
mac = ["% GENERATED by figures/make_sweep_table.py --- do not edit by hand.",
       f"\\newcommand{{\\SweepDone}}{{{len(done)}}}", f"\\newcommand{{\\SweepPending}}{{{len(df)-len(done)}}}",
       f"\\newcommand{{\\SweepFlagWin}}{{{fw}}}", f"\\newcommand{{\\SweepFlagNo}}{{{fn}}}", f"\\newcommand{{\\SweepUnflagWin}}{{{uw}}}", f"\\newcommand{{\\SweepUnflagNo}}{{{un}}}",
       f"\\newcommand{{\\SweepPubFlagWin}}{{{pfw}}}", f"\\newcommand{{\\SweepPubUnflagWin}}{{{puw}}}",
       f"\\newcommand{{\\SweepRuleFlagWin}}{{{rfw}}}", f"\\newcommand{{\\SweepRuleFlagNo}}{{{rfn}}}", f"\\newcommand{{\\SweepRuleUnflagWin}}{{{ruw}}}", f"\\newcommand{{\\SweepRuleUnflagNo}}{{{run}}}",
       f"\\newcommand{{\\SweepHiggsSlice}}{{{higgs_win}}}", f"\\newcommand{{\\SweepWinTotal}}{{{fw+uw}}}", f"\\newcommand{{\\SweepTotal}}{{{len(done)}}}", f"\\newcommand{{\\SweepBeatBoth}}{{{len(beat_both)}}}", f"\\newcommand{{\\SweepLoss}}{{{int(done.loss_cv.sum())}}}"]
(ROOT / "tables/sweep_counts.tex").write_text("\n".join(mac) + "\n"); print(f"  wrote tables/sweep.tex ({len(df)} rows) and sweep_counts.tex")

# \SweepBeatBoth is generated, but the prose beside it names the datasets BY HAND:
# "\SweepBeatBoth{} (Higgs, frame rates, road safety, crime records)". If the win set moves,
# the macro follows and the names do not, leaving a count that disagrees with its own list.
# Check it here, where the number is produced -- that is the moment drift is introduced.
import glob as _glob
_names = list(beat_both.name)
_bad = []
for _f in _glob.glob(str(ROOT / "*.tex")) + _glob.glob(str(ROOT / "sections-*.tex")):
    for _m in re.finditer(r"\\SweepBeatBoth\{\}\s*\(([^)]*)\)", pathlib.Path(_f).read_text(errors="ignore")):
        _items = [x.strip() for x in _m.group(1).split(",") if x.strip()]
        if len(_items) != len(_names):
            _bad.append((pathlib.Path(_f).name, len(_items), _m.group(1)[:70]))
print(f"  beat_both = {len(_names)}: {_names}")
if _bad:
    print("  !! PROSE DISAGREES with \\SweepBeatBoth -- the hand-written list must be updated:")
    for _n, _c, _t in _bad:
        print(f"     {_n}: prose lists {_c} name(s) for a count of {len(_names)}  ({_t})")
else:
    print(f"  prose lists beside \\SweepBeatBoth all carry {len(_names)} name(s)")

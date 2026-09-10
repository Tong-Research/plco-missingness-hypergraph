"""Result 168: the diagnostic validation re-scored against tuned mean imputation (referee point, 2026-09-03).

The published AUC (0.757 for H_exc, 0.618 for iota) defines a win as a significant paired gain over the tuned
indicator model. MIMIC-IV's outcome was a gain over tuned imputation and a loss to the indicator, so the
validation criterion and the credited prediction differed. This script scores both measures under the
imputation criterion too, from the committed files results/synthetic_suite_1se.csv and
results/diagnostic_validation.csv (row-aligned by construction; the join is verified on delta and p).
"""
import pathlib
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
HERE = pathlib.Path(__file__).resolve().parent.parent

def main():
    s = pd.read_csv(HERE / "results/synthetic_suite_1se.csv"); d = pd.read_csv(HERE / "results/diagnostic_validation.csv")
    assert len(s) == len(d) == 108
    assert np.allclose(s.delta_vs_tuned_ind, d.delta) and np.allclose(s.p_vs_tuned_ind, d.p), "row alignment failed"
    m = s.copy(); m["iota"] = d.iota.to_numpy(); m["het_excess"] = d.het_excess.to_numpy()
    di = m.safe_adaptive - m.tuned_impute
    crit = {"sig_vs_indicator": (m.p_vs_tuned_ind < .05) & (m.delta_vs_tuned_ind > 0),
            "pos_vs_indicator": m.delta_vs_tuned_ind > 0,
            "floor_vs_imputation": di >= 0.002, "cap_vs_imputation": di >= 0.01, "pos_vs_imputation": di > 0}
    rows = [dict(criterion=k, n_win=int(y.sum()), auc_hexc=roc_auc_score(y, m.het_excess), auc_iota=roc_auc_score(y, m.iota)) for k, y in crit.items()]
    out = pd.DataFrame(rows); out.to_csv(HERE / "results/diagnostic_rescore.csv", index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    mim = (di >= 0.002) & (m.delta_vs_tuned_ind <= 0)
    print(f"MIMIC-shaped configs (beat imputation >= 0.002, not the indicator): {int(mim.sum())}/108; "
          f"H_exc mean {m.het_excess[mim].mean():+.3f} vs rest {m.het_excess[~mim].mean():+.3f}")

if __name__ == "__main__":
    main()

# Pre-registration manifest

Every file here was written BEFORE the run it governs -- the `written` column is the
file's own mtime, preserved by the copy. None was tracked by git until 2026-09-02: the
originals lived under `results/`, which `.gitignore` excludes wholesale, so each commit
message that said 'pre-registered' referred to a file the repository never held. The
predictions were made in advance; the record of them was not durable. It is now.

| id | original path | written (mtime) | tracked copy |
|---|---|---|---|
| A4 | `results/ideas/A4/PREREG.md` | 2026-08-27 10:25:24 | `prereg/A4.md` |
| A4b | `results/ideas/A4b/PREREG.md` | 2026-08-27 10:35:19 | `prereg/A4b.md` |
| B7 | `results/ideas/B7/PREREG.md` | 2026-08-27 11:23:49 | `prereg/B7.md` |
| xarch | `results/xarch/PREREG.md` | 2026-09-02 10:42:11 | `prereg/xarch.md` |
| R1 | `results/ideas/R1/PREREG.md` | 2026-09-02 13:42:46 | `prereg/R1.md` |
| MIMIC.md | 2026-09-02 15:46:42 | approved 15:46; run not started at approval |
| PROJECTION.md | 2026-09-03 19:24:46 | approved 19:23; run not started at approval; run script experiments/idea_h_projection_test.py, scorer score_projection.py committed with it |
| HIGGS.md | 2026-09-04 00:11:44 | approved 00:11; run not started at approval; runner experiments/run_candidate.py, scorer score_candidate.py committed 8130de5 |
| PORTO.md | 2026-09-04 00:11:44 | approved 00:11; run not started at approval; runner experiments/run_candidate.py, scorer score_candidate.py committed 8130de5 |
| ACS.md | 2026-09-04 00:11:44 | approved 00:11; run not started at approval; runner experiments/run_candidate.py, scorer score_candidate.py committed 8130de5 |
| HCAL.md | 2026-09-04 21:51:22 | approved 21:51; run not started at approval; runner experiments/run_hcal.py, scorer score_hcal.py committed c6b091c; sha256 cedd742cbb6f of the approved text; outcome appended 22:15 (P1, P4, P5 hold; P2, P3(i) fail; (b),(c) apply); amendment 22:05 binning guard |
| DRIFT.md | 2026-09-05 18:57:37 | approved 18:51; run not started at approval; runner experiments/drift_probe.py, scorer score_drift.py committed ada0c19; sha256 ad7d05860991 |
| THIRDCOND.md | 2026-09-06 10:07:07 | approved 10:02; run not started at approval; runner experiments/third_condition.py committed 9962791; sha256 6a6d45021caf |
7fb3feed7a495656  prereg/RECOV.md  frozen 2026-09-06 11:20
dc8934706ff74c3d  prereg/DISTIL.md  frozen 2026-09-06 11:20
266285504e08f070  prereg/UNSEEN.md  frozen 2026-09-06 11:20
53a14711ca647963  prereg/AMPUTE.md  frozen 2026-09-06 11:20
4e2551d74abcf5be  prereg/PROXY.md  frozen 2026-09-06 11:20
22bfce9748ee1d38  prereg/PRIV.md  frozen 2026-09-06 15:05
0693ca8540a153aa  prereg/POSETSIM.md  frozen 2026-09-06 15:05
06abffe9e642c4b2  prereg/SCHEMA0.md  frozen 2026-09-06 15:05
fa98287aba525311  prereg/EXPLORE.md  frozen 2026-09-06 16:10
4ffba9e4063232d9  prereg/EXPLORE-CONFIRM.md  frozen EXPLORE-CONFIRM
2026-09-06 16:45  prereg/EXPLORE-CONFIRM.md  frozen 
63038ddbb75b1688  prereg/REGIME.md  frozen REGIME
2026-09-06 17:50  prereg/REGIME.md  frozen 
9dd5288e90316e31  prereg/RRSTRUCT.md  frozen 2026-09-06 18:30
2e8136ce52be2c02  prereg/MASKINC.md  frozen 2026-09-06 18:30
9fb691ec2c5ecc5d  prereg/RRMIRROR.md  frozen RRMIRROR
2026-09-06 20:35  prereg/RRMIRROR.md  frozen 
167da95d72f1cd38  prereg/SMDI.md  frozen SMDI
2026-09-06 21:10  prereg/SMDI.md  frozen 
229549c7c0130a08  prereg/PLASMODE.md  frozen PLASMODE
2026-09-06 22:15  prereg/PLASMODE.md  frozen 
c9faa73991f37649  prereg/MVPCDET.md  frozen MVPCDET
2026-09-06 22:30  prereg/MVPCDET.md  frozen 
7ed995324c47d679  prereg/DETSWEEP.md  frozen DETSWEEP
2026-09-06 23:50  prereg/DETSWEEP.md  frozen 
4c52e5b9a105f906  prereg/MISDIAG.md  frozen MISDIAG
2026-09-07 00:15  prereg/MISDIAG.md  frozen 

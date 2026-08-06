import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
d = json.load(open(HERE / "results.json"))
P = d["params"]
SINC_LIM, SAB_LIM = P["sinc_local_lim_Wm2"], P["sab_4cm2_lim_Wm2"]
a = d["arrays"]["illuminator_1600"]
g_ratio = 10 ** ((45 - 37) / 10)          # scale 37 dBi model -> 45 dBi AN/SPG-62
Ptx = 1e4                                  # 10 kW CW

rs, cA, cB = [], [], []
for rk, rr in a["ranges"].items():
    e = rr["yaw0"]; r = float(rk[1:])
    rs.append(r)
    cA.append(Ptx * e["sinc_ff"] * g_ratio / SINC_LIM)         # industry incident / RL
    cB.append(Ptx * e["wc_local_4cm2"] * g_ratio / SAB_LIM)    # AEGIS worst-case absorbed / BR
rs = np.array(rs); cA = np.array(cA); cB = np.array(cB)
# fine range for zone boundary (1/r^2 scaling anchored at r=20)
rf = np.linspace(5, 600, 400)
k20 = 20.0
cA_ref = Ptx * a["ranges"]["r20"]["yaw0"]["sinc_ff"] * g_ratio / SINC_LIM * (k20 / rf) ** 2
cB_ref = Ptx * a["ranges"]["r20"]["yaw0"]["wc_local_4cm2"] * g_ratio / SAB_LIM * (k20 / rf) ** 2

fig, ax = plt.subplots(1, 2, figsize=(10, 4.0))
ax[0].loglog(rf, cA_ref, "-", color="#c44", lw=2, label="Industry: unperturbed S_inc / reference level")
ax[0].loglog(rf, cB_ref, "--", color="#28c", lw=2, label="AEGIS: worst-case absorbed APD / basic restriction")
ax[0].axhline(1.0, color="k", lw=0.8, ls=":")
rzA = rf[np.argmin(np.abs(cA_ref - 1))]; rzB = rf[np.argmin(np.abs(cB_ref - 1))]
ax[0].axvline(rzA, color="#c44", lw=0.8, alpha=0.6); ax[0].axvline(rzB, color="#28c", lw=0.8, alpha=0.6)
ax[0].set_xlabel("range r (m)"); ax[0].set_ylabel("compliance ratio (=1 at zone edge)")
ax[0].set_title(f"Keep-out zone, 45 dBi X-band emitter, 10 kW\nAEGIS {rzB:.0f} m vs industry {rzA:.0f} m", fontsize=9)
ax[0].legend(fontsize=7, loc="lower left"); ax[0].grid(True, which="both", alpha=0.2)

# panel 2: the coupling identity that causes the tie
rr2 = np.array([a["ranges"][k]["yaw0"]["wc_local_4cm2"] / a["ranges"][k]["yaw0"]["sinc_ff"]
                for k in a["ranges"]])
ax[1].semilogx(rs, rr2, "o-", color="#28c", label="wc absorbed APD / S_inc (this work)")
ax[1].axhline(SAB_LIM / SINC_LIM, color="#c44", ls="--",
              label=f"limit ratio 100/185 = {SAB_LIM/SINC_LIM:.2f}")
ax[1].axhline(0.489, color="k", ls=":", label="normal-incidence skin T0 = 0.489")
ax[1].set_xlabel("range r (m)"); ax[1].set_ylabel("absorbed / incident")
ax[1].set_ylim(0, 0.7)
ax[1].set_title("Why they tie: ICNIRP's RL already\nembeds the absorbed/incident coupling", fontsize=9)
ax[1].legend(fontsize=7, loc="lower right"); ax[1].grid(True, which="both", alpha=0.2)
fig.tight_layout()
fig.savefig(HERE / "fig_zone_comparison.png", dpi=130)
print("wrote fig_zone_comparison.png ; zones AEGIS", round(rzB), "industry", round(rzA))

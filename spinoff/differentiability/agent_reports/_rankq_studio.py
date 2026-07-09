"""Rank / effective-rank of the REAL ray-traced AEGIS exposure operator Q.

Uses the studio grid of precomputed Q matrices (data/studio/qop/*.npz), which
were built by AEGIS's full pipeline: real DiffeRT/Sionna rays -> body_channel
(Fresnel t_s/t_p, tissue depth coupling) -> Q = sum_t area_t G_t^H G_t.

Metrics (all on the descending eigenvalue spectrum lam of the M x M Hermitian PSD Q):
  numrank_e6 : # eig > 1e-6 * lam_max        (numerical algebraic rank, loose)
  numrank_e10: # eig > 1e-10 * lam_max       (numerical algebraic rank, tight)
  r90        : # eig for cumulative sum >= 90% of trace   (paper's "effective rank")
  r99        : # eig for cumulative sum >= 99% of trace
  PR         : (sum lam)^2 / sum lam^2        (participation ratio)
  stable     : trace / lam_max               (stable rank)
  top1       : lam_max / trace               (dominant-mode share)
"""
import glob, os, re
import numpy as np

QDIR = "/home/user/aegis/data/studio/qop"


def metrics(Q):
    Q = 0.5 * (Q + Q.conj().T)
    lam = np.linalg.eigvalsh(Q).real[::-1]
    lam = np.maximum(lam, 0.0)
    tot = lam.sum()
    lmax = lam[0]
    cum = np.cumsum(lam) / tot
    r90 = int(np.searchsorted(cum, 0.90) + 1)
    r99 = int(np.searchsorted(cum, 0.99) + 1)
    return dict(
        M=len(lam),
        numrank_e6=int((lam > 1e-6 * lmax).sum()),
        numrank_e10=int((lam > 1e-10 * lmax).sum()),
        r90=r90, r99=r99,
        PR=float(tot**2 / (lam**2).sum()),
        stable=float(tot / lmax),
        top1=float(lmax / tot),
    )


def parse(name):
    m = re.match(r"(\w+?)_(los|nlos)_bs(\d+)_(\d+)(?:_seed(\d+))?$", name[:-4])
    if not m:
        return None
    return dict(mesh=m.group(1), cond=m.group(2), bs=int(m.group(3)),
                freq=int(m.group(4)), seed=(int(m.group(5)) if m.group(5) else None))


def main():
    rows = []
    for f in sorted(glob.glob(os.path.join(QDIR, "*.npz"))):
        info = parse(os.path.basename(f))
        if info is None:
            continue
        d = np.load(f, allow_pickle=True)
        Q = d["Q"]
        rows.append({**info, **metrics(Q)})

    import statistics as st
    def agg(sel, key):
        vals = [r[key] for r in rows if sel(r)]
        return vals

    # ---- 1. Grand summary over ALL configs (seeded trials only for iid stats) ----
    seeded = [r for r in rows if r["seed"] is not None]
    print(f"# studio qop files parsed: {len(rows)}  (seeded trials: {len(seeded)})")
    print(f"# meshes={sorted(set(r['mesh'] for r in rows))} bs={sorted(set(r['bs'] for r in rows))} "
          f"freqs={sorted(set(r['freq'] for r in rows))} cond={sorted(set(r['cond'] for r in rows))}")
    print()
    print("=== GRAND SUMMARY across all seeded trials (real ray-traced Q) ===")
    for key in ["r90", "r99", "PR", "stable", "top1", "numrank_e6", "numrank_e10"]:
        v = np.array([r[key] for r in seeded], float)
        print(f"  {key:11s}: median={np.median(v):7.2f}  p10={np.percentile(v,10):7.2f}  "
              f"p90={np.percentile(v,90):7.2f}  min={v.min():7.2f}  max={v.max():7.2f}")

    # ---- 2. Effective rank vs FREQUENCY (fixed physical aperture!) ----
    print()
    print("=== FREQ SWEEP: eff-rank vs dosimetry freq, FIXED physical array (lambda/2 @28GHz) ===")
    print("    (studio array spacing is fixed; aperture does NOT scale with lambda)")
    for bs in sorted(set(r["bs"] for r in rows)):
        print(f"  -- bs{bs} ({bs*bs} elements), LOS, median over mesh+seed --")
        print(f"     {'freq':>5} {'r90':>6} {'r99':>6} {'PR':>7} {'stable':>7} {'top1':>6} {'numrank_e6':>10}")
        for freq in sorted(set(r["freq"] for r in rows)):
            sub = [r for r in seeded if r["bs"] == bs and r["freq"] == freq and r["cond"] == "los"]
            if not sub:
                continue
            def med(k): return np.median([r[k] for r in sub])
            print(f"     {freq:5d} {med('r90'):6.1f} {med('r99'):6.1f} {med('PR'):7.2f} "
                  f"{med('stable'):7.2f} {med('top1'):6.3f} {med('numrank_e6'):10.1f}  (n={len(sub)})")

    # ---- 3. LOS vs NLOS (multipath richness / angular spread) ----
    print()
    print("=== LOS vs NLOS at 28 GHz (angular spread / multipath richness) ===")
    for bs in sorted(set(r["bs"] for r in rows)):
        for cond in ["los", "nlos"]:
            sub = [r for r in seeded if r["bs"] == bs and r["freq"] == 28 and r["cond"] == cond]
            if not sub:
                continue
            def med(k): return np.median([r[k] for r in sub])
            print(f"  bs{bs:2d} {cond:4s}: r90={med('r90'):5.1f} r99={med('r99'):5.1f} "
                  f"PR={med('PR'):6.2f} top1={med('top1'):.3f}  (n={len(sub)})")

    # ---- 4. Array size bs8 (M=64) vs bs16 (M=256) at 28 GHz LOS ----
    print()
    print("=== ARRAY SIZE at 28 GHz LOS (bs8=64 elem vs bs16=256 elem) ===")
    for bs in sorted(set(r["bs"] for r in rows)):
        sub = [r for r in seeded if r["bs"] == bs and r["freq"] == 28 and r["cond"] == "los"]
        if not sub:
            continue
        def med(k): return np.median([r[k] for r in sub])
        M = bs * bs
        print(f"  bs{bs:2d} (M={M:4d}): r90={med('r90'):5.1f} r99={med('r99'):5.1f} PR={med('PR'):6.2f} "
              f"stable={med('stable'):6.2f}  rank/M(r99)={med('r99')/M:.3f}")


if __name__ == "__main__":
    main()

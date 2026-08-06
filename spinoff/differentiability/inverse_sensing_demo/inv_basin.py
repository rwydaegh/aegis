"""Basin-size and observable-domain test for the coherent PO pose inverse problem.

Hypothesis: coherent phase loss at 28 GHz (lambda ~1.07 cm) has a convergence basin of
order lambda. A pose perturbation of 0.3 rad moves body surface points by O(10 cm) >> lambda,
so gradient descent starts many wavelengths outside the basin and cannot converge. Test by
(1) sweeping init perturbation size, (2) comparing coherent vs magnitude-domain observable,
(3) gradient (Adam) vs random search at equal forward-eval budget.
"""
from __future__ import annotations
import numpy as np, torch, smplx, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inv_scatter import po_channel, make_array, verts_of, model

torch.manual_seed(1); np.random.seed(1)
f0=28e9
DIMS=list(range(6))

def trial(init_sigma, freqs, domain="coherent", method="adam", steps=250, n_ant=8, seed=0):
    torch.manual_seed(seed); np.random.seed(seed)
    tx=make_array(n_ant,2.0,1.1,140.0); rx=make_array(n_ant,2.0,1.1,140.0)
    tt=torch.zeros(63); tt[DIMS]=0.4*torch.randn(len(DIMS))
    with torch.no_grad(): y=po_channel(tt,tx,rx,freqs)
    def obsloss(h):
        if domain=="coherent": return ((h-y).abs()**2).mean()
        else: return ((h.abs()-y.abs())**2).mean()   # magnitude domain
    th0=torch.zeros(63); th0[DIMS]=tt[DIMS]+init_sigma*torch.randn(len(DIMS))
    e0=float((th0-tt).norm())
    mask=torch.zeros(63); mask[DIMS]=1.0
    if method=="adam":
        th=th0.clone().detach().requires_grad_(True)
        opt=torch.optim.Adam([th],lr=0.02)
        for it in range(steps):
            opt.zero_grad(); loss=obsloss(po_channel(th,tx,rx,freqs)); loss.backward()
            th.grad*=mask; opt.step()
        pe=float((th.detach()-tt).norm())
    else:  # random search, same eval budget (steps forward passes)
        best=th0.clone();
        with torch.no_grad(): bl=float(obsloss(po_channel(best,tx,rx,freqs)))
        for it in range(steps):
            cand=best.clone(); cand[DIMS]+=0.05*torch.randn(len(DIMS))
            with torch.no_grad(): l=float(obsloss(po_channel(cand,tx,rx,freqs)))
            if l<bl: bl=l; best=cand
        pe=float((best-tt).norm())
    return e0,pe

if __name__=="__main__":
    band=[f0]; wide=[f0+d for d in np.linspace(-2e9,2e9,7)]
    print("== Basin sweep: coherent single-freq, Adam, 6 dims ==")
    for s in [0.005,0.01,0.02,0.05,0.1,0.3]:
        e0,pe=trial(s,band); print(f"  init {e0:.3f} rad -> final {pe:.3f} rad  ({'RECOVER' if pe<e0*0.5 else 'stuck/diverge'})")
    print("== Same, 4 GHz band (7 tones) ==")
    for s in [0.01,0.05,0.1,0.3]:
        e0,pe=trial(s,wide); print(f"  init {e0:.3f} rad -> final {pe:.3f} rad  ({'RECOVER' if pe<e0*0.5 else 'stuck/diverge'})")
    print("== Magnitude-domain observable (smoother?), single freq ==")
    for s in [0.05,0.1,0.3]:
        e0,pe=trial(s,band,domain="mag"); print(f"  init {e0:.3f} rad -> final {pe:.3f} rad  ({'RECOVER' if pe<e0*0.5 else 'stuck/diverge'})")
    print("== Gradient vs random search, equal 250-eval budget, init 0.05 rad, single freq ==")
    for m in ["adam","random"]:
        errs=[trial(0.05,band,method=m,seed=s)[1] for s in range(4)]
        print(f"  {m}: mean final pose err {np.mean(errs):.3f} rad over 4 seeds")

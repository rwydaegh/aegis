"""Decisive fast tests (all single-frequency 28 GHz, 6 active dims, 8x8 array):
(1) gradient direction quality: cos(-grad, dir-to-truth) vs distance from truth,
(2) learning-rate control near truth (narrow basin vs wrong direction),
(3) magnitude-domain observable recovery (smoother?),
(4) gradient (Adam) vs random search at equal 250-eval budget.
"""
from __future__ import annotations
import numpy as np, torch, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inv_scatter import po_channel, make_array
torch.manual_seed(3); np.random.seed(3)
f0=28e9; DIMS=list(range(6)); mask=torch.zeros(63); mask[DIMS]=1.0
tx=make_array(8,2.0,1.1,140.0); rx=make_array(8,2.0,1.1,140.0)
tt=torch.zeros(63); tt[DIMS]=0.4*torch.randn(len(DIMS))
with torch.no_grad(): y=po_channel(tt,tx,rx,[f0])
def cohloss(th): return ((po_channel(th,tx,rx,[f0])-y).abs()**2).mean()
def magloss(th): return ((po_channel(th,tx,rx,[f0]).abs()-y.abs())**2).mean()

print("== (1) gradient direction cosine vs distance from truth (coherent) ==")
for d in [0.005,0.01,0.02,0.05,0.1,0.2]:
    cs=[]
    for s in range(6):
        torch.manual_seed(100+s)
        th0=tt.clone(); th0[DIMS]=tt[DIMS]+d*torch.randn(len(DIMS))
        thg=th0.clone().detach().requires_grad_(True); cohloss(thg).backward()
        g=thg.grad[DIMS]; dt=(tt[DIMS]-th0[DIMS])
        cs.append(float((-g*dt).sum()/(g.norm()*dt.norm()+1e-12)))
    print(f"  dist {d:.3f} rad: mean cos {np.mean(cs):+.3f}  (>0 gradient toward truth)")

print("== (2) lr control, coherent, init 0.02 rad, 400 steps ==")
torch.manual_seed(7); th0=tt.clone(); th0[DIMS]=tt[DIMS]+0.02*torch.randn(len(DIMS))
e0=float((th0-tt).norm())
for lr in [2e-2,2e-3,5e-4,1e-4]:
    th=th0.clone().detach().requires_grad_(True); opt=torch.optim.Adam([th],lr=lr)
    for _ in range(400):
        opt.zero_grad(); cohloss(th).backward(); th.grad*=mask; opt.step()
    print(f"  lr={lr:.0e}: {e0:.3f} -> {float((th.detach()-tt).norm()):.3f} rad")

print("== (3) magnitude-domain recovery, init sweep, Adam lr=2e-3, 400 steps ==")
for s in [0.02,0.05,0.1,0.3]:
    torch.manual_seed(9); th0=tt.clone(); th0[DIMS]=tt[DIMS]+s*torch.randn(len(DIMS))
    e0=float((th0-tt).norm())
    th=th0.clone().detach().requires_grad_(True); opt=torch.optim.Adam([th],lr=2e-3)
    for _ in range(400):
        opt.zero_grad(); magloss(th).backward(); th.grad*=mask; opt.step()
    pe=float((th.detach()-tt).norm())
    print(f"  init {e0:.3f} -> {pe:.3f} rad  ({'recover' if pe<0.6*e0 else 'stuck'})")

print("== (4) Adam vs random search, equal 250-eval budget, coherent, init 0.05 rad ==")
def adam_run(seed):
    torch.manual_seed(seed); th0=tt.clone(); th0[DIMS]=tt[DIMS]+0.05*torch.randn(len(DIMS))
    th=th0.clone().detach().requires_grad_(True); opt=torch.optim.Adam([th],lr=2e-3)
    for _ in range(250):
        opt.zero_grad(); cohloss(th).backward(); th.grad*=mask; opt.step()
    return float((th.detach()-tt).norm())
def rand_run(seed):
    torch.manual_seed(seed); th0=tt.clone(); th0[DIMS]=tt[DIMS]+0.05*torch.randn(len(DIMS))
    best=th0.clone();
    with torch.no_grad(): bl=float(cohloss(best))
    for _ in range(250):
        c=best.clone(); c[DIMS]+=0.02*torch.randn(len(DIMS))
        with torch.no_grad(): l=float(cohloss(c))
        if l<bl: bl=l; best=c
    return float((best-tt).norm())
a=[adam_run(s) for s in range(5)]; r=[rand_run(s) for s in range(5)]
print(f"  Adam   mean final {np.mean(a):.3f} rad (init 0.05)")
print(f"  Random mean final {np.mean(r):.3f} rad (init 0.05)")

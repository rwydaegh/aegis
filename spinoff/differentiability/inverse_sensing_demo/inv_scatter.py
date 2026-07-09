"""Toy inverse-scattering pose recovery through a differentiable PO surface operator.

Chain: SMPL-X pose theta (PyTorch, differentiable) -> vertices -> triangle facets
-> coherent physical-optics scattered field at a multistatic array -> complex channel h.

We simulate y = g(theta_true), then recover theta by gradient descent on ||g(theta)-y||^2.
Everything is torch, so autodiff runs end to end through SMPL-X LBS into the PO integral.

This is the "discarded half" of AEGIS (reflectance instead of transmittance, radiation
integral toward an observer instead of absorbed density at the surface). Self-shadowing is
omitted; only smooth orientation/illumination gates are used (the differentiable-render trick).
"""
from __future__ import annotations
import numpy as np, torch, smplx, time, sys

torch.manual_seed(0); np.random.seed(0)
DEV = "cpu"
C0 = 299792458.0
MP = "/home/user/.aegis/models"

model = smplx.create(MP, model_type="smplx", gender="neutral", use_pca=False, flat_hand_mean=True).to(DEV)
FACES = torch.tensor(model.faces.astype(np.int64), device=DEV)  # (F,3)
BETAS = torch.zeros(1, 10, device=DEV)
GO = torch.zeros(1, 3, device=DEV)

# Optional face subsample for speed (keep every DS-th face). DS=1 => full 20908.
DS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
FACES_S = FACES[::DS]

def verts_of(body_pose):  # body_pose (63,)
    out = model(betas=BETAS, body_pose=body_pose.unsqueeze(0), global_orient=GO)
    return out.vertices[0]  # (V,3)

def facets(v):
    tv = v[FACES_S]                      # (F,3,3)
    c = tv.mean(1)                       # centroid (F,3)
    n = torch.cross(tv[:,1]-tv[:,0], tv[:,2]-tv[:,0], dim=1)
    a = 0.5*torch.norm(n, dim=1, keepdim=True)   # area (F,1)
    n = n/(torch.norm(n,dim=1,keepdim=True)+1e-12)
    return c, n, a.squeeze(1)

def po_channel(body_pose, tx, rx, freqs, kappa=40.0):
    """Coherent PO multistatic channel. Returns complex (n_freq, n_tx, n_rx)."""
    v = verts_of(body_pose)
    c, n, a = facets(v)                  # (F,3),(F,3),(F,)
    # geometry per (tx,facet) and (rx,facet)
    ri = c[None,:,:] - tx[:,None,:]      # (T,F,3) tx->facet
    rs = rx[:,None,:] - c[None,:,:]      # (R,F,3) facet->rx
    di = torch.norm(ri,dim=2); ds = torch.norm(rs,dim=2)
    ui = ri/(di[...,None]+1e-12); us = rs/(ds[...,None]+1e-12)
    ndu_i = (n[None,:,:]*ui).sum(2)      # (T,F)  <0 when facet faces tx
    ndu_s = (n[None,:,:]*us).sum(2)      # (R,F)  >0 when facet faces rx
    illum = torch.nn.functional.softplus(-ndu_i*8)/8   # smooth lit gate (T,F)
    recv  = torch.nn.functional.softplus( ndu_s*8)/8   # smooth visible gate (R,F)
    # specular lobe: reflect ui about n, align with us
    rdir = ui - 2*ndu_i[...,None]*n[None,:,:]          # (T,F,3)
    align = torch.einsum('tfd,rfd->trf', rdir, us)     # (T,R,F) cos of mismatch
    lobe = torch.exp(kappa*(align-1.0))                # sharp specular lobe
    amp = a[None,None,:]*illum[:,None,:]*recv[None,:,:]*lobe   # (T,R,F)
    dtot = di[:,None,:] + ds[None,:,:]                 # (T,R,F) round-trip path
    out = []
    for f in freqs:
        k = 2*np.pi*f/C0
        ph = torch.exp(-1j*k*dtot)                     # (T,R,F)
        h = (amp*ph).sum(2)                            # (T,R)
        out.append(h)
    return torch.stack(out,0)                          # (nf,T,R)

# ---- array geometry: a panel arc around the body at ~2 m, 28 GHz band ----
def make_array(n=8, R=2.0, z=1.0, span=120.0):
    ang = torch.linspace(-span/2, span/2, n)*np.pi/180
    p = torch.stack([R*torch.sin(ang), R*torch.cos(ang), torch.full((n,),z)],1)
    return p.to(DEV)

def run_recovery(active_dims, freqs, n_ant=8, noise=0.0, steps=300, lr=0.02, seed=0, verbose=True):
    torch.manual_seed(seed)
    tx = make_array(n_ant, R=2.0, z=1.1, span=140.0)
    rx = make_array(n_ant, R=2.0, z=1.1, span=140.0)  # multistatic (each tx, each rx)
    # true pose: perturb chosen joints
    theta_true = torch.zeros(63, device=DEV)
    pert = torch.zeros(63, device=DEV)
    pert[active_dims] = 0.4*torch.randn(len(active_dims))
    theta_true = theta_true + pert
    with torch.no_grad():
        y = po_channel(theta_true, tx, rx, freqs)
        if noise>0:
            y = y + noise*y.abs().mean()*(torch.randn_like(y.real)+1j*torch.randn_like(y.imag))
    # init: perturbed guess on the active dims
    theta = torch.zeros(63, device=DEV)
    theta[active_dims] = theta_true[active_dims] + 0.3*torch.randn(len(active_dims))
    theta = theta.clone().detach().requires_grad_(True)
    mask = torch.zeros(63, device=DEV); mask[active_dims]=1.0
    opt = torch.optim.Adam([theta], lr=lr)
    e0 = float((theta.detach()-theta_true).norm())
    v_true = verts_of(theta_true).detach()
    hist=[]
    for it in range(steps):
        opt.zero_grad()
        h = po_channel(theta, tx, rx, freqs)
        loss = ((h-y).abs()**2).mean()
        loss.backward()
        theta.grad *= mask   # only move active dims
        opt.step()
        if it%50==0 or it==steps-1:
            with torch.no_grad():
                perr=float((theta-theta_true).norm())
                vrmse=float((verts_of(theta)-v_true).norm(dim=1).mean())*1000
                hist.append((it,float(loss),perr,vrmse))
    pe=float((theta.detach()-theta_true).norm())
    if verbose:
        print(f"  dims={len(active_dims)} nant={n_ant} nf={len(freqs)} noise={noise}: pose err {e0:.3f}->{pe:.3f} rad, vert RMSE {hist[-1][3]:.1f} mm, loss {hist[0][1]:.2e}->{hist[-1][1]:.2e}")
    return e0, pe, hist

if __name__=="__main__":
    f0=28e9
    band=[f0]                       # single frequency
    wide=[f0+d for d in np.linspace(-1e9,1e9,5)]   # 2 GHz band, 5 tones
    print("== A. Recovery, single freq, increasing pose dimension, 8x8 multistatic ==")
    for nd in [1,3,6,12,21]:
        dims=list(range(nd))
        run_recovery(dims, band, n_ant=8, steps=250)
    print("== B. Single freq vs 2 GHz band (6 dims, harder init handled by bandwidth) ==")
    run_recovery(list(range(6)), band, n_ant=8, steps=250)
    run_recovery(list(range(6)), wide, n_ant=8, steps=250)
    print("== C. Antenna count sweep (6 dims, single freq) ==")
    for na in [2,4,8,12]:
        run_recovery(list(range(6)), band, n_ant=na, steps=250)
    print("== D. Noise robustness (6 dims, wideband, 8x8) ==")
    for ns in [0.0,0.05,0.2]:
        run_recovery(list(range(6)), wide, n_ant=8, noise=ns, steps=250)

import bpy
import numpy as np

# wipe objects, keep materials
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

# fit quay axis from row footprint points (PCA)
ROW_IDS = ["494007824", "514020945", "514020946", "493993762", "494008001", "493993763"]
allp = []
for bid in ROW_IDS:
    allp += [tuple(p) for p in ring_enu(by_id[bid]["ring"])]
P = np.array(allp)
c = P.mean(0)
u, s, vt = np.linalg.svd(P - c)
axis = vt[0]  # along-quay
if axis[1] < 0:
    axis = -axis
nrm = np.array([-axis[1], axis[0]])  # across, pointing away from water side (check sign later)
print("quay axis", axis.round(3), "normal", nrm.round(3))

def to_local(p):
    d = np.asarray(p) - c
    return float(d @ nrm), float(d @ axis)   # (t across, s along)

bb = {}
for bid in ROW_IDS:
    loc = [to_local(p) for p in ring_enu(by_id[bid]["ring"])]
    ts = [q[0] for q in loc]
    ss = [q[1] for q in loc]
    bb[bid] = (min(ts), max(ts), min(ss), max(ss))
    print(bid, named.get(bid), [round(v, 1) for v in bb[bid]])

FRONT = min(b[0] for b in bb.values())
print("front t =", round(FRONT, 1))

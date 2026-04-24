# Skeletal animation: a crash course

From a triangle in the bind pose to its position `r(t)` during a walk cycle, with every matrix labeled.

---

## 1. The high-level picture

A deformable character mesh (10k–100k vertices) is not animated vertex-by-vertex. That would be intractable. Instead:

- The mesh (**skin**) is attached to an invisible tree of bones (the **skeleton**, **rig**, or **armature** in Blender).
- The animator keyframes a handful of joint rotations.
- Each vertex is mathematically bound to one or more bones and follows them automatically via **skinning**.

The data flow, every frame:

```
  animation clip  ──►  local joint transforms L_i(t)
                       │
                       ▼   forward kinematics
                       world joint transforms T_i(t)
                       │
                       ▼   skinning
                       vertex position r(t)
```

Your upper-left-arm triangle goes through steps 1–3 implicitly, via its three vertices.

---

## 2. Jargon glossary

| Term | Meaning |
|---|---|
| Armature / rig / skeleton | The tree of bones |
| Bone / joint | A node in the tree. Mathematically: a coordinate frame |
| Bind pose / rest pose / T-pose | The reference pose where the mesh was attached |
| Skin weights | Per-vertex weights saying how much each bone influences the vertex |
| Skinning | Computing deformed vertex positions from joint transforms |
| LBS / linear blend skinning / SSD | The default skinning algorithm |
| DQS / dual quaternion skinning | An alternative that avoids "candy-wrapper" collapse |
| Forward kinematics (FK) | Joint world transforms ← local transforms |
| Inverse kinematics (IK) | Local transforms ← target world position (foot plants, hand reaches) |
| Keyframe | A sample `(t_k, value_k)` of an animated parameter |
| Animation clip / action | A collection of keyframed curves, e.g. *walk cycle* |
| Local transform | A joint's pose relative to its parent |
| World / global transform | A joint's pose relative to the scene origin |
| Offset matrix / inverse bind matrix | $B_i^{-1}$; maps a vertex from bind-pose world space into bone $i$'s local frame |

---

## 3. Transforms: the language

A joint's pose is an **affine transform** — rotation plus translation (plus optional scale). In 3D the 4×4 homogeneous form is the universal currency:

$$
T = \begin{bmatrix} R & t \\ 0^\top & 1 \end{bmatrix}, \qquad R \in SO(3),\ t \in \mathbb{R}^3.
$$

A point $p \in \mathbb{R}^3$ is extended to $(p_x, p_y, p_z, 1)^\top$ and transformed by matrix multiplication $p' = T\,p$. Transforms compose by matrix product: $T_{AC} = T_{AB}\, T_{BC}$.

### Rotation representations (the usual zoo)

Rotations live on $SO(3)$, a curved manifold, so there are multiple parameterizations with different trade-offs.

| | Size | Pros | Cons |
|---|---|---|---|
| Rotation matrix $R$ | 9 | no ambiguity, fast to apply | heavy; drifts off $SO(3)$ |
| Euler angles $(\alpha,\beta,\gamma)$ | 3 | human-readable (pitch/yaw/roll) | **gimbal lock**; order-dependent |
| Axis–angle $(\hat n, \theta)$ | 4 | natural for joint limits | singular at $\theta=0$ |
| Unit quaternion $q = (w,x,y,z)$ | 4 | no singularities, cheap, smooth interpolation | not intuitive to read |

Blender shows you Euler or quaternion on each bone. Internally, serious animation systems use quaternions.

**Quaternion → rotation matrix** (for a unit quaternion $q=(w,x,y,z)$):

$$
R(q) = \begin{bmatrix}
1-2(y^2+z^2) & 2(xy - zw) & 2(xz + yw) \\
2(xy + zw)   & 1-2(x^2+z^2) & 2(yz - xw) \\
2(xz - yw)   & 2(yz + xw)   & 1-2(x^2+y^2)
\end{bmatrix}
$$

**SLERP** (spherical linear interpolation) between $q_0, q_1$ at $u\in[0,1]$:

$$
\operatorname{slerp}(q_0, q_1, u) = \frac{\sin((1-u)\Omega)}{\sin\Omega}\, q_0 + \frac{\sin(u\Omega)}{\sin\Omega}\, q_1,\quad \cos\Omega = q_0 \cdot q_1.
$$

This is the geodesic on the unit quaternion sphere — the "correct" shortest-arc blend of two orientations. Linearly averaging rotation matrices or quaternions, in contrast, is *not* geodesic, and that mistake is the root cause of the LBS artifact we'll hit in §6.

---

## 4. The rig: a tree of transforms

The skeleton is a rooted tree. Each joint $i$ has:

- a parent index $\mathrm{parent}(i)$ (the root has no parent),
- a **local transform** $L_i$ — its pose relative to the parent,
- a **world transform** $T_i$ — its pose in world space.

Transforms compose, so:

$$
\boxed{\; T_i \;=\; T_{\mathrm{parent}(i)} \cdot L_i \;} \qquad\text{(forward kinematics)}
$$

with $T_{\text{root}} = L_{\text{root}}$. Traverse root→leaves accumulating the product. Cost: $O(\#\text{joints})$, typically a few dozen for a humanoid, negligible.

A typical humanoid hierarchy:

```
root
├── pelvis
│   ├── spine ── chest ── neck ── head
│   ├── chest ── L.clavicle ── L.upper_arm ── L.forearm ── L.hand ── L.fingers…
│   ├── chest ── R.clavicle ── …
│   ├── L.thigh ── L.shin ── L.foot ── L.toe
│   └── R.thigh ── …
```

Your triangle is parented, through skin weights, primarily to `L.upper_arm`.

---

## 5. Bind pose and the inverse bind matrix

Here is the crucial step — the one that confuses people most often.

The mesh was authored in a specific pose: the **bind pose**, usually a T-pose. At bind time, every joint $i$ has a world transform $B_i$, the **bind-pose world matrix**.

A vertex $v$ in bind-pose world space can be re-expressed in bone $i$'s local frame:

$$
v^{(i)}_{\text{local}} \;=\; B_i^{-1}\, v.
$$

$B_i^{-1}$ is the **inverse bind matrix** (also called the **offset matrix** in Assimp/DirectX, or the **bind-shape matrix**'s inverse in COLLADA). It is computed once and stored.

Now suppose the joint moves. At time $t$ its world transform is $T_i(t)$. If the vertex were *rigidly* attached to bone $i$, it would be sent back out to world space by:

$$
v^{(i)}(t) \;=\; T_i(t)\, B_i^{-1}\, v.
$$

So the **skinning matrix** of bone $i$ is

$$
\boxed{\; M_i(t) \;=\; T_i(t)\, B_i^{-1} \;}
$$

Sanity check: at the bind time the skeleton is in the bind pose, so $T_i = B_i$, giving $M_i = B_i B_i^{-1} = I$. The vertex does not move. Good.

---

## 6. Skinning: vertices follow (multiple) joints

If each vertex belonged to exactly one bone, we'd be done: $r(t) = M_j(t) v$. But at joints — elbow, shoulder, hip — the skin has to smoothly follow *several* bones or it creases visibly.

So every vertex carries a small **weight list** $\{(j, w_j)\}$ with

$$
\sum_j w_j = 1, \qquad w_j \ge 0,
$$

typically 2–4 influences per vertex.

### Linear Blend Skinning (LBS)

The default algorithm in every mainstream DCC tool and game engine:

$$
\boxed{\;
r(t) \;=\; \sum_{j \in \mathrm{infl}(v)} w_j\, M_j(t)\, v
\;=\; \sum_{j} w_j\, T_j(t)\, B_j^{-1}\, v
\;}
$$

That is the answer to your question for a single vertex. A triangle is three vertices; each is skinned independently and the triangle is re-rasterized from the three deformed positions.

LBS is fast (handful of $4\times 4$ matvecs per vertex, trivially parallel in a GPU vertex shader) and differentiable.

**Why it sometimes fails — the "candy-wrapper" collapse.** If two bones are twisted ~180° relative to each other (arm twist, strong elbow bend), the weighted *matrix sum* is near-degenerate: you're linearly averaging two rotations, but $SO(3)$ is not a vector space. The skin pinches toward the bone axis and loses volume.

### Dual Quaternion Skinning (DQS)

A **dual quaternion** $\hat q = q_r + \varepsilon q_d$ (with $\varepsilon^2 = 0$) encodes a rigid transform (rotation + translation) as a single algebraic object, and blending them respects rotational geometry:

$$
\hat q(t) = \operatorname{normalize}\!\Bigl(\textstyle\sum_j w_j\, \hat q_j(t)\Bigr), \qquad r(t) = \hat q(t)\, v\, \hat q(t)^*.
$$

Elbows bend without collapsing. Trade-offs: slightly more expensive, and pure DQS cannot represent non-uniform scale or shear. Blender, Maya, Unity and Unreal all offer it as an option ("preserve volume" checkbox in Blender's armature modifier).

Further refinements you might meet in the wild: **optimized center of rotation** (Le & Hodgins 2016), **delta mush**, **implicit skinning**, plus neural methods (NeuroSkinning, SNARF). LBS remains the default because it is cheap, stable, and good enough for 95% of rigs.

---

## 7. Animation data: keyframes and curves

An **animation clip** is a set of scalar curves, one per animated channel. For a skeleton, the usual channels per joint are:

- 3 translation components (usually only on the root),
- 4 quaternion components (or 3 Eulers) for rotation,
- optional 3 scale components.

A **keyframe** is a sample $(t_k, \text{value}_k)$. Between keyframes:

- Translation & scale: linear, or cubic Bezier (Blender's F-curves default to Bezier).
- Rotation: **SLERP** on quaternions (or Bezier on Euler, but beware gimbal-lock singularities).

So at time $t$, for joint $i$ we evaluate its channel curves and reassemble

$$
L_i(t) \;=\; \underbrace{T_{\text{trans}}(t)}_{\text{4×4 translation}} \,\cdot\, \underbrace{R_i(t)}_{\text{4×4 rotation from slerp}(q_a, q_b)} \,\cdot\, \underbrace{S_i(t)}_{\text{4×4 scale, often }I}.
$$

### Walk cycle specifics

A walk cycle is a *periodic* clip, typically 1.0–1.5 seconds long. Animators traditionally key four canonical poses per step (contact → down → pass → up), mirrored for the opposite leg — 8 poses per full 2-step cycle. Between poses everything is interpolated. The clip is looped with $L_i(t) = L_i(t \bmod T)$.

Two conventions for making the character actually move:

1. **In-place**: the root stays at the origin; the game engine translates the whole armature along the path. One clip retargets to any trajectory.
2. **Root motion**: the root translation channel actually moves forward each cycle, and per frame the engine reads $\Delta$ root translation to advance the character collider. Tighter foot contact; harder to retarget.

For your upper-arm triangle the directly relevant channels are:

- `L.upper_arm` rotation: swings anti-phase with the same-side leg, amplitude ~±30° about the shoulder-local X axis.
- `L.clavicle` rotation: small bob.
- `pelvis` rotation and translation: small vertical bob at 2× cycle frequency; pelvic twist at 1× frequency.
- `root` translation: zero if in-place; forward ramp if root-motion.

All of these multiply up the FK chain into $T_{\text{L.upper\_arm}}(t)$, which feeds $M_{\text{L.upper\_arm}}(t)$, which dominates the LBS sum for your vertex.

---

## 8. Putting it all together: $r(t)$ for your triangle

Everything assembled, from the constant bind-pose vertex $v$ to its animated position.

**Precompute once (at load time):**

1. Forward-kinematics the bind skeleton to get $B_i$ for every joint.
2. Store the inverse bind matrices $B_i^{-1}$.
3. Store each vertex's influence list $\{(j, w_j)\}$.

**Each frame, at time $t$:**

4. Evaluate the animation curves to get, per joint,

$$
L_i(t) \;=\; T_{\text{trans},i}(t)\cdot R_i(t)\cdot S_i(t),
$$

where $R_i(t)$ comes from SLERPing the two bracketing rotation keyframes.

5. Walk the skeleton tree root→leaves to get world transforms

$$
T_i(t) \;=\; T_{\mathrm{parent}(i)}(t)\,\cdot\, L_i(t).
$$

6. Assemble skinning matrices

$$
M_i(t) \;=\; T_i(t)\, B_i^{-1}.
$$

7. For each vertex $v$ of your triangle, compute

$$
\boxed{\;
r(t) \;=\; \sum_{j \in \mathrm{infl}(v)} w_j\, M_j(t)\, v.
\;}
$$

8. Do this for all three triangle vertices. The triangle is now in its new position. Normals transform by $M_j^{-\top}$ if you care about lighting, or in practice are skinned the same way as positions and renormalized — the difference only shows up under non-uniform scale.

### Concrete example for your upper-left-arm triangle

Suppose the triangle has vertices $v_1, v_2, v_3$ somewhere on the biceps, and weights concentrated on three bones:

| Vertex | $w_{\text{L.clavicle}}$ | $w_{\text{L.upper\_arm}}$ | $w_{\text{L.forearm}}$ |
|---|---|---|---|
| $v_1$ (near shoulder) | 0.20 | 0.80 | 0.00 |
| $v_2$ (mid-biceps) | 0.00 | 1.00 | 0.00 |
| $v_3$ (near elbow) | 0.00 | 0.85 | 0.15 |

Then

$$
r_k(t) \;=\; w^{(k)}_{\text{clav}}\, M_{\text{clav}}(t)\, v_k \;+\; w^{(k)}_{\text{up}}\, M_{\text{up}}(t)\, v_k \;+\; w^{(k)}_{\text{fore}}\, M_{\text{fore}}(t)\, v_k.
$$

During the walk, the shoulder rotation dominates all three $M_j(t)$ through the FK chain, so the whole triangle swings back-and-forth along an arc of radius ~(distance from vertex to shoulder pivot), exactly as rigid-body kinematics predicts. The small clavicle and forearm weights smooth the deformation at the shoulder and elbow seams, preventing creases.

---

## 9. The canonical human: parametric body models (SMPL and friends)

Suppose you don't want to model or buy a character. You just want *the* human — a clean shrink-wrapped mesh, skeleton inside, nothing else. Does it exist? Yes. The field has standardized on a family of **parametric body models** — statistical models learned from thousands of 3D body scans. Any human body is parameterized by two low-dimensional vectors:

- $\beta$ — **shape** (body proportions: tall/short, skinny/wide, etc.),
- $\theta$ — **pose** (joint angles).

Set both to zero and you get a canonical "mean human" in the bind pose. That is the most canonical human mesh in graphics today.

### SMPL — the one everyone uses

SMPL has:

- **6890 vertices, 13 776 triangles**, fixed topology (every instance has the same connectivity).
- **24 joints** organized in the standard humanoid hierarchy (root = pelvis).
- A **template mesh** $\bar T \in \mathbb{R}^{6890\times 3}$ — the population mean.
- **Shape parameters** $\beta \in \mathbb{R}^{10}$ — the first 10 PCA components of body-scan shape variation.
- **Pose parameters** $\theta \in \mathbb{R}^{72}$ — 24 joints × 3-DoF axis–angle rotations.
- Fixed **skinning weights** $\mathcal{W} \in \mathbb{R}^{6890 \times 24}$ (rows sum to 1).
- Learned **blend-shape bases** $\mathcal{S} \in \mathbb{R}^{6890 \times 3 \times 10}$ (shape) and $\mathcal{P} \in \mathbb{R}^{6890 \times 3 \times 207}$ (pose correctives that fix LBS candy-wrapping).
- A **joint regressor** $\mathcal{J} \in \mathbb{R}^{24 \times 6890}$ that predicts joint locations from the shaped mesh (so the skeleton scales with $\beta$).

The full model is

$$
M(\beta, \theta) \;=\; W\!\Bigl(T(\beta, \theta),\; J(\beta),\; \theta,\; \mathcal{W}\Bigr),
$$

with the *shape-and-pose-corrected* template

$$
T(\beta,\theta) \;=\; \bar T \;+\; B_S(\beta) \;+\; B_P(\theta),
$$

where

$$
B_S(\beta) = \sum_{n=1}^{10} \beta_n \mathcal{S}_n, \qquad B_P(\theta) = \sum_{n=1}^{207} \bigl(R_n(\theta) - R_n(\theta^*)\bigr)\, \mathcal{P}_n,
$$

and $W(\cdot)$ is ordinary **LBS** (the exact formula from §6). So the entire model is just §1–§8 of this primer with two learned corrections added to the template before skinning:

- $B_S(\beta)$: deforms the T-pose mesh from *mean human* to *this specific body*.
- $B_P(\theta)$: pose-dependent correctives that un-pinch the LBS artifacts near joints — cheap, local, effective.

Set $\beta = 0$ and $\theta = 0$ and you have the canonical mean human in T-pose. That is the answer to your question.

### SMPL's extended family

| Model | Adds | Vertices | Use |
|---|---|---|---|
| **SMPL** | body only | 6890 | the baseline |
| **SMPL-H** | articulated hands (merged MANO) | 6890 + hand joints | body + fingers |
| **SMPL-X** | hands + expressive face (MANO + FLAME) | 10 475 | full expressive avatar, current SOTA in research |
| **MANO** | just the hand | 778 | hand tracking |
| **FLAME** | just the head/face | 5023 | face tracking, talking heads |
| **STAR** | sparser, more localized blendshapes than SMPL | 6890 | improved deformation, same topology story |
| **GHUM / GHUML** | Google's alternative, nonlinear VAE shape space | 10 168 | Google's ecosystem (MediaPipe) |

SMPL-X is where the field has mostly consolidated as of the mid-2020s. Datasets (**AMASS**, thousands of hours of mocap retargeted onto SMPL-X), priors (**VPoser** — a VAE over valid poses), and downstream tools (**HuMoR**, **SLAHMR**, **PHALP**) all speak SMPL-X.

### How to actually get one

- **Python**: `pip install smplx`, register at https://smpl-x.is.tue.mpg.de to download the `.npz` model files (free for research; commercial use needs a license from MPI). Then:

  ```python
  import smplx, torch
  model = smplx.create("models/", model_type="smpl", gender="neutral")
  out = model(betas=torch.zeros(1,10), body_pose=torch.zeros(1,69), global_orient=torch.zeros(1,3))
  vertices = out.vertices   # (1, 6890, 3)  — the canonical human
  ```

- **Blender add-on**: *SMPL-X Blender add-on* from MPI — drops the mesh + armature into the scene, with sliders for $\beta$ and regular bone controls for $\theta$.

- **Unity / Unreal**: same add-on ships FBX exporters.

### Alternatives if SMPL's license bothers you

- **MakeHuman** (open source, GPL) — procedural, artist-friendly, exports a rigged mesh. Not statistical but very configurable.
- **Mixamo** (Adobe, free) — upload any humanoid mesh, it auto-rigs it and gives you a library of walk/run/jump clips retargeted to a shared skeleton. Great if you already have a character you like.
- **Meta Avatars / Ready Player Me** — cartoony stylized humans, production-grade rigs, free tiers.

For a physics-accurate exposure simulation like AEGIS, SMPL/SMPL-X is almost certainly the right choice: watertight, manifold, consistent topology across subjects (so you can reuse per-vertex quantities like tissue labels), parameterized shape for population studies, and a standard skeleton for pose-dependent dosimetry.

---

## 10. Where to go from here

- **Blender**: tab into **Weight Paint** mode on any rigged mesh — you are literally editing the $w_j$ values with a brush. Toggle the armature modifier's *Preserve Volume* to see LBS vs DQS side by side.
- Gregory, *Game Engine Architecture*, ch. 11 — the best end-to-end treatment.
- Lewis, Cordner, Fong, *Pose Space Deformation* (SIGGRAPH 2000) — the paper that cemented LBS + blend-shape correctives as the modern baseline.
- Kavan et al., *Skinning with Dual Quaternions* (I3D 2007) — the DQS paper; the math is very readable.
- Le, Hodgins, *Real-time skeletal skinning with optimized centers of rotation* (SIGGRAPH 2016) — modern cheap fix for LBS.
- **glTF 2.0** spec, `Skins` section — the shortest correct description of this whole pipeline, matches the formulas above exactly.

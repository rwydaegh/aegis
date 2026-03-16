# Overview

AEGIS provides nine fidelity levels for computing absorbed power density on human body meshes. Each level adds a physical correction to the previous one, trading accuracy for computational cost.

The typical workflow:

1. Load a tissue model (skin properties at your frequency)
2. Load a body mesh (triangle mesh in STL or OBJ format)
3. Define propagation paths (directions and powers of incoming waves)
4. Run the engine at your chosen fidelity level
5. Inspect the result (per-triangle Sab, total P_abs, compliance status)

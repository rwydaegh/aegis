# R2 storage note

The roughly 100 GB under `r2:aegis-studio` appears to be the older Coherent Exposure Studio precompute grid: body-channel and exposure-operator packs, body maps, meshes, and ray packs. It may be obsolete for the paper campaign, but it is not safe to treat it as disposable until its current object inventory and hashes are recorded.

For v2, use a separate immutable, content-addressed prefix. Do not overwrite or reuse Studio object names. After the v2 campaign is copied and independently verified with `rclone check --download`, inventory the Studio prefix and classify each subtree as:

- still used by the viewer;
- worth retaining as an archived historical dataset;
- reproducible and safe to delete.

Only delete the third category, after preserving a file manifest, sizes, hashes, source/version provenance, and any viewer dependency mapping. R2 capacity is not the constraint, so there is no reason to risk deleting the only copy merely to make room for v2.

The desired final layout is therefore separate prefixes for Studio, frozen paper versions, and the new v2 evidence bundle. Cleanup comes after verification, not before it.

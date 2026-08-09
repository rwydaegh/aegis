# Resumable hybrid panorama semantics

`semantic_twin.cli.hybrid_batch` is the production operations wrapper around
the existing single-panorama runner. It does not alter segmentation or fusion.
It supplies the reviewed, immutable contract for every station:

* Mapillary Vistas Mask2Former at `1536` inference pixels
* SAM 3 at its native `1008` square resolution, with the reviewed concept
  catalogue and prompt batch `32`
* `4096 x 2048` equirectangular output
* CUDA and `--production`, with both model revisions and the SAM 3 source
  commit pinned in the job and station sidecars

Each result is written to the versioned directory
`semantics_sam3_3c879f39826c281e_61id` below its panorama station. The name
pins the SAM 3 revision prefix and the reviewed 61-ID vocabulary. It prevents
the hybrid campaign from mutating or being confused with an older dense-only
`semantics/` result.

## Invocation

From this directory, give exactly one explicit station source:

```bash
python -m semantic_twin.cli.hybrid_batch \
  --walk-manifest data/panoramas/tokyo_hachiko/walk_manifest.json \
  --job-manifest outputs/hybrid_batch/tokyo.json
```

The acquisition manifest's `panorama_dirs` values are resolved relative to the
manifest itself. A manually curated list uses one directory per line:

```bash
python -m semantic_twin.cli.hybrid_batch \
  --stations-file inputs/tokyo_stations.txt \
  --job-manifest outputs/hybrid_batch/tokyo.json
```

Blank lines and text after `#` are ignored. The default catalogue is
`config/semantic_concepts.json`; `--concepts` is available for an explicit
path, but production mode still requires its reviewed semantic digest.

## Resume and validation

After each station the job manifest is replaced atomically. A station is
marked `skipped_complete` only when all of the following agree:

1. `semantics.json` and `panorama_semantics.npz` contain the hybrid metadata
   and raster axes required by the production contract;
2. the dense view cache records the current panorama digest, model revision,
   and inference/view sizes;
3. `hybrid_batch_contract.json` records the exact source panorama hash,
   catalogue hash, model pins, and SHA-256 hashes of every output artifact;
4. every recorded artifact still exists and has its recorded hash.

An existing versioned directory without the sidecar is therefore not treated
as complete. It is rerun once, then becomes resumable. Failed stations are
recorded with their exception and elapsed time while the remaining stations
continue. `--fail-fast` is available for debugging. Rerunning the same command
reuses valid per-view caches through the underlying runner, while a changed
source panorama or contract forces recomputation.

"""Reconstruct every segmented person in a panorama's crops with SAM 3D Body.

The segmenter supplies the instances, so the human detector is never run: each
person-shaped connected component of the label map becomes one box and one mask,
and SAM 3D Body is conditioned on both.  The crop's intrinsics are known exactly
from its field of view, so the bundled FOV estimator is not run either.  Those
two substitutions are what make the reconstruction reproducible: nothing about
the placement depends on a model guessing a camera it was never shown.

Only the camera-frame reconstruction is written here.  Placement into scene ENU
needs the recovered pose and the support mesh, which live with
``build_dynamic_bodies.py``.

Example (on the GPU host)::

    python infer_sam3_body.py --views views --semantics-json semantics.json \\
        --out sam3_body --checkpoint ~/checkpoints/sam-3d-body-vith/model.ckpt
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from semantic_twin.vision.bodies import person_instances, pinhole_intrinsics  # noqa: E402

# Vistas splits a person by what they are doing, and a rider is still a body.
PERSON_WORDS = ("person", "rider", "bicyclist", "motorcyclist")


def person_class_ids(semantics_json: pathlib.Path, words: tuple[str, ...] = PERSON_WORDS) -> set[int]:
    """Resolve the person classes of whatever taxonomy the segmenter used."""
    entity_id2label = json.loads(semantics_json.read_text())["entity_id2label"]
    ids = {int(key) for key, name in entity_id2label.items() if any(word in name.casefold() for word in words)}
    if not ids:
        raise ValueError(f"the segmentation taxonomy has no person classes among {words}")
    return ids


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True, help="directory with hSSS_YYY.jpg and _labels.npy")
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--view-names", nargs="+", help="crop stems, default every hSSS_YYY.jpg in --views")
    parser.add_argument("--checkpoint", type=pathlib.Path, required=True)
    parser.add_argument("--mhr-path", type=pathlib.Path)
    parser.add_argument("--fov-deg", type=float, default=90.0)
    parser.add_argument("--min-pixels", type=int, default=600)
    parser.add_argument("--min-height-px", type=int, default=48)
    parser.add_argument("--max-people-per-view", type=int)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    import torch
    from sam_3d_body import SAM3DBodyEstimator, load_sam_3d_body

    args.out.mkdir(parents=True, exist_ok=True)
    ids = person_class_ids(args.semantics_json)
    names = args.view_names or sorted(path.stem for path in args.views.glob("h*_*.jpg"))
    if not names:
        raise FileNotFoundError(f"no perspective crops in {args.views}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, model_cfg = load_sam_3d_body(str(args.checkpoint), device=device, mhr_path=str(args.mhr_path or ""))
    estimator = SAM3DBodyEstimator(sam_3d_body_model=model, model_cfg=model_cfg)
    faces = np.asarray(estimator.faces, dtype=np.int64)

    manifest: list[dict[str, object]] = []
    total_bodies = 0
    started = time.perf_counter()
    for name in names:
        labels = np.load(args.views / f"{name}_labels.npy")
        confidence_path = args.views / f"{name}_confidence.npy"
        confidence = np.load(confidence_path) if confidence_path.exists() else None
        instances = person_instances(
            labels,
            ids,
            view_id=name,
            confidence=confidence,
            min_pixels=args.min_pixels,
            min_height_px=args.min_height_px,
        )
        if args.max_people_per_view is not None:
            instances = instances[: args.max_people_per_view]
        if not instances:
            manifest.append({"view": name, "instances": 0, "bodies": 0})
            continue

        image = np.asarray(Image.open(args.views / f"{name}.jpg").convert("RGB"), dtype=np.uint8)
        height, width = image.shape[:2]
        intrinsics = pinhole_intrinsics(width, height, args.fov_deg)
        camera = torch.from_numpy(intrinsics[None].astype(np.float32))
        bodies = 0
        for instance in instances:
            box = np.asarray(instance.bbox_xyxy, dtype=np.float32).reshape(1, 4)
            mask = instance.mask.astype(np.uint8).reshape(1, height, width, 1)
            elapsed = time.perf_counter()
            outputs = estimator.process_one_image(image, bboxes=box, masks=mask, cam_int=camera)
            elapsed = time.perf_counter() - elapsed
            for index, output in enumerate(outputs):
                body_id = f"{instance.instance_id}_{index:02d}"
                np.savez_compressed(
                    args.out / f"{body_id}.npz",
                    vertices_camera_raw_m=np.asarray(output["pred_vertices"], dtype=np.float64),
                    faces=faces,
                    keypoints_camera_raw_m=np.asarray(output["pred_keypoints_3d"], dtype=np.float64),
                    keypoints_image_px=np.asarray(output["pred_keypoints_2d"], dtype=np.float64),
                    pred_cam_t_m=np.asarray(output["pred_cam_t"], dtype=np.float64).reshape(3),
                    intrinsics=intrinsics,
                    bbox_xyxy=np.asarray(instance.bbox_xyxy, dtype=np.int64),
                    instance_mask=np.packbits(instance.mask),
                    mask_shape=np.asarray(instance.mask.shape, dtype=np.int64),
                    shape_params=np.asarray(output["shape_params"], dtype=np.float64),
                    scale_params=np.asarray(output["scale_params"], dtype=np.float64),
                    body_pose_params=np.asarray(output["body_pose_params"], dtype=np.float64),
                    global_rot=np.asarray(output["global_rot"], dtype=np.float64),
                    metadata_json=np.array(
                        json.dumps(
                            {
                                "body_id": body_id,
                                "view_id": name,
                                "instance_id": instance.instance_id,
                                "segmenter_confidence": instance.mean_confidence,
                                "instance_pixels": instance.pixel_count,
                                "model": "facebook/sam-3d-body-vith",
                                "model_frame": "x-right, y-down, z-forward",
                                "intrinsics_source": f"known {args.fov_deg:g} degree pinhole crop",
                                "instances_from": "segmentation connected components, no human detector",
                                "seconds": elapsed,
                            },
                            sort_keys=True,
                        )
                    ),
                )
                bodies += 1
        total_bodies += bodies
        manifest.append({"view": name, "instances": len(instances), "bodies": bodies})
        print(f"[sam3-body] {name}: {len(instances)} person instances, {bodies} bodies", flush=True)

    seconds = time.perf_counter() - started
    (args.out / "manifest.json").write_text(
        json.dumps(
            {
                "model": "facebook/sam-3d-body-vith",
                "checkpoint": str(args.checkpoint),
                "views_directory": str(args.views),
                "person_class_ids": sorted(ids),
                "min_pixels": args.min_pixels,
                "min_height_px": args.min_height_px,
                "fov_deg": args.fov_deg,
                "bodies": total_bodies,
                "seconds": seconds,
                "views": manifest,
            },
            indent=2,
        )
    )
    print(f"[sam3-body] {total_bodies} bodies from {len(names)} crops in {seconds:.1f} s", flush=True)


if __name__ == "__main__":
    main()

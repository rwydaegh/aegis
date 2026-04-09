"""Modal App definition, container images, and shared resources."""

import modal

app = modal.App("aegis-rt", include_source=False)

scene_volume = modal.Volume.from_name("aegis-scenes", create_if_missing=True)

differt_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "jax[cuda12]>=0.4.20",
        "differt>=0.7.0",
        "equinox",
        "numpy",
        "scipy",
    )
    .add_local_dir("src/aegis", remote_path="/root/aegis")
)

sionna_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("sionna-rt>=2.0,<3.0", "numpy", "scipy")
    .add_local_dir("src/aegis", remote_path="/root/aegis")
)

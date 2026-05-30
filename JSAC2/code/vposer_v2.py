"""Minimal VPoser v2.0 loader.

The installed `human_body_prior` package only ships the v1 VPoser class
(see `human_body_prior.train.vposer_smpl.VPoser`), but the V02_05 release
uses a different architecture (encoder_net / decoder_net). We re-implement
just the decoder (which is what we need for differentiable z -> pose
rollouts) and load the published v2.0 checkpoint into it.

Architecture inferred from the .ckpt state-dict shapes:

  encoder_net (not used here, kept for reference):
    [1] BatchNorm1d(63)
    [2] Linear(63, 512)
    [4] BatchNorm1d(512)
    [6] Linear(512, 512)
    [7] Linear(512, 512)
    [8] mu: Linear(512, 32);  logvar: Linear(512, 32)

  decoder_net:
    [0] Linear(32, 512)
    [3] Linear(512, 512)
    [5] Linear(512, 126)   # 21 joints * 6 (continuous rotation repr)

Output convention: 21 SMPL body joints (joints 1..21, excluding the
global_orient at joint 0). Each is a 6-D continuous rotation
representation (Zhou et al. 2019), converted to 3x3 rotation matrices and
then to axis-angle.
"""

from __future__ import annotations

from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F


VPOSER_CKPT = Path(
    "/home/user/aegis/data/vposer/V02_05/snapshots/V02_05_epoch=13_val_loss=0.03.ckpt"
)
NUM_JOINTS_BODY = 21
LATENT_D = 32


def _continuous_rot_to_matrix(d6: torch.Tensor) -> torch.Tensor:
    """Zhou et al. 2019 continuous rotation -> 3x3 matrix, VPoser layout.

    Input: (..., 6) where the 6 entries are reshape-(3,2)-interleaved:
    a1_components at indices 0, 2, 4 and a2_components at indices 1, 3, 5
    (this matches `human_body_prior.tools.rotation_tools.ContinousRotReprDecoder`
    which does `view(-1, 3, 2)`).  Output: (..., 3, 3).
    """
    rs = d6.view(*d6.shape[:-1], 3, 2)
    a1 = rs[..., :, 0]
    a2 = rs[..., :, 1]
    b1 = F.normalize(a1, dim=-1)
    b2 = a2 - (b1 * a2).sum(-1, keepdim=True) * b1
    b2 = F.normalize(b2, dim=-1)
    b3 = torch.linalg.cross(b1, b2, dim=-1)
    return torch.stack([b1, b2, b3], dim=-1)  # columns = b1, b2, b3


def _rotmat_to_axisangle(R: torch.Tensor) -> torch.Tensor:
    """3x3 rotation matrix -> axis-angle (...) -> (..., 3)."""
    cos = ((R[..., 0, 0] + R[..., 1, 1] + R[..., 2, 2]) - 1.0) * 0.5
    cos = cos.clamp(-1.0 + 1e-7, 1.0 - 1e-7)
    angle = torch.arccos(cos)
    sin = torch.sin(angle).clamp(min=1e-7)
    axis = torch.stack(
        [
            R[..., 2, 1] - R[..., 1, 2],
            R[..., 0, 2] - R[..., 2, 0],
            R[..., 1, 0] - R[..., 0, 1],
        ],
        dim=-1,
    ) / (2.0 * sin.unsqueeze(-1))
    return axis * angle.unsqueeze(-1)


def _axisangle_to_rotmat(aa: torch.Tensor) -> torch.Tensor:
    """Axis-angle (...,3) -> rotation matrix (...,3,3) via Rodrigues."""
    angle = aa.norm(dim=-1, keepdim=True).clamp(min=1e-12)
    axis = aa / angle
    K = torch.zeros(*aa.shape[:-1], 3, 3, device=aa.device, dtype=aa.dtype)
    K[..., 0, 1] = -axis[..., 2]
    K[..., 0, 2] = axis[..., 1]
    K[..., 1, 0] = axis[..., 2]
    K[..., 1, 2] = -axis[..., 0]
    K[..., 2, 0] = -axis[..., 1]
    K[..., 2, 1] = axis[..., 0]
    eye = torch.eye(3, device=aa.device, dtype=aa.dtype).expand_as(K)
    sin = torch.sin(angle).unsqueeze(-1)
    cos = torch.cos(angle).unsqueeze(-1)
    return eye + sin * K + (1.0 - cos) * (K @ K)


class VPoser(nn.Module):
    """Encoder + decoder re-implementation of VPoser v2.0.

    Loads the published v2.0 checkpoint and exposes:
      - encode(theta_aa): (..., 21, 3) axis-angle -> mu (..., 32)
      - decode(z): (..., 32) -> body pose axis-angle (..., 21, 3)

    Use mean-only encoding (no rsample) for deterministic z0 inversion
    of an AMASS frame.
    """

    def __init__(self):
        super().__init__()
        # Encoder: BatchNorm(63) + Linear(63,512) + BN(512) + Linear(512,512) +
        # Linear(512,512) + Linear(512,32)x2 (mu, logvar)
        self.enc_bn1 = nn.BatchNorm1d(NUM_JOINTS_BODY * 3)
        self.enc_fc1 = nn.Linear(NUM_JOINTS_BODY * 3, 512)
        self.enc_bn2 = nn.BatchNorm1d(512)
        self.enc_fc2 = nn.Linear(512, 512)
        self.enc_fc3 = nn.Linear(512, 512)
        self.enc_mu = nn.Linear(512, LATENT_D)
        self.enc_logvar = nn.Linear(512, LATENT_D)

        # Decoder: Linear(32,512) + Linear(512,512) + Linear(512,126)
        self.dec_fc1 = nn.Linear(LATENT_D, 512)
        self.dec_fc2 = nn.Linear(512, 512)
        self.dec_out = nn.Linear(512, NUM_JOINTS_BODY * 6)

    @classmethod
    def from_checkpoint(cls, ckpt_path: Path | str = VPOSER_CKPT) -> "VPoser":
        m = cls()
        sd = torch.load(ckpt_path, map_location="cpu", weights_only=False)["state_dict"]

        # Encoder
        m.enc_bn1.weight.data.copy_(sd["vp_model.encoder_net.1.weight"])
        m.enc_bn1.bias.data.copy_(sd["vp_model.encoder_net.1.bias"])
        m.enc_bn1.running_mean.data.copy_(sd["vp_model.encoder_net.1.running_mean"])
        m.enc_bn1.running_var.data.copy_(sd["vp_model.encoder_net.1.running_var"])
        m.enc_fc1.weight.data.copy_(sd["vp_model.encoder_net.2.weight"])
        m.enc_fc1.bias.data.copy_(sd["vp_model.encoder_net.2.bias"])
        m.enc_bn2.weight.data.copy_(sd["vp_model.encoder_net.4.weight"])
        m.enc_bn2.bias.data.copy_(sd["vp_model.encoder_net.4.bias"])
        m.enc_bn2.running_mean.data.copy_(sd["vp_model.encoder_net.4.running_mean"])
        m.enc_bn2.running_var.data.copy_(sd["vp_model.encoder_net.4.running_var"])
        m.enc_fc2.weight.data.copy_(sd["vp_model.encoder_net.6.weight"])
        m.enc_fc2.bias.data.copy_(sd["vp_model.encoder_net.6.bias"])
        m.enc_fc3.weight.data.copy_(sd["vp_model.encoder_net.7.weight"])
        m.enc_fc3.bias.data.copy_(sd["vp_model.encoder_net.7.bias"])
        m.enc_mu.weight.data.copy_(sd["vp_model.encoder_net.8.mu.weight"])
        m.enc_mu.bias.data.copy_(sd["vp_model.encoder_net.8.mu.bias"])
        m.enc_logvar.weight.data.copy_(sd["vp_model.encoder_net.8.logvar.weight"])
        m.enc_logvar.bias.data.copy_(sd["vp_model.encoder_net.8.logvar.bias"])

        # Decoder
        m.dec_fc1.weight.data.copy_(sd["vp_model.decoder_net.0.weight"])
        m.dec_fc1.bias.data.copy_(sd["vp_model.decoder_net.0.bias"])
        m.dec_fc2.weight.data.copy_(sd["vp_model.decoder_net.3.weight"])
        m.dec_fc2.bias.data.copy_(sd["vp_model.decoder_net.3.bias"])
        m.dec_out.weight.data.copy_(sd["vp_model.decoder_net.5.weight"])
        m.dec_out.bias.data.copy_(sd["vp_model.decoder_net.5.bias"])

        m.eval()
        return m

    def encode(self, theta_aa: torch.Tensor) -> torch.Tensor:
        """Encode body pose (axis-angle, ..., 21, 3) -> mean latent (..., 32).

        Returns the posterior MEAN (no sampling) for deterministic
        AMASS-frame -> z0 inversion.
        """
        flat = theta_aa.reshape(*theta_aa.shape[:-2], NUM_JOINTS_BODY * 3)
        # BatchNorm needs (N, C) shape; squeeze and expand if needed.
        in_shape = flat.shape
        x = flat.reshape(-1, NUM_JOINTS_BODY * 3)
        x = self.enc_bn1(x)
        x = F.leaky_relu(self.enc_fc1(x), negative_slope=0.2)
        x = self.enc_bn2(x)
        x = F.leaky_relu(self.enc_fc2(x), negative_slope=0.2)
        x = F.leaky_relu(self.enc_fc3(x), negative_slope=0.2)
        mu = self.enc_mu(x)
        return mu.reshape(*in_shape[:-1], LATENT_D)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """z: (..., 32) -> body pose axis-angle (..., 21, 3)."""
        x = F.leaky_relu(self.dec_fc1(z), negative_slope=0.2)
        x = F.leaky_relu(self.dec_fc2(x), negative_slope=0.2)
        d6 = self.dec_out(x).reshape(*z.shape[:-1], NUM_JOINTS_BODY, 6)
        R = _continuous_rot_to_matrix(d6)
        aa = _rotmat_to_axisangle(R)
        return aa


# Back-compat alias.
VPoserDecoder = VPoser


# Sanity check + round-trip test.
if __name__ == "__main__":
    import numpy as np
    vp = VPoser.from_checkpoint()

    # Round-trip: encode an AMASS frame, decode, compare.
    import sys
    sys.path.insert(0, "/home/user/aegis/src")
    from aegis.geometry.pose_stream import PoseStream
    walks = sorted(Path("/home/user/aegis/data/poses/plaza_run_walks").rglob("*.npz"))
    ps = PoseStream.load(walks[0])
    poses = ps.poses[:, :66].reshape(-1, 22, 3)
    body_aa = poses[50, 1:]  # (21, 3)

    body_t = torch.tensor(body_aa, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        z0 = vp.encode(body_t)
        body_recon = vp.decode(z0)
    err = (body_recon - body_t).norm(dim=-1).mean()
    print(f"AMASS frame round-trip: |z0|={z0.norm():.3f}, "
          f"per-joint reconstruction err = {err:.4f} rad ({float(err)*180/3.14159:.2f} deg)")

    # Sanity: random z gives plausible joint magnitudes
    z = torch.randn(5, LATENT_D)
    with torch.no_grad():
        aa = vp.decode(z)
    print(f"random z (5 samples) joint magnitudes (deg) per sample:")
    for i in range(5):
        mags = aa[i].norm(dim=-1).numpy() * 180 / 3.14159
        print(f"  sample {i}: range [{mags.min():.1f}, {mags.max():.1f}], mean {mags.mean():.1f}")

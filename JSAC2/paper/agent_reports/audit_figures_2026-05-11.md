# Figure-claim audit (2026-05-11)

Visual sanity check of the 12 figures of `JSAC2/paper/jsac2_v3.tex` and `jsac2_v3_supp.tex` against caption + surrounding prose. PNG copies at the paths cited under each item were inspected. Numerical claims were cross-referenced against the underlying NPZ archives in `JSAC2/code/outputs/` where helpful.

## Verdict summary

| # | Figure | Verdict |
|---|---|---|
| 1 | Hero (`fig_hero_munich.png`) | ✗ contradicts |
| 2 | Per-scene SINR (`fig_munich_perscene.png`) | ✓ supports |
| 3 | Reachability (`fig_munich_reachability.png`) | ✓ supports |
| 4 | Per-joint sensitivity (`fig_per_joint_sensitivity.png`) | ⚠ minor |
| 5 | Comfort Pareto (`fig_comfort_pareto.png`) | ✗ contradicts |
| 6 | Baselines (`fig_baselines.png`) | ⚠ minor |
| 7 | SAR receipt (`fig_sab_receipt.png`) | ⚠ minor |
| 8 | IMU sensitivity (`imu_gamma_overlay.png`) | ⚠ minor |
| 9 | Peak APD (`peak_apd_sensitivity.png`) | ⚠ minor |
| 10 | DTN architecture | ✓ supports |
| 11 | Kirchhoff schematic | ✓ supports |
| 12 | Munich Rx grid | ✓ supports |

## Substantive findings

### 1. Hero figure — wrong best-pose SINR label (✗)
`fig_hero_munich.png` panel (b) is titled **"best-found pose, SINR = 17.8 dB"**. Caption (line 1037) and prose (line 1018) both say the best of N=100 random latents is **19.5 dB**. Panel (c) annotates the gap as "Δ = 8.6 dB" which assumes 10.9 → 19.5. Ground-truth NPZ confirms `sinr_existence_max[17] = 19.51 dB`. The 17.8 dB label in (b) is wrong — it disagrees both with the caption and with the (c) plot in the same figure.

Action: regenerate (b) title using `sinr_existence_max[17]` rather than whatever was used (likely the SINR of a different specific latent draw, or the gradient-loop terminal value).

### 5. Comfort Pareto — x-axis is "comfort cost", not latent radius (✗)
Caption and prose (lines 1136-1147, 1152-1156) describe the x-axis as the latent-radius `‖z − z₀‖` and quote thresholds of "0.5-radius ≈ 6 dB", "unit-radius ≈ 7.5 dB", "saturates above 1.2". The figure's x-axis is labelled **"Comfort cost C(Δθ) [comfort units]"** and ranges 0 to 4. The Pareto frontier reaches +6 dB at C ≈ 0.85, +7.5 dB at C ≈ 1.5, and saturates near C ≈ 2-3.

If `C(Δθ)` is the joint-space comfort cost rather than the latent-norm, the x-axis legend in the prose is wrong (or the figure's x-axis is the wrong quantity). The numbers cited (6, 7.5 dB, saturation) are visually present in the curve, just at different x-locations than the prose suggests. A reader cannot reconcile the two without trusting one over the other. Either:
- relabel the x-axis to `‖z − z₀‖` and re-plot in latent radius, or
- update the prose to cite "C(Δθ) ≈ 0.85", "C ≈ 1.5", "saturates near C ≈ 2-3" with units of `comfort units`.

The title also reads "binding regime, 55 dB, 10 m BS" — useful info that should appear in the caption (caption only says "one representative NLOS-class scene").

### 4. Per-joint sensitivity — top-5 share is closer to ~60% than ">80%" (⚠)
Caption (line 1127) and prose (line 1113) say the top 5 joints "carry the bulk of the gradient mass" / "over 80% of the gradient mass". Eyeballing the bar heights: pelvis ≈ 7800, L hip ≈ 6200, R hip ≈ 4900, spine1 ≈ 4900, spine2 ≈ 3900 → top-5 sum ≈ 27,700. Sum of all 22 visible bars looks ≈ 45,000-48,000, so top-5 share ≈ 58-62%, not >80%. The visible spine3, L knee, R collar, R shoulder, R knee bars are not negligible. The qualitative claim "torso > periphery" is supported, but the quantitative ">80%" likely overstates it. Suggest dropping the percentage or recomputing from `per_joint_sensitivity.npz`.

The visible top-5 list (pelvis, L hip, R hip, spine1, spine2) does match the caption.

### 6. Baselines — band-label inconsistency between caption/prose and x-axis labels (⚠)
NPZ-derived means match the prose exactly (LOS-att ZF -18.1%, binding RIHB +7.1% / T-pose +5.8%, NLOS both +13.8%). However the figure x-axis labels the three bands as **(25-35 dB) / (50-60 dB) / (70-85 dB)** while the prose at lines 1170, 1173 names them "55 dB scalar loss" and "80 dB scalar loss". The prompt's "35/55/80 dB" matches the prose's centroids but not the figure's range labels. Not contradictory, just inconsistent presentation. Nothing actionable if the centroid/range distinction is acceptable.

### 7. SAR receipt — `P_abs` instantaneous trace not visible in panel (b) (⚠)
The PNG renders very small at column width, but in panel (b) the only line that reads is the green dashed cumulative-dose curve. The legend lists "P_abs [mW]" as a separate blue trace, but no blue line is visible — it appears flat near zero relative to the cumulative-dose axis scale. Caption claims both are shown with a dual y-axis. Suggest replotting with the instantaneous trace on a log scale or with a clearer color/lineweight so it is actually visible. Panels (a) (heatmap with cyan star) and (c) (ECDF with orange ICNIRP line) look correct.

### 8. IMU sensitivity — y-axis label cropped, "90th percentile" claim not directly verifiable (⚠)
The figure's y-axis label is partially cut off ("loop SINR loss vs noiseless o..."). Render export is bleeding outside the bbox. The mean curves (~0.2-0.4 dB) are consistent with the "<0.5 dB mean loss" claim. The ±1σ shading reaches ~+1.5 dB upper edge, broadly consistent with a "90th percentile <1.8 dB" claim, but the figure shades ±1σ, not 5/95 percentiles, so the prose claim cannot be read off the figure directly. Either crop the bbox to fix the y-axis label and/or add a ±1.65σ band if the 90th-percentile sentence stays.

### 9. Peak APD sensitivity — right panel y-axis is dB but prose reports % (⚠)
Right-panel y-axis says **"whole-body P_abs ratio (dB, perturbed/oracle)"**. The SI prose (lines 442-457) reports the same quantity in **percentage offset** ("-0.5% at 4°", "-3.2% at 16°"). Translating: -0.5% ≈ -0.022 dB and -3.2% ≈ -0.14 dB. The figure plots NLOS at σ=16° at roughly -0.18 dB (≈ -4%) and LOS at σ=16° at roughly -0.10 dB (≈ -2.3%). The averaged-across-LOS+NLOS value is therefore close to -0.14 dB ≈ -3.2% ✓, but a reader has to do the dB↔% conversion themselves. Suggest plotting in % directly, or duplicate-label the y-axis with both units.

Left-panel numbers match: σ=2° peak-APD location error ≈ 38 cm (LOS), 67 cm (NLOS) → mean ≈ 52 cm ✓; σ=16° → 54/62 cm → mean ≈ 58 cm ✓.

## ✓ Figures that pass without notes

- **2. Per-scene SINR.** 18 bars (9 blue LOS, 9 orange NLOS), scene 17 baseline ≈ 11 dB, best ≈ 19 dB, gap visually ≈ 8 dB — all match `munich_existence.npz`.
- **3. Reachability.** Two panels (LOS, NLOS), 5 K values {2,5,10,15,20}, both reach ~89% (= 8/9) at K=20.
- **10. DTN architecture.** Network / On-device twin / User boxes, J path dictionary, SMPL-X mesh, h_b Kirchhoff, K_99 SVD γ fit, ∇R, S_ab, IMU return, two semantic outputs at the bottom.
- **11. Kirchhoff schematic.** BS array + path n with k_n, body triangle with n_t, η-hat to phone at r_p, K_n integrand box.
- **12. Munich Rx grid.** BS marker at center, yellow broadside arrow, 9 green LOS + 9 red NLOS, x and y ranges roughly match the claim.

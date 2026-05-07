# epsilon-effective rank of Q on Thelonious, plaza scenario

- Bodies: 20, thelonious, 20-80 m range, azimuth +/- 60 deg
- Freq: 26 GHz, 8x8 UPA (half-wavelength), 10 deg down-tilt
- Tissue: Skin 26 GHz (eps_r=17.71, sigma=24.41 S/m)

Definition: epsilon-effective rank = #{k : lambda_k / lambda_1 >= epsilon}.

### Model A: plaza specular (LOS + ground + 2 facades)

| epsilon | p10 | median | p90 | min | max |
|---|---|---|---|---|---|
| 1e-01 | 2 | 3 | 3 | 2 | 3 |
| 1e-02 | 3 | 4 | 4 | 3 | 4 |
| 1e-03 | 4 | 4 | 4 | 4 | 4 |

### Model B: 3GPP_38.901_UMa_LOS stochastic (12 clusters x 5 subpaths = 60 paths)

| epsilon | p10 | median | p90 | min | max |
|---|---|---|---|---|---|
| 1e-01 | 1 | 1 | 1 | 1 | 1 |
| 1e-02 | 2 | 3 | 3 | 2 | 3 |
| 1e-03 | 3 | 3 | 4 | 3 | 4 |

# epsilon-effective rank of Q on Thelonious, plaza scenario

- Bodies: 20, thelonious, 20-80 m range, azimuth +/- 60 deg
- Freq: 26 GHz, 8x8 UPA, half-wavelength spacing, 10 deg down-tilt
- Tissue: Skin 26 GHz (eps_r=17.71, sigma=24.41 S/m)
- Paths per body: LOS + ground bounce + 2 facade specular reflections

Definition: epsilon-effective rank = #{k : lambda_k / lambda_1 >= epsilon}.

| epsilon | p10 | median | p90 | min | max |
|---|---|---|---|---|---|
| 1e-01 | 2 | 3 | 3 | 2 | 3 |
| 1e-02 | 3 | 4 | 4 | 3 | 4 |
| 1e-03 | 4 | 4 | 4 | 4 | 4 |

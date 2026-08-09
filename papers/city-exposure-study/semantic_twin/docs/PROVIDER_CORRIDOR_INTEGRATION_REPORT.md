# Provider corridor integration report

This is a read-only evaluation of the opt-in `provider_corridor_v1` contract.
It does not change `config/city_cohort_manifest.json`, any comparable campaign
configuration, or the established `registered_span_street_v1` route.

The same read-only check is available without editing that manifest:

```bash
python -m semantic_twin.cli.cohort --route-contract provider_corridor_v1 --json
```

The evaluation used the current admitted reports and provider link inputs in
`/home/user/aegis/papers/city-exposure-study/semantic_twin` on 2026-08-07. Tokyo
was evaluated after its 10-camera atlas completed that day. The
contract considered every admitted-camera pair connected in one provider graph
component. It registered the exact shortest provider node path to both camera
endpoints, then calculated the maximum nearest-camera distance continuously at
every segment endpoint and exact Voronoi breakpoint. A camera in a disconnected
provider component cannot support a candidate path. Candidates exceeding 20 m
were refused. Selection maximized Euclidean endpoint separation, then preferred
the shorter registered provider path, then canonical station IDs.

## Expected selections

| Site | Endpoint stations | Provider node path | Span (m) | Path (m) | Continuous max gap (m) | Accepted / connected / all pairs |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Korenmarkt | `walk_05_1084407470281938` to `walk_08_1019442960256615` | `1084407470281938`, `582445657694750`, `661483666648209`, `706535575184668`, `1419513849204492`, `1019442960256615` | 49.005 | 49.036 | 10.107 | 11 / 11 / 36 |
| Prague | `pano_02_MuUayaL3yQ2qYd_O` to `pano_07_uUsx9yov1IPH4Nmo` | `MuUayaL3yQ2qYd_OxE4CwQ`, `9DEX760IKTts_gFkf-WjJQ`, `Q9qwZ4uWs2pIn2P3Jt2UIg`, `BBrYQpi0-rZLNQXV0WSd7A`, `7ZtNkWqTMab-DAWjFN8CeA`, `RDcKK-eBrBBc8UAVIsX3Vw`, `YaAB9Pi4inYKHBk9GFIi2g`, `p9sxREl5fWTL7t1gcueTyw`, `Ek3oSeXuB1qgRAD1DWlQnw`, `bLzsBdJ7LJdcRxNJfi9Abg`, `GQpgBqYt7DPZIgcQOKTORw`, `QvY2oEIej_MYGiaPX9N_Iw`, `DTT5fxX1RNIE5vwqHmdFtA`, `grcodJ1AIu6yY8iERrIWxg`, `fn0BJ5Nmn4nSLI8XOOz_2Q`, `eJJ54gToyobC2u3b_xYSuA`, `RWQUIL4uW1c9GB1iE196Ig`, `5asRnZt7-KEVZe3vaDW9eQ`, `kkl0MWIz9e1lwe5WlAeQ6g`, `bBYgF75dmDNOzvkaR9r0Dg`, `Qc6iezvvG2AsFauNP3yZDA`, `HfuT3UIDWqwI_Gnhy-WJlw`, `fnfRF5qtfQoaabHCSKBcIQ`, `QJAhsSqFNrgWKquFXcMglQ`, `NIRX5s8gVSdpEw6tnsWaRQ`, `yJGtGPbSZYzilQf7K_LKRA`, `o_AoslaiT1s43SRqULJSOA`, `QnjwTrAD0DDX-KHhN6hbYw`, `atqtqDIF9BzImNuc2OmPyw`, `1tXzd1R48Gi5MUURHfh7tg`, `sWxTPGt5hGiCGCWkwocEvg`, `H0BGZLqmiJ42CSLX-AHNgA`, `uUsx9yov1IPH4NmoOTYj9A` | 103.781 | 120.707 | 16.230 | 38 / 66 / 66 |
| Madrid | `pano_03_WrlL3iu5qfh8xeeE` to `pano_12_wbhVfxvyavN8SkDr` | `WrlL3iu5qfh8xeeE80aHOA`, `9_zKoIXsQQ80R2lZHvTAQQ`, `gvvhHspDS14f6e0lRTZ6Ag`, `EExsn_pAas6uzzHgaPjOJQ`, `AjSuzc9WfpYQCN2_TBEUgw`, `wbhVfxvyavN8SkDrEWEU4A` | 62.437 | 75.894 | 15.448 | 24 / 36 / 36 |
| Mexico City | `pano_04__wXj2KviEnfsV7YV` to `pano_09_3dinepTkEFNpmpIb` | `_wXj2KviEnfsV7YVjsTBTg`, `jb8VQjMzzUqIrMeN_NV-Cg`, `Z4RPMMRGBxqT2CtclYjfyA`, `9_UwtAKK7mPl8-E-eAYNaA`, `YOrXjCmmx2kO1-Dk7CaCYw`, `4NcKvSxbDnJgMgO4ORI4Bg`, `kT-sJBOixC0rcAkkrZ1p-w`, `UuEvq7lRV9E9I2eZ9V-Aig`, `ZncCJRMwz22UCr8EahagYA`, `6bCRfUhg38vwee9LM2IHJw`, `o6FlhxRElkFeg5qC5_3ZhA`, `mUu7vYKLcc7_miwZY9IOHA`, `1XeLFDRrdEu7e9sOKBmtxA`, `1_f_eXcObxSHHg4NX3IWhw`, `9W6vTjpUZDqZbygxs5qoTg`, `XhXNk6p2_LQOmtW9Ombdeg`, `giZXKKC2zLTI451DwQDywA`, `xx_YC3U8fOjIy2jFESwKwg`, `VWbDsE75LmYC4wnhJpjtzQ`, `i-7buoXf6eKSkXi3Xw0g1A`, `oVrocI6iIuG0yfocvILEkw`, `G_dMQ1zMLcTq3Wfburdlgw`, `eMyt8z6_iXjQkTwT8y1-ew`, `veBp_e0JGFegX0B8_Os91g`, `lf6iE5N8gPl0tfuk9MgGhw`, `jcRJ24e8KnIggkmdigZLXg`, `BWa5OUEl3SCHzbvHKmY5Vw`, `3dinepTkEFNpmpIbnQERvQ` | 52.395 | 59.367 | 15.140 | 6 / 10 / 10 |
| Tokyo | `pano_05_XVJVifnGo2nWMynw` to `pano_09_eribq7xEToHqtyTb` | `XVJVifnGo2nWMynwQxUtJg`, `RaNoutOgDdz7nABPid3adw`, `GR5jUP1WQSbKFJwSc2hvIw`, `sHYDaW3IGG9Xef11LALRFQ`, `TTQ4BiEM-Htj3xBbgTJ5dA`, `AXABum0p3VBvLgpsoC-_6w`, `NCILawcpTxk3OjbQf6nPSQ`, `6BJ23SY0VBx1sbvSrXbksw`, `eribq7xEToHqtyTbDC4H6w` | 72.160 | 88.313 | 12.334 | 45 / 45 / 45 |

Each runtime corridor provenance record additionally seals the admitted report
bytes, every provider graph input file, a canonical graph digest, endpoint
station IDs, exact provider node path, registered ENU polyline, continuous gap,
span, path length, full pair-selection audit, and a final selection hash.

The selection hashes for this read-only snapshot are:

- Korenmarkt: `6013aa940b04fb9d934034f7337b2b983a70a0885baf525b7c88c39b81be27fa`
- Prague: `244b7b314799fcc523d7b0397836956d8aea8ce172a3ede37c9361727211d6cb`
- Madrid: `c7f0548c9bc79be0e2eeb2cb3c77ccdfd254b1b611fe80d9953a0d5ce2d21def`
- Mexico City: `4dfa7f3390f815c1adfc3d60b07e170111558bc11c4ac8335681b66428328d88`
- Tokyo: `4b636d1a14f9b3be1a24ee6440af0476f0d07b14eca0cd604e7a2654c01f3e85`

# v1 to v2: why the section was rebuilt

v1 was built on a claim that is false. Two independent checks (a direct read of the ICNIRP 2020
PDF, and the Fable red-team in `redteam_fable.md`) refuted it. This file records what broke and
what replaced it, so the mistake is not reintroduced.

## The claim that was wrong

v1 argued: ICNIRP 2020 says up to 50% of incident power is reflected away from the body, industry
still certifies against the incident-field reference level, therefore there is roughly a factor of
two of unclaimed compliance margin that AEGIS can harvest by computing the basic restriction
directly.

**ICNIRP already granted that margin, in the reference level, with an equation.** ICNIRP 2020
eq. (29), in the derivation of the local reference levels above 6 GHz:

```
Sinc = Sab · T^-1        where   T = 1 - |Gamma|^2      (eq. 30)
```

The reference level *is* the basic restriction divided by the transmittance. The reflected fraction
is already divided out. The tables confirm it. General public, local exposure:

| f | RL (Sinc = 55·f^-0.177) | BR (Sab) | RL/BR | Transmittance ICNIRP assumed |
|---|---|---|---|---|
| 6 GHz | 40.1 W/m² | 20 W/m² | **2.00** | 0.50 |
| 10 GHz | 36.6 | 20 | 1.83 | 0.55 |
| 26 GHz | 30.9 | 20 | 1.54 | 0.65 |
| 60 GHz | 26.6 | 20 | 1.33 | 0.75 |
| 300 GHz | 20.0 | 20 | 1.00 | 1.00 |

The "factor of two" v1 proposed to reclaim is, at 6 GHz, exactly the ratio already printed in
ICNIRP's Table 6. The implied transmittance curve is ICNIRP's own conservative rounding of Sasaki
et al. (2017), 0.4 rising to 0.8. The occupational tables give an identical ratio.

Also: the "up to 50% is reflected away" sentence is **not in the guidelines**. It is from ICNIRP's
*Differences between the 2020 and previous guidelines* web page, where its job is to explain why the
dosimetric quantity changed. v1 quoted a regulator against itself.

Wout (Belgian rep to CENELEC TC106X and IEC TC106), Grangeat (Nokia, IEC TC106 MT3) and Parazzini
could each have falsified this in under a minute. All three are attached to the application.

## Three rescue attempts that also fail

- **Obliquity and curvature.** Hoped a real curved body absorbs materially less than ICNIRP's planar
  normal-incidence model. Diao, Rashed and Hirata ([arXiv:2007.02604](https://arxiv.org/pdf/2007.02604))
  computed it: above 20 GHz with curvature radii over 30 mm, differences in heating factor between
  APD averaging schemes and between TE and TM are below ~6%, and curvature radius effects are "rather
  small". No factor of two hides in the geometry. And at the hot spot, which is by construction the
  patch facing the antenna, incidence is near normal, which is ICNIRP's own assumption.
- **The reactive near field.** ICNIRP does forbid reference-level use there, so basic restrictions
  must be assessed. But **AEGIS cannot compute the reactive near field** (lambda/2pi = 1.7 mm at
  28 GHz). Citing this as the demand argument points at the one regime the method does not serve.
- **Wrong restriction.** Above 6 GHz at a base-station compliance boundary the binding basic
  restriction is **whole-body SAR (0.08 W/kg)**, not local Sab. The whole-body RL (10 W/m²) is 3x
  below the local RL (~31 W/m² at 26 GHz), so it binds first. v1's Fresnel argument aimed at a
  restriction that is not setting the boundary.

## What v2 is built on instead

1. **Devices, not base stations.** Above 6 GHz, on devices, absorbed power density *is* the
   certification quantity. It needs no rhetorical assist. Ericsson's own 63195 contributor said "go
   there instead of base stations". `LATEST_GOOD/honest_analysis.md` reached the same conclusion
   independently. Nokia's negative on the base-station route is now reported as a documented negative
   that moved the beachhead, which is stronger evidence of real discovery than any positive quote.
2. **The procedure does not exist yet.** IEC/IEEE 63195 parts 3 and 4 (absorbed power density) are
   still drafts. Part 4 currently specifies FDTD and FEM. The rules are open, in a working group,
   inside the project window.
3. **ICNIRP invites it, in writing:** "information from a technical standards body, designed to
   specify external exposures for each EMF source type to more adequately match the basic
   restrictions, should be utilized to improve reference level assessment procedures." A far better
   quote than the 50% one, and it is on our side rather than against us.
4. **Distribution.** Ericsson described the deal shape unprompted: "a drop-in replacement, for EMF
   Visual or IXUS." An OEM licence into the incumbent compliance tool reaches year-5 revenue through
   3 deals instead of 24 seats. v1 truncated this quote at exactly the point where it stopped being
   flattering and started being useful.
5. **Concede the niche.** v1 demolished the ZMT $2.3M figure and put nothing in its place, which a
   business developer reads as a dodge. And it is falsified by our own annex: Parazzini's letter says
   ZMT gives her group Sim4Life free, so the flagship alpha customer *is* a ZMT customer. v2 sizes the
   market bottom-up, concedes a few-million ceiling, and points out that accepted Unisens projected
   €780k at year 5 and cleared this jury.
6. **The compliance-boundary story survives only as a measurement.** The whole-body RL above 6 GHz was
   carried over unchanged from ICNIRP 1998, where it was set by whole-body resonance near 70 MHz, and
   has never been re-derived for the superficial-absorption regime. There may be genuine margin there.
   Estimated ~1.5x in power, ~1.2x in distance. **This estimate is NOT VERIFIED** and no published
   value was found. It is therefore a Phase 1 deliverable with a kill date, not a claim.

## Still open

- The ~1.5x whole-body margin estimate needs an actual computation before it is quoted anywhere.
- Lojic Kapetanovic and Poljak, SpliTech 2021 (DOI 10.23919/SpliTech52315.2021.9566429) is still
  unread. It applied automatic differentiation to mmWave APD. Any novelty claim about
  differentiability must be checked against it first.
- The turnover table in v1 was a near-clone of the accepted Unisens table (year 3 identical at 420k).
  v2 rebuilds it bottom-up from unit prices and customer counts so the arithmetic is visible.

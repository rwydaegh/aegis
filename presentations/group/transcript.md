# Geometric Dosimetry -- Speaker Transcript

Robin Wydaeghe, Ghent University & imec
Group talk, 15 minutes (+ 5 min Q&A)


## [Slide 1: Title] (0:00 -- 0:16)

Geometric dosimetry. Closed-form absorption laws from 100 MHz to 100 GHz.

[pause, 5s settle]


## [Slide 2: Back-of-envelope calculation] (0:16 -- 1:07)

[CLICK 1]
Before we get into the physics, let me say why this matters. EMF compliance assessment for 5G deployments requires computing absorbed power density on the body. The standard approach is FDTD. Quick back of the envelope. The body is about two metres. The skin depth at millimetre-wave frequencies is about 0.2 millimetres. That ratio is ten to the fourth per dimension. In 3D, your FDTD mesh has ten to the twelfth cells. One plane wave, one phantom, one frequency: weeks.

[pause]

[CLICK 2]
Our formulation works on the body surface. The surface area is about 1.7 square metres. At millimetre resolution, that is roughly ten to the sixth elements. The depth direction is solved analytically by Fresnel coefficients. So we go from ten to the twelfth down to ten to the sixth. Six orders of magnitude.

[pause]


## [Slide 3: Exact absorption law] (1:07 -- 2:01)

[CLICK 1]
The exact law has three factors. The absorbed power density at a point r equals S inc, the incident power density. This is set by the environment. The antenna, the distance, the reflections. We have no control over it.

[CLICK 2]
Times T eff, the Fresnel transmission factor. This captures how much power crosses the air-tissue boundary. It depends on incidence angle, polarisation, tissue properties, and frequency. Four variables.

[CLICK 3]
Times a ReLU of the dot product between the surface normal and the negative wave direction. This is a visibility gate. If the surface faces away from the wave, it absorbs nothing. This factor is exact.

[CLICK 4]
The material factor depends on four variables. We will see that it simplifies to a single number.


## [Slide 4: ANIMATION 1 -- Pseudo-Brewster compensation] (2:01 -- 3:12)

[ANIMATION: Title "Pseudo-Brewster compensation" writes on. Axes appear: angle theta on x-axis, transmission T on y-axis.]

Let me show you what happens to the Fresnel transmission when you plot it against incidence angle. This is skin tissue at 28 gigahertz.

[ANIMATION: T_s curve traces from 0 to 85 degrees. Blue curve, decreasing. Label "T_s" appears.]

The s-polarisation transmission decreases with angle. That is the standard Fresnel behaviour.

[ANIMATION: T_p curve traces. Red curve, increasing toward a peak. Yellow star marks the pseudo-Brewster angle around 78 degrees. Label and dashed guide line appear.]

The p-polarisation does the opposite. It increases toward a peak. This is the pseudo-Brewster angle. For lossy media it is not a true zero of the reflection, but the transmission still peaks.

[ANIMATION: T_avg curve traces. Green, thicker. Nearly flat. Dashed yellow line at T_0 = 0.54 appears. Yellow circumscribe highlights the flat green curve.]

Now take the polarisation average. Look at that. It is almost flat. The s decrease and the p increase compensate each other nearly perfectly.

[pause]

This was not obvious to us either.

[pause]

[ANIMATION: Variation annotation: "< 6% up to 75 degrees." Azzam reference appears below.]

Less than six percent variation up to 75 degrees. This holds for any material with a complex refractive index magnitude above 2.5. Biological tissue sits between 3 and 6.

[ANIMATION: T_s and T_p fade to gray. Title fades. T_eff(theta) writes on, then morphs to T_0 with a yellow flash.]

So the four-variable material factor collapses. T eff of theta becomes just T zero.

[ANIMATION: Punchline text writes on: "Material physics collapses to one number."]

Material physics collapses to one number.

[pause]


## [Slide 5: The geometric absorption law] (3:12 -- 3:53)

[CLICK 1]
That gives us the geometric absorption law. S ab equals S inc times T zero times the ReLU factor. The material factor is gone. All spatial variation comes from body geometry.

[CLICK 2]
For skin at 28 gigahertz, T zero is 0.54. About half the incident power enters the body. The approximation error is below six percent. At 60 gigahertz, T zero is 0.57 with even smaller error. The condition is that the refractive index magnitude exceeds 2.5, which biological tissue satisfies across the entire range from 100 MHz to 100 GHz.


## [Slide 6: ANIMATION 2 -- Geometry of absorption] (3:53 -- 5:18)

[ANIMATION: Equation builds term by term at top of screen. S_ab(r) = S_inc (blue) * T_0 (red) * ReLU (green). Equation shrinks to top-left corner.]

The equation is on screen. Now let me show you what the geometry factor actually looks like on a body.

[ANIMATION: Elliptical body cross-section draws. Wave arrow from the left with k-hat label appears.]

Here is a cross-section of a body. The wave arrives from the left.

[ANIMATION: Green normal arrows grow from the lit side via LaggedStart. Lengths proportional to cosine. Red dots mark the ReLU boundary.]

On the lit side, arrows proportional to the cosine. On the shadow side, nothing. The red dots mark the ReLU boundary.

[ANIMATION: Colored arc segments appear along the lit surface, green fading to black at the boundary. Surface heatmap.]

The heatmap shows the absorption pattern. Brightest where the surface faces the wave directly. Fading to zero at the boundary.

[ANIMATION: Normals and heatmap fade. Parallel rays from the left, some hitting the body, some missing. Shadow bar appears on the right labeled A_perp. Power equation writes at bottom: P_abs = S_inc * T_0 * A_perp.]

Total absorbed power is the integral over the surface. It equals S inc times T zero times the projected shadow area. This is the cross-section the body presents to the wave.

[ANIMATION: Rays and shadow bar fade. Wave arrow rotates from left to upper-left, then lower-left, then back. Normals update in real time.]

As the wave direction changes, the lit region shifts. The absorption pattern rotates with the wave.

[ANIMATION: Rotating arrow removed. 16 thin arrows from all directions appear around the body. "Average over all directions" text. Body slides right. Cauchy formula writes on the left: <P_abs> = S_inc * T_0 * A_ab / 4. Yellow circumscribe. Cauchy portrait and "Cauchy, 1841" attribution.]

Average over all wave directions and you get Cauchy's formula from 1841. The direction-averaged shadow area of a convex body is one quarter of its surface area. This result is 180 years old. It was just never applied to dosimetry before.

[pause]


## [Slide 7: Validation] (5:18 -- 6:18)

[CLICK 1]
How well does this work. First test: Mie theory. Mie gives the exact solution for lossy spheres, so it tests both the Fresnel physics and the geometric optics jointly. At body-relevant sizes at 28 gigahertz, the error is five to ten percent. The error is conservative, meaning we slightly underestimate absorption. The dominant source of error is diffraction into the geometric shadow.

[CLICK 2]
Second test: the Thelonious child phantom, a realistic anatomical mesh. Total absorbed power error is 0.35 percent. Local root mean square error is 3.2 percent.

[CLICK 3]
The framework error of five to fifteen percent is smaller than the dielectric uncertainty in tissue properties, which is around twenty percent. The main limitation is diffraction at shadow boundaries, which the geometric optics assumption cannot capture.

[pause]


## [Slide 8: AEGIS intro] (6:18 -- 6:26)

Let me show you what this looks like in practice.


## [Slide 9: Live demo] (6:26 -- 8:56)

[Switch to AEGIS viewer in browser]

This is AEGIS, our real-time dosimetry tool. It implements all nine fidelity levels from the framework.

[Navigate the 3D scene]

You can see the body phantom here. I can place a base station anywhere in the scene and the absorption map updates in real time. The colour scale shows absorbed power density on the surface.

[Rotate the wave direction]

Watch how the absorption pattern shifts as I change the wave direction. The lit side moves, the shadow side stays dark. That is the ReLU factor doing its job.

[Change frequency or fidelity level]

I can switch between frequencies. The T zero value updates. The spatial pattern stays the same because it is all geometry.

[Show ICNIRP compliance overlay]

There is also an ICNIRP compliance layer that flags any region exceeding the exposure limit. This runs at interactive frame rates because the underlying equation is closed-form. No simulation loop, no iteration.

[pause, respond to any questions from the room]

[Switch back to slides]


## [Slide 10: From incoherent to coherent] (8:56 -- 9:54)

[CLICK 1]
That incoherent framework is deployed in AEGIS. But 5G uses MIMO beamforming, where the situation changes.

[CLICK 2]
Here is the key difference. In the incoherent case, you add powers. One path, one S inc, one absorption pattern. With MIMO, you have multiple antenna elements, each sending a signal with a controlled phase. The fields from all elements arrive at the body simultaneously and add as complex vectors.

[CLICK 3]
The signal path sees a scalar channel at the user equipment. The exposure path sees a vector field distributed over the entire body surface. These are fundamentally different optimization targets. You want to maximize signal while constraining exposure.


## [Slide 11: ANIMATION 3 -- Coherent phasor alignment] (9:54 -- 10:56)

[ANIMATION: Title "Coherent hotspot formation" writes on. Four phasor arrows appear one by one from a common origin, each with a random phase. Different colours.]

Here are four antenna elements, each contributing a field at some point on the body. The phases are random.

[ANIMATION: Red sum vector appears. Label: "Random phases: fields partially cancel." "Partial cancellation" text.]

The vector sum is small. The fields partially cancel. This is the typical incoherent situation.

[ANIMATION: Text "The precoder controls the phases..." appears. All four phasors smoothly rotate to align at phase zero over 8 seconds. Sum arrow grows long.]

Now the precoder aligns the phases.

[ANIMATION: Flash at the tip of the long sum arrow. Label morphs to "Aligned: absorption concentrates."]

When the phases align, the field magnitude is the sum of the individual magnitudes. Absorption concentrates at that point.

[ANIMATION: Phasors fade. Coherent law writes: S_ab(r) = ||G_tilde(r) x||^2. Then P_abs = x^H Q x. Then Q definition. Yellow circumscribe around P_abs equation. Annotation: "Q: Hermitian PSD, M x M. Dominant eigenvector maximises body absorption."]

The coherent absorption law replaces S inc times the geometric factor with the squared norm of a field channel matrix G tilde times the precoding vector x. Integrate over the body surface and you get P abs equals x Hermitian Q x. Q is the exposure operator. It is an M by M Hermitian matrix that captures the body's complete absorption response to any precoder.


## [Slide 12: Exposure-constrained beamforming] (10:56 -- 11:48)

[CLICK 1]
The coherent law and the exposure operator are on the left. Q captures the body's absorption response. It is Hermitian and positive semidefinite. Its eigenvectors are the body's absorption modes.

[CLICK 2]
The design problem: maximize signal power at the user equipment subject to a constraint on total absorbed power. This has a closed-form solution. The optimal precoder is a regularised channel inverse. Lambda Q plus nu I, inverse, applied to the conjugate channel vector.

Lambda controls the trade-off. When lambda is zero, you get standard matched-filter beamforming, maximum signal, no body awareness. As lambda grows, the precoder steers energy away from directions that the body absorbs efficiently. The body's absorption eigenvectors get suppressed.


## [Slide 13: Summary] (11:48 -- 12:08)

[CLICK 1]
Three results. Pseudo-Brewster collapses the material to T zero. Dosimetry becomes geometry. Ten to the twelfth becomes ten to the sixth. The coherent extension gives the exposure operator Q with a closed-form beamformer.

[CLICK 2]

[CLICK 3]
Tissue physics makes dosimetry geometric. The geometry is fast. The fast computation enables exposure-aware network design.

[pause]


## [Slide 14: Thank you] (12:08 -- 12:14)

Thank you.

# Transmit-to-path map note

Exposure operators require more than body state.  The body state tells us how
the body couples incident paths, but the network also needs the map from its
controllable transmit variables to the path amplitudes that arrive at that
body.

The useful factorization is

$$
Q_u(\xi_u) = B_u^H M_u(\xi_u) B_u .
$$

Here:

- `xi_u` is body state: position, orientation, pose, mesh, tissue, grip or
  device-body geometry.
- `M_u(xi_u)` is the path-space exposure Gram: how pairs of incident paths
  couple through the body surface and Fresnel filter.
- `B_u` is the transmit-to-path control map: how BS antenna, port, or beam
  weights produce complex amplitudes on the paths incident on body `u`.

`J` is only a special case of `B`.  In the monograph and AEGIS ray-traced
path object, each path is tagged by `element_index`, so the map is a binary
dispatch matrix:

$$
B_u = J_u, \qquad (J_u)_{n m}=1\{j(n)=m\}.
$$

In a real system this binary view is usually too narrow.  A calibrated array
or beam model gives a dense map:

$$
(B_u)_{n m} = \alpha_n a_m(\Omega^{\mathrm{AoD}}_n).
$$

or, at beam/codebook level,

$$
(B_u)_{n b} = \alpha_n g_b(\Omega_n).
$$

Realistic ways to obtain `B_u`:

1. **Ray-traced digital twin.** DiffeRT/Sionna generates paths and transmit
   element or port tags.  This gives `J` or `B` directly and is the right
   first implementation route.
2. **BS-side channel sounding.** Estimate path delay, AoD, AoA, gain, and
   polarization from uplink SRS or downlink sounding, then build `B_u` from
   the calibrated BS array response.
3. **Beam/codebook approximation.** If only beam weights are controllable,
   build `B_u` from beam gains toward each estimated path direction.  This is
   lower-resolution but closer to commercial systems.

Implementation API should therefore be closer to:

`build_exposure_operator(body_state, path_state, tx_control_map)`

not just:

`build_exposure_operator(body_state)`

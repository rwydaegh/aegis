# Research canvas: AEGIS

**Name:** Robin Wydaeghe
**Date:** 31/08/2026

## Research problem

Wireless devices and antennas must stay within limits for human electromagnetic exposure. Engineers therefore need to know how much power a person absorbs for different antenna positions, beams, body poses and device designs. Accurate computer simulations can take hours or days for a single case. Testing every relevant configuration is often impractical, so engineers use sparse samples or conservative worst-case assumptions. This can hide important exposure cases, limit design choices and move problems to a late stage of development. My applied research makes these calculations fast enough for large-scale screening and design.

## Context

I developed AEGIS during my PhD in Engineering Physics at the WAVES research group of Ghent University and imec. My PhD was supported by GOLIAT, ETAIN, SHAPE and ATTO and involved researchers in wireless propagation, measurements and human-exposure modelling. I developed the core AEGIS method and software independently.

## Your research results

I found that absorbed power can often be calculated from tissue properties and the exposed surface geometry of the body, without simulating the complete body volume. I turned this into AEGIS, working software that produces full-body exposure maps in milliseconds and screens many configurations. The core research is mature. Industrial validation and integration are the next steps.

## Output and ownership

- The geometric dosimetry method and mathematical models
- Algorithms for exposure mapping, screening and beamforming
- The AEGIS software engine, API and interactive 3D viewer
- Validation data, automated tests, documentation and technical know-how
- A patent application in preparation and research publications

I am the sole inventor and owner of these results.

## Differentiators

AEGIS replaces repeated full-body simulations with a fast surface calculation. It connects antenna and propagation data directly to the energy absorbed on a realistic 3D body, including multiple sources and beams. It supports screening and optimisation. Detailed simulation and measurement remain for final validation.

## Alternatives and competition

Current alternatives are full-wave simulation tools such as Sim4Life, CST, HFSS and Feko, physical measurement systems such as DASY, and simpler worst-case compliance calculations. These methods are trusted, but they are either computationally expensive, measurement-intensive or too conservative for exploring many designs.

## Upcoming alternatives and competition

Faster GPU solvers, hybrid simulation methods and AI models trained on full-wave results will reduce simulation time. Existing simulation vendors may also add screening and optimisation layers. AEGIS must therefore compete through transparent physics, independent validation, easy integration and speed across many configurations.

## About you

I am a Belgian engineering physicist with bachelor's and master's degrees from Ghent University and a submitted PhD thesis. I combine electromagnetic theory, simulation and scientific software, with experience at Keysight, IT'IS/ZMT and international research projects. I want to build industrial software or a deep-tech company around physics. I am also interested in technology, entrepreneurship, chess and current affairs.

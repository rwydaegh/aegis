Spinal manipulations

Introduction
1. The very general first or second statement should be about only FR2 and mmWave and the why: it offers higher bandwidths over there so more datarates. You're already pretty close. No need for FR1 or FR3. No 'load bearing'
2. 'slowed down on the schedule' is too specific. A more general statement like 'remain challenging' or something and that deployment is not quite there yet (cite something idk, maybe a placeholder)
3. bodies are everywhere
bodies are, and the array gain that the panel buys is quickly
given back by the pedestrian standing between the antenna
and the served user. --> bad wording but spinally ok. shorter and more normal wording
4. Second point: the rollout is mainly legislatively blocked with fear of exposure from public (cite brussel geneva etc as examples, no need for V/m, irrelevant). not this sentence, a good Robin sentence, but something more along those lines.
5. 'that ties the two frictions together' lol dude. no
6. Note that Hochwald etc is for the uplink... I think one of the first citations should be that seminal one about the human block X (a ton) of dB of the signal in mmWave
7. you CANNOT cite the monograph or the TAP paper. you do this a lot, do NOT do this. there are three citations like this. And it's not just removing citations, it's thinking what to do instead then... Esp for the intro we need to rethink the literature positioning. 
8. Tbh for RIS lets go with this verbatim. Get rid of your 'parallel work' sentence. 
"The human body is a passive lossy reflector mediated by its pose and actuated by intelligent instructions on a smartphone. We aptly name this a \emph{Reflective Intelligent Human Body} (RIHB)." This sentence or a very slight variation of it must somehow feature in the intro (you can move it around a bit idc)
9. what is the other direction? downlink? not so clear. but good point though.
10. Throughout the whoooole paper you keep splitting h in hLOS hbody and hNLOS. Why? arent our algos smart enough for a general case h= h_BS + h_body? I havent quite read the whole paper but this seems reasonable to do, no? (i could be missing smth)
11.  no current body-twin
formulation provides the user with the real-time absorbed-
power feedback that the regulatory framing implicitly
promises; --> not the way you say this. More like, 'no current body digital twin provides the public, regulators or epidiomiloists both an accurate and instantaneous determination of exposure'
12. the body-mediated channel coefficient hb has,
to the authors’ knowledge, been treated only as a direction-
resolved scattering object suited to forward radiosity, not as
the receiver-anchored Kirchhoff integral that the phone-on-
body geometry actually demands --> this is very technical. idk if it fits in the big picture. maybe good to think a bit what to put instead... 
13. I think a key gap is simply that there is no way for ppl to know that they are blocking the signal and how their pose can improve performance. and this with enough SI keywords so the editors like us (closed loop for example)
14. perhaps in this intro there is also not enough emphasis on the vision. it needs to be clear what we're asking: the user is in a bad pose, an app or on-device feedback signal facilitates communication with the user such that that changes, and then it's time for the user to that kinda rare thing of downloading a shit ton of data (exploiting gigabit internet that we've been promised). this idea is kinda missing. 
15. he closed loop
between user-side pose actuation, on-device twin update,
and base-station-side precoder adaptation has not been
formulated or empirically tested --> id be careful with this one too
16. okay, now that im reading on after 'This work addresses', you do say it like I wanted... It is quite jargon technical tbh, can be toned down just a tad so a more general audience doesnt tune out. But stay academical and in style though. Obviously the sentences are too long but that's a style thing the style pass will pick up
17. A passive reconfigurable scatterer whose surface phase
pattern is fixed by pose and whose only tuning is the
user’s intelligence is, in the same role as a reconfigurable
intelligent surface but with the human in place of the panel,
a Reflective Intelligent Human Body (RIHB). --> this is actually not a bad sentence. can you suggest a mutant of this with mine? or what do you think?
18. the novelty should also be about the quickness of our computation of SARwb and local averaged APD (drop these words) in the whole mmWave band, much fast than FDTD. So take a page out of the TAP paper playbook. 
22. Your contributions are a bit too specific and not so clear on a high level. 
It would also be a power move to say you compute exposure per-slot realtime on smartphone compute hardware, could be cool to include...

From here on, I wont be going in the meso-tomicro scale but zooming out my feedback
doesnt mean you shouldnt still put attention on the meso to micro scale. Usually for formulas/derivations: if you keep it dry, have nice and rigorous, airtight derivations and clean ones, it's hard to do anything wrong (Define stuff, refer well, simple sentences). Overall that is okayish right now.

Your system model part is spinally really good. I like how you defer to things. Equation 1 is a bit abstract maybe (mixing scalars and vectors?) and things arent well defined. On the flip side I guess you dont wanna dwell on the details here, which is good... Following Wout pet peeves and my own feedback from the TAP paper the flowchart needs to be introduced earlier and be really a point to hang onto. 

Saying things are deliberately comrpessed is not a good wording... but it is the right idea

you state two conditions i and ii for culling. Why not just have the right equation with []_+ and V in the first place? like, earlier? Also, is u, v from gram scmidt actually used in any derivation? I wonder on the use of this paragraph... Saying it is a SMPLX is important tho. Maybe more focus on the RT scene and J too. 

T approx 0.54 is a funny thing to make a whole equation...

Fig 1 flowchart of Network-centric DTN architecture
- look at the png, the white labels are in white rectangesl which COVER the arrows, so they need to either go a bit higher/low wrt the arrows or not have a white rectangle background for absolutely no reason. 
- K99 mode SVD gamma fit: nobody understands this on first glance.
- I think the elements you put in here have to be understandable on first glance (some of it is ok like precoder x etc). Eg J must be clear comes from RT
- do NOT use ReLU but []_+ like in the TAP paper

I do like the pacing at the beginning and that it's fast. Make sure you refer enough to the Suppl info

Saying Kirchoff operator is the 'new' central object 'of this paper'... the word new isnt necessary. that's just cuz we went through this process together, but the reader doesnt care. be careful of those kind of mistakes (artefacts of our conversation). also 'this paper' for no reason...

Figure 3: you're missing the environment in this image. it's still from back when we didnt have any... also a lot of work on sizing here... the fontsize needs to be the native one from the text. will need to iterate a lot on it. 

So are we actually using J = 2 n x H Vnt ? or is this just to say we only look at the visible-from-UE triangles? I think we can just use prose then. 

"Why a UE-anchored render: a complexity argument"

First of all: terrible subsection name (never ask questions)
Again, I wouldnt be framing this from our earlier mistake of doing it forward and now we do it backwards for speed. Tbh i wonder if this one is needed in the text. The idea should be in there, but just smaller and really direct: we do it this way, period. Cost comparison is not needed.


Sec V.B: If you have tried various things and settled on one, just pick the one you go for and dont speak of any others. 

" dominates in both far-BS
(rank-1 regime, K99 = 1) and close-BS (rank-many regime,
K99 = 4) geometries."
is this a consequence of our old scenary? we are now raytracing.. still relevant? what about section VII then?

"At σjoint = 4◦ (the canonical operating point for an
in-pocket consumer-grade IMU), the cap-violation rate
drops from 2.47% (uncalibrated dual-ascent) to 1.06%
(γ-corrected closed loop). At the worst-case σjoint = 16◦
(poorly-calibrated IMU), the violation rate stays at 1.17%
under the closed loop while the uncalibrated baseline climbs
to 4.16%. The underlying mechanism is that the K = K99
SVD basis at the served-user geometry absorbs 93.5% of
the pose-induced channel-prediction error at 20 dB uplink
pilot SNR.
" im lost. but I also didnt read the Suppl inf. so could be clearer... idk what to do about it tho

A scientific question: how do we know comfort is "Comfort becomes a Mahalanobis ball in latent space" ? Perhaps at least a citation is worth it.

"The user need not see the gradient itself. A simple haptic
or visual cue (“stronger signal this way”) s" naaaaah man

OK so from a engineering perspective I think I see a big issue. You have sampled 13K poses from 50 AMASS walk cycles, but these are only walk cycles. So all poses are frames of a human walking. Humans can do anything... Have you looked at your hero figure (a) and (b) baseline to best pose? it seems barely different? is the human also orienting the whole body? 

Can you report some basic configuration of the ray-tracer? amount of reflections... material is made out of concrete I guess... You also need to argue in this paragraph that the fidelity of the environmental twin is not of huge importance as it gets calibrated anyways. the point is for the BS to know what the main MPC's AoA is at the UE just based on their position (given by GPS or IMU data). This is crucial to inclde, maybe even in the big flowchart. You will btw need quite a bit of reflections and diffraction in the RT to be accurate. any other parameters there? 

im still not satisfied with the RX positions and which are supposed LOS/NLOS
1. take a regular grid high in the sky. around the BS
2. project downwards
3. if on a building (height isnt 0), drop
4. if too close to the BS, drop
5. check if LOS/NLOS using Sionna
6. RT. If no paths or too few rays coming in, drop too. 
Show me the result. Look at it urself. also plot the facing direction of the BS in that figure

So for the main results you will need to remake them anyways then i will criticize.

"feedback that the regulatory framing assumes but does not
currently deliver" I hate this framing. Also baaad subtitle names in VII. 

Your discussion in general is a tad small. But I like that you put it there. Lets leave it alone for now. 
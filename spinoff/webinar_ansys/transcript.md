# Enabling 6G Technologies - transcript

Ansys webinar presented by **Shawn Carpenter** (Program Director, Ansys), 26 June 2024.

Source: `../Enabling 6G Technologies.mp4` (01:00:06). Speech transcribed with
faster-whisper `large-v3` (float16, GPU). Slide images were auto-extracted from
the video; each `## Slide N` heading marks when that slide first appeared on
screen, so the deck reads alongside the talk. Combined deck: `slides.pdf`. See
`README.md` for how this was produced.

---


## Slide 1 - appears [00:00:00]

![Slide 1 (shown 00:00:39)](slides/slide_01_00-00-39.png)

**[00:00:00]** Today, we're joined by Sean Carpenter, Program Director at Ansys, who will be presenting this webinar and bringing his extensive expertise in engineering simulation and software innovation to the discussion.

**[00:00:12]** So, with that, I'll just hand it over to Sean to start the main presentation.

**[00:00:17]** Thank you, Raha.

**[00:00:18]** Okay, let's proceed.

**[00:00:20]** Welcome, everybody.

**[00:00:20]** Thank you for joining us today, this morning or afternoon, depending on where you're located.

**[00:00:25]** We appreciate you giving us a chunk of your summer here today.

**[00:00:28]** I'll be talking today about, excuse me, enabling 6G technologies and, in particular, focusing on some physics that drive the AI revolution into the 6G radio and antenna systems, concentrating particularly on the wireless link for these systems.

**[00:00:43]** So, let's just dive right in here and get started.

**[00:00:46]** So, this is going to be about, in particular, like I said, looking at some of the challenges that we're going to see in the design and implementation of 6G wireless networks.


## Slide 2 - appears [00:00:47]

![Slide 2 (shown 00:01:24)](slides/slide_02_00-01-24.png)

**[00:00:55]** This involves access point antenna designs for 5G and array systems, particularly access points, base stations, and so forth.

**[00:01:04]** But we're also combining that with wireless channel modeling that is also based on physics, and physics that is both fast and accurate.

**[00:01:12]** That sounds kind of like a difficult promise, but I hope by the end of today's presentation, you'll agree with us that this is something that's truly attainable.

**[00:01:23]** Now, further, wireless channels are a very important part of the design and implementation of 6G.

**[00:01:25]** Wireless channels are going to be important to us.

**[00:01:27]** They are a means by which we can generate synthetic data and then connect to network digital twins.

**[00:01:32]** And you'll see some of this demonstrated here later in our presentation as we go on.


## Slide 3 - appears [00:01:37]

![Slide 3 (shown 00:02:30)](slides/slide_03_00-02-30.png)

**[00:01:38]** So, let's just talk a little bit here and I will focus admittedly here on the things more on the wireless link end of things, the wireless gap or the physical layer.

**[00:01:47]** But some of the challenges that we see coming down the pipe here for 6G radio and antenna systems designs that form that link connecting,

**[00:01:55]** you know,

**[00:01:55]** to the network,

**[00:01:55]** to the network,

**[00:01:55]** to our signal processing systems.

**[00:01:58]** We're seeing the addition of new spectrum and that's across all of the bands, not just rising up into the terahertz or sub terahertz frequency bands, but we're seeing expansion in the FR1, which is the coverage layer, FR2 in the mid bands as well as up at the millimeter waves.

**[00:02:12]** And that has implications on the antenna designs, it has implications on the radio systems that are connected to those antennas, and it certainly has implications on the base band processing systems, which are becoming progressively more and more important.

**[00:02:25]** And at the moment we're seeing more and more complex as we develop bigger and better silicon to service these requests, of course we'll have more band, more spectrum, more sub carriers to process which, and and of course more, uh, degrees of freedom with model user massive MIMO, which adds up to a big

**[00:02:42]** a big

**[00:02:42]** baseband processing challenge.

**[00:02:45]** In addition, we anticipate new waveforms and the methodologies behind how we resource, schedule, the resources, across the band, and they know the time and frequency schedules.

**[00:02:55]** We'll have coexistence challenges with other services, minimize our interference, minimizing

**[00:03:01]** our inter-cell interference sources, and we also anticipate in 6G bringing a very sharp

**[00:03:10]** introduction of AI at the radio and at the wireless channel so that we can deliver the

**[00:03:15]** best possible service and anticipate the conditions under which we need to deliver service to

**[00:03:21]** subscribers or to customers across this channel.


## Slide 4 - appears [00:03:24]

![Slide 4 (shown 00:03:48)](slides/slide_04_00-03-48.png)

**[00:03:24]** Now, just to illustrate what's going on in the bands, and this focuses primarily on the

**[00:03:28]** capacity and coverage there, excuse me, that's at frequency bands from roughly 3 to up to

**[00:03:34]** about 15.5 gigahertz, we can see at the most recent World Radio Conference meeting that

**[00:03:40]** worldwide we are expecting the addition of new spectrum and the harmonization of some

**[00:03:46]** of this additional spectrum into the existing spectrum plans, and as you see, it's geographically

**[00:03:53]** dependent.

**[00:03:54]** The providers of equipment that need to operate in these areas are going to need to anticipate

**[00:04:00]** all of these worldwide uses and the local spectrum allocations, and you can clearly

**[00:04:06]** see there's going to be a need for multiband systems here unless we're going to build a

**[00:04:10]** separate antenna for every band that comes online.


## Slide 5 - appears [00:04:13]

![Slide 5 (shown 00:05:15)](slides/slide_05_00-05-15.png)

**[00:04:15]** Now, in the past, when we've been modeling particularly systems at a couple of gigahertz

**[00:04:20]** and below, the sort of the existing models that were there to predict broadcasts and

**[00:04:25]** predict propagation, predict how well signals would get from an access point to a subscriber

**[00:04:30]** were more or less carried as analytical models, cost models, empirically developed models,

**[00:04:35]** and they did a pretty reasonable job for us at the 2G, 3G, 4G nodes, but as we've gone

**[00:04:42]** to higher frequencies and as we've gone to more creative apertures, more creative antenna

**[00:04:46]** systems in our base stations, the need has arisen for more complex channel models to

**[00:04:51]** represent what's going on in these systems.

**[00:04:53]** So, as we've gone to higher frequencies and as we've gone to more creative apertures,

**[00:04:54]** more creative antenna systems in our base stations, the need has arisen for more complex

**[00:04:55]** channel models to represent what's going on in these systems.

**[00:04:56]** Now, across the industry, there's a general agreement that that has to be expanded to

**[00:05:00]** include some ray-based methods so that we can begin to anticipate the changes that might

**[00:05:05]** happen both in wideband systems and at bands where we don't yet have a great deal of empirical

**[00:05:10]** data, and as we go to 6Gs, we begin looking at, you know, further additional spectrum,

**[00:05:18]** new antennas, and newer scenarios, high-speed, you know, high-velocity subscribers and so

**[00:05:23]** forth.

**[00:05:24]** So, there's, I think, going to be a need to combine ray tracing in bespoke locations

**[00:05:29]** that combine computational electromagnetics into the picture.


## Slide 6 - appears [00:05:33]

![Slide 6 (shown 00:06:46)](slides/slide_06_00-06-46.png)

**[00:05:33]** Now, if we're going to derive or come up with a model for wireless modeling that we could

**[00:05:39]** use at any band in any setting, it's going to need to satisfy some requirements.

**[00:05:45]** Some of the obvious ones you can see here and some not so obvious ones.

**[00:05:48]** Obviously, we want to be able to support a channel modeling methodology for any location

**[00:05:53]** on the planet where we might install a network.

**[00:05:55]** Or install an access point that will operate for us at frequencies from, you know, VHF or

**[00:06:01]** high VHF, 350 megahertz up to, you know, hundreds of gigahertz and be suitable.

**[00:06:06]** This is key.

**[00:06:07]** Be suitable for very wideband systems.

**[00:06:10]** Operational bandwidths for some of the 6G systems are anticipated to be hundreds of

**[00:06:14]** megahertz or multiple gigahertz and involve the processing of thousands or maybe tens

**[00:06:20]** of thousands of subcarriers and carrier aggregation across multiple bands.

**[00:06:25]** We want a channel model that will support modeling for urban, suburban, rural, indoor

**[00:06:30]** and high velocity scenarios, can accommodate full and high fidelity three-dimensional antenna

**[00:06:36]** representations and three-dimensional propagation, again, potentially over very broad bands.

**[00:06:43]** It should exhibit smooth fading and parameter drift over time with moving subscribers.

**[00:06:48]** That's important because it's the motion that causes channel changes to vary rather significantly

**[00:06:54]** with the frequency selectivity.

**[00:06:55]** It becomes particularly pronounced and important.

**[00:06:59]** It should have a spatial consistency.

**[00:07:01]** So when we model array systems, they should show just the phase differences that we anticipate

**[00:07:05]** for an expanding spherical wave that is, you know, approaching or impinging on our access

**[00:07:11]** system.

**[00:07:12]** We should see channel characteristics vary smoothly with frequency and not be discontinuous.

**[00:07:18]** And we should see data at adjacent frequencies correlating to what goes on at a particular

**[00:07:22]** frequency of interest.

**[00:07:23]** It should exhibit spherical rave behavior.

**[00:07:25]** And array nonstationarity if we're going to model massive MIMO and multi-user massive

**[00:07:30]** MIMO.

**[00:07:32]** And of course, we want to be able to accommodate motion, a channel model that can accommodate

**[00:07:36]** motion and do so very efficiently for both slow and fast movers.

**[00:07:41]** And then finally, include the physics of materials.

**[00:07:45]** Some surfaces are rough.

**[00:07:47]** Some will exhibit diffuse scatter.

**[00:07:49]** They'll have loss, absorption.

**[00:07:52]** They'll exhibit reflection or partial reflection and transmission.

**[00:07:55]** And we want to be able to capture that and the polarization shift that happens with


## Slide 7 - appears [00:08:00]

![Slide 7 (shown 00:09:12)](slides/slide_07_00-09-12.png)

**[00:08:00]** waves hitting those surfaces.

**[00:08:04]** So for close to almost 40 years now, ANSYS has been servicing the high frequency community

**[00:08:09]** for very precision electromagnetic analysis to validate designs for things as small as

**[00:08:14]** a transistor and things as large as an antenna and even pushing recently into things as large

**[00:08:20]** as a city.

**[00:08:22]** So here you can just see a quick run through, a demonstration of the things that we've been

**[00:08:24]** doing.

**[00:08:25]** We've involved antenna performance modeling, modeling multiple antennas on a pole to capture

**[00:08:31]** interference and cross coupling, looking at antennas as packaged into handheld devices

**[00:08:37]** or mobility devices and understanding how they couple, how the packaging impacts their

**[00:08:41]** efficiency and radiation quality.

**[00:08:44]** And then finally, beam forming systems and now most recently, modeling the propagation

**[00:08:49]** of energy through electrically very large environments you see illustrated here from

**[00:08:54]** our solver stack.

**[00:08:55]** The project is called Antenna Performance Modeling.

**[00:08:55]** Antenna Performance Modeling is a tool that can be used to simulate the propagation of

**[00:08:56]** a wavefront through a big chunk of a city that could be hundreds of thousands, maybe

**[00:09:02]** close to a million wavelengths in extent at the frequency of interest.

**[00:09:07]** All of this comes together.

**[00:09:08]** Everything that you simulate at the rudimentary level like an antenna can be embedded and

**[00:09:12]** progressively built up to assess the next level of integration, excuse me, and then

**[00:09:17]** set in place into the context of something like a city.


## Slide 8 - appears [00:09:21]

![Slide 8 (shown 00:10:20)](slides/slide_08_00-10-20.png)

**[00:09:23]** So we want to virtualize end-to-end communications.

**[00:09:26]** How do we do that?

**[00:09:27]** Well, the consideration, of course, are the things in the middle.

**[00:09:31]** We've got a wireless channel, and when I use that term, that's what I'm talking about.

**[00:09:35]** It's the channel that takes the energy from a transmit antenna to a receive antenna, and

**[00:09:42]** that can include things like line-of-sight propagation beyond light-of-sight where we'll

**[00:09:47]** have diffraction and multi-path effects.

**[00:09:51]** We'll have detailed interaction with terrain, with man-made structures, these structures

**[00:09:56]** have physical materials and physical reflection and transmission properties, and they'll

**[00:10:01]** have surface roughnesses.

**[00:10:03]** But that channel is influenced by the antenna and the manner in which the antenna directs

**[00:10:08]** energy.

**[00:10:10]** And so we want to connect into this channel model or bring to it the physics of a high-fidelity

**[00:10:15]** antenna model and include that as part of our antenna system model.

**[00:10:20]** So that antenna model could be rooted in high-fidelity physics simulation, it could be rooted also

**[00:10:25]** in...

**[00:10:26]** It could be rooted in measurement-based models or array system models that might include

**[00:10:32]** mutual coupling effects.

**[00:10:34]** Now, of course, to do an end-to-end physical layer or baseband-to-baseband model, we also

**[00:10:41]** have to connect our radios.

**[00:10:42]** That would be for a full link layer simulation, and so here we would use like a digital signal

**[00:10:48]** processing stack or capture a model like a software-defined radio model so that we can

**[00:10:54]** wrap that around and evaluate the modulation.

**[00:10:56]** Okay.

**[00:10:56]** So we have the modulation and the demodulation, the channel estimation, all of the things

**[00:11:00]** that we do to recover signals so that we can get to very precise link layer or link level

**[00:11:07]** one kinds of metrics, right, to assess what's going on within our channel.

**[00:11:12]** But that rests on an accurate model of our channel, which is the physics of the antenna,

**[00:11:17]** the physics of the propagation and scattering in the environment.


## Slide 9 - appears [00:11:20]

![Slide 9 (shown 00:11:25)](slides/slide_09_00-11-25.png)

**[00:11:21]** So let's talk a little bit about this process.

**[00:11:24]** It starts with high-fidelity antenna modeling.

**[00:11:26]** And so in order to do that, right, we'll need to have antenna designs.


## Slide 10 - appears [00:11:27]

![Slide 10 (shown 00:12:13)](slides/slide_10_00-12-13.png)

**[00:11:30]** They serve the RF link, and they have to be accurately characterized in our link simulation.

**[00:11:36]** Now, they have an installed performance assessment.

**[00:11:39]** That basically means when you take that antenna and you put it onto a host platform, you put it

**[00:11:44]** on the tower or you mount it or integrate it into a car or a quadcopter or an aircraft or a

**[00:11:50]** handheld device, that installation interaction, the host platform interaction, will modify how it

**[00:11:56]** radiates.

**[00:11:57]** It will modify its feed point characteristics.

**[00:11:59]** And so we want to be able to capture that because its performance will directly impact

**[00:12:04]** the link that it's serving.

**[00:12:06]** And then for antenna systems that provide MIMO capability or multi-user massive MIMO,

**[00:12:11]** we have multiple elements tightly packed into an antenna system, and we want to characterize

**[00:12:17]** their radiation, but we want data available on a channel-by-channel or a polarization-by-polarization

**[00:12:23]** basis so that we can capture the information.

**[00:12:26]** And we want to have information that we need to evaluate beam-forming algorithms or to evaluate

**[00:12:32]** different kinds of MIMO techniques that we might apply in the baseband processing.

**[00:12:38]** Now, once we have a model for everything that goes on end-to-end from our transmitter side to our

**[00:12:43]** receiver side, we can capture that into what is classically called the H matrix or the channel

**[00:12:49]** matrix.

**[00:12:50]** It's the characteristic for a time-varying wireless channel at a particular instant in time.


## Slide 11 - appears [00:12:55]

![Slide 11 (shown 00:13:39)](slides/slide_11_00-13-39.png)

**[00:12:57]** And then, of course, we want to be able to capture data from the antenna system.

**[00:13:01]** So, we want to be able to capture data from the antenna system, and we want to be able

**[00:13:06]** to capture data from the antenna system.

**[00:13:08]** Now, let's talk about the antenna systems.

**[00:13:10]** This is kind of flows through three sort of user personas.

**[00:13:15]** One is the antenna system developers who are charged with either designing an individual

**[00:13:20]** antenna or they're charged with developing an array system and optimizing that system

**[00:13:25]** for best radiation efficiency and radiation coverage.

**[00:13:27]** It's, you know, how well it receives energy, how efficiently it radiates.

**[00:13:31]** And that's a great model, a great starting point.

**[00:13:34]** They've put a lot of care into developing that information, but that's not usually quite enough.

**[00:13:39]** You need to know how it's going to perform when it's installed in a particular location.

**[00:13:43]** And that's where we flow to the antenna system integrators.

**[00:13:46]** They often will take a particular antenna design and place it onto the intended service location

**[00:13:52]** or integrate it into a host platform and then assess its installed performance in terms of

**[00:13:57]** how efficiently it radiates or accepts power, how efficiently it radiates the power spatially.

**[00:14:03]** Then the third step usually goes to the network architects and some of the RF systems engineers

**[00:14:08]** who are charged with assessing and modeling the channel, looking at link modeling.

**[00:14:12]** So if they're primarily concerned with link coupling simulations or looking at area field coverage

**[00:14:18]** that is possible with a given antenna system.


## Slide 12 - appears [00:14:23]

![Slide 12 (shown 00:15:14)](slides/slide_12_00-15-14.png)

**[00:14:23]** So just another look here at installed antenna systems.

**[00:14:26]** And to reinforce the idea that this is a very, very, very, very, very, very, very, very important

**[00:14:27]** thing.

**[00:14:28]** And of course, the idea that the installation matters for the antenna.

**[00:14:31]** Remember, antenna spec sheet patterns are not always enough to accurately describe how

**[00:14:35]** your antenna is going to serve the RF link.

**[00:14:38]** You really need to take a look at or at least consider what its installation effects are going to be,

**[00:14:43]** how it interacts with its host platform, with its mounting location.

**[00:14:48]** And to that end, this is a part of our simulation stack.

**[00:14:51]** Once you have an antenna design, you can integrate it into something like you see this tractor

**[00:14:55]** or pack them into.

**[00:14:56]** Pack them into a mobile device or place them on different vehicles.

**[00:15:00]** And you can see how varied and interesting some of these patterns get with near field

**[00:15:06]** interaction of either the platform or with parts of the human body, for example,

**[00:15:11]** or other articulating mechanical structure around your antenna.

**[00:15:16]** Now, you may say, Sean, I don't have an antenna model.


## Slide 13 - appears [00:15:17]

![Slide 13 (shown 00:16:03)](slides/slide_13_00-16-03.png)

**[00:15:20]** I buy an antenna from a vendor.

**[00:15:23]** How can I get an antenna model when it's really hard to get?

**[00:15:25]** When it's really hard to get a model that I could take and put onto a platform and simulate?

**[00:15:32]** Well, the good news is you can synthesize ready-to-simulate models in the ANSYS HFSS tool stack.

**[00:15:39]** We actually have a toolkit that will support about 70 different topologies.

**[00:15:43]** Now, you may not be able to capture exactly the same antenna that comes from your vendor,

**[00:15:47]** but you could get something that is topologically very similar so that your simulations can still have good fidelity.

**[00:15:54]** So if you know they're using a patch antenna design at 2.4 gigahertz, for example,

**[00:15:59]** you could synthesize that very quickly.

**[00:16:01]** It synthesizes the designs based on your textual input here, and they're ready to solve.

**[00:16:06]** And you can see some examples here of the different topologies that are available.

**[00:16:10]** These are instantly built, ready for simulation.

**[00:16:13]** They're fully parameterized, so if you want to build them into a larger array,

**[00:16:18]** you have all of the shape and size characteristics baked into the model.

**[00:16:22]** And you can basically go through them.

**[00:16:25]** You can go off and grab that structure and drop it onto like an aircraft model or a car model


## Slide 14 - appears [00:16:31]

![Slide 14 (shown 00:17:21)](slides/slide_14_00-17-21.png)

**[00:16:31]** in order to solve the installed performance.

**[00:16:33]** Another very important aspect of 6G communications is going to be the access point designs that are coming forward.

**[00:16:42]** Obviously, phased arrays are a big part of it.

**[00:16:44]** We see the growing number of elements that are in 5G-based stations today.

**[00:16:48]** Most of those leading edge systems now are giving us, you know,

**[00:16:53]** 32 to as many as 256 ports, like 128 elements or super elements that are dual polarized,

**[00:17:01]** so you have two polarization outputs off of each element.

**[00:17:04]** And we want to be able to simulate these things.

**[00:17:06]** We want to – maybe we want to optimize them for coverage,

**[00:17:09]** or we want to evaluate very accurately their performance across the entire array and over a very broad band.

**[00:17:17]** ANSYS has developed a technology for building these up that are built upon the HFSS 3D component concept.

**[00:17:23]** The component is a basic building block for the different parts of your array.

**[00:17:28]** Some of those building blocks can contain antennas, antennas with multiple ports.

**[00:17:32]** Some of those building blocks may be structure around the antenna, buffer space,

**[00:17:37]** finite edge distance to the edge of your ground plane, and so forth.

**[00:17:41]** But anything that would appear in that design that's going to be electromagnetically important,

**[00:17:45]** and particularly the edges, right, of your array, or an integrated radome.

**[00:17:49]** You can arrange these automatically with these parameterized units,

**[00:17:53]** and you can take these cells and drop them in, change the shape factor of your array at any time,

**[00:17:58]** and then automatically create an open region to take this ready for simulation.

**[00:18:03]** Building up an array like this for simulation is something that can be done as quickly as minutes

**[00:18:08]** when you have these components all built up.

**[00:18:11]** And on the simulation side, I won't go in too much detail here,


## Slide 15 - appears [00:18:12]

![Slide 15 (shown 00:18:51)](slides/slide_15_00-18-51.png)

**[00:18:15]** but the power that this methodology has extends to saving you time and resources in the simulation.

**[00:18:22]** You can actually, in parallel, mesh each of these unit cells so that they have good convergence,

**[00:18:29]** and then stitch them together in whatever arrangement you specify,

**[00:18:33]** and simulate the cross-couplings between all of these regions using the meshing that we've accomplished for the unit cells.

**[00:18:40]** And this, again, enables you to put together very extensive designs.

**[00:18:45]** Focus your resources on simulating the unit cells and then solving for the overall

**[00:18:52]** the constructed finite array system can be done in a fraction of the time

**[00:18:57]** with the fraction of the resources that it would take to do an explicit simulation of a complete array design in one go.

**[00:19:03]** And when you do that, you've got broadband information for all of your ports

**[00:19:08]** that will be good under any beam steering angle that you're interested in,

**[00:19:12]** really under any condition that you will apply in terms of excitations for the array.

**[00:19:17]** So you've got a good array model that can be applied to a collection of power amplifiers

**[00:19:22]** that might drive each of these channels.

**[00:19:24]** And to look at any kind of beam steering that you want to.


## Slide 16 - appears [00:19:27]

![Slide 16 (shown 00:20:59)](slides/slide_16_00-20-59.png)

**[00:19:28]** Look at an infinite number of beam steering combinations, multi-beam state vectors,

**[00:19:33]** and whatever you want to do.

**[00:19:36]** Now, we have an array model. We want to set it into the context of a large scene.

**[00:19:40]** How do we do that?

**[00:19:42]** Well, once you have a simulated finite phased array model,

**[00:19:45]** these things can be easily packaged with some automation in the HFSS Toolkit 4,

**[00:19:52]** ready for simulation in wireless channel model simulation.

**[00:19:56]** So we can create an array that's packaged and ready to install into a city model

**[00:20:02]** and simulate its coupling to a collection of subscribers.

**[00:20:05]** We do this by exporting in what we call an embedded element pattern metadata file group.

**[00:20:12]** So when you have an array simulation completed,

**[00:20:17]** you can simply right click on the radiation node in an HFSS project,

**[00:20:21]** select metadata export, and you can export all the data that you need to represent

**[00:20:26]** this complete array for ray tracing or for a downstream channel modeling simulation.

**[00:20:32]** And put it in, literally install it into a location like you see here in this city.

**[00:20:37]** Now, these metadata files will contain a collection of far-field patterns,

**[00:20:43]** one for each port on your antenna.

**[00:20:45]** So if you preserve ports for each polarization feed of each antenna,

**[00:20:49]** you can have this data accessible to you

**[00:20:51]** in the channel simulation.

**[00:20:53]** Now those, the far-fields will have for each element,

**[00:20:57]** they'll be registered to the phase center of each element,

**[00:20:59]** and they will contain the effects of mismatch,

**[00:21:02]** loss characteristics, the mutual and cross coupling impacts,

**[00:21:05]** all the things that you need then when you go on and process this

**[00:21:09]** in a real world situation where you're maybe adding MIMO state vectors

**[00:21:13]** for multi-beam beam steering and so forth.

**[00:21:16]** You've got everything you need baked into this model.


## Slide 17 - appears [00:21:21]

![Slide 17 (shown 00:22:03)](slides/slide_17_00-22-03.png)

**[00:21:21]** Now here's just a sneak preview of some of

**[00:21:23]** the things coming up for those of you who I know,

**[00:21:25]** and to look again to the 6G challenge where we're going to have to engineer

**[00:21:29]** potentially many bands into one radio head, into one antenna unit.

**[00:21:34]** We're going to have to start to leverage some of the new techniques coming up

**[00:21:38]** in leveraging frequency selective surfaces to shield multi-band systems

**[00:21:42]** and construct multi-band systems.

**[00:21:45]** And that unit cell approach that I showed you earlier

**[00:21:48]** can be leveraged to do three-dimensional stacked systems

**[00:21:51]** so that you can lay out very efficient simulations of very complex systems

**[00:21:56]** that may have multiple band, multiple antenna systems involved.

**[00:22:00]** And here's something that you could easily simulate on a laptop computer,

**[00:22:04]** but it's really detailed.

**[00:22:06]** There's a lot going on here.

**[00:22:08]** There's 3D components for the balance for the low band antennas on top,

**[00:22:11]** the antenna designs themselves,

**[00:22:13]** the frequency selective surface is another combination of these components,

**[00:22:17]** and then the high frequency antennas located underneath.

**[00:22:20]** So stay tuned.

**[00:22:21]** We'll have a very great informational webinar coming up by Dr.

**[00:22:26]** Hawal Rashid,

**[00:22:27]** one of my colleagues here at ANSYS on multi-band interleaved and installed

**[00:22:31]** antenna design in HFSS.

**[00:22:33]** And he'll show you how to do some of this multi-band design in HFSS.

**[00:22:37]** Okay.


## Slide 18 - appears [00:22:39]

![Slide 18 (shown 00:22:50)](slides/slide_18_00-22-50.png)

**[00:22:39]** It's time for us to now talk about using these antennas in high fidelity

**[00:22:43]** channel modeling where we introduce motion.

**[00:22:46]** We want the modeling to be done with fidelity.

**[00:22:48]** We want channel soundings to occur very quickly.

**[00:22:51]** You know, every millisecond or less than a millisecond.

**[00:22:55]** How do we do that?


## Slide 19 - appears [00:22:56]

![Slide 19 (shown 00:25:16)](slides/slide_19_00-25-16.png)

**[00:22:57]** What are the electromagnetics going on under the hood to accomplish this?

**[00:23:00]** Well, we're using a technique called shooting and bouncing rays,

**[00:23:04]** and it's an electromagnetic analysis technique for the channel modeling.

**[00:23:08]** And it basically works in maybe a way analogous to how you would test a

**[00:23:13]** device on your high frequency lab bench.

**[00:23:16]** We have a couple of antennas.

**[00:23:18]** We want to model the link between them.

**[00:23:20]** The antennas have a terminal.

**[00:23:21]** The antennas have a terminating impedance.

**[00:23:23]** And we might connect a frequency source or a frequency sweep generator to the

**[00:23:27]** input of one antenna.

**[00:23:29]** And we'll do a ray tracing from our antenna source through the environment

**[00:23:34]** to capture all the bouncing, the, you know,

**[00:23:36]** multi-path and the diffraction and reflections and things that happen in the

**[00:23:40]** environment.

**[00:23:41]** And on the output, we'll sense I and Q voltage samples.

**[00:23:44]** Now, those of you who work in, you know,

**[00:23:47]** high frequency circuit design would recognize this as a forward scattering

**[00:23:50]** parameter.

**[00:23:51]** This is a frequency sensor, or an S21 data sample.

**[00:23:53]** This is what you get with most of your benchtop vector network analyzers.

**[00:23:57]** You drive the frequency sweep and you capture a large number of samples here.

**[00:24:02]** Here's our I and Q samples that show the channel model from input of transmit

**[00:24:07]** antenna to the output of the receive antenna.

**[00:24:10]** It includes the losses through the channel and the delays and the multi-path,

**[00:24:13]** but it's all in the frequency domain.

**[00:24:16]** This is a basis for our channel model, the H matrix.

**[00:24:19]** It's a frequency domain model.

**[00:24:20]** frequency domain model or a complex frequency response model. Now that can be converted and

**[00:24:26]** we see this in our network analyzers when we flip them into the time domain reflectometry mode.

**[00:24:31]** You run this through an IFFT and now you can get the true delay spread. So you can see our

**[00:24:36]** incident wave propagation is usually the first hit and then we have a series of delayed hits

**[00:24:42]** in the time domain that occur because of delayed longer path, right? They're delayed reflections

**[00:24:48]** that take place and go through the environment. That's a complex impulse response. So that's still

**[00:24:52]** complex data. I'm showing you the magnitude here but it's a way of viewing the same thing. What's

**[00:24:58]** the delay spread in the channel? And that can be used to develop a tap delay line model that's

**[00:25:03]** familiar to people who are working with 3GPP channel models except here now is a technique

**[00:25:09]** where you can capture as many taps as you want to in order to derive that model for then applying

**[00:25:15]** perhaps time domain or envelope time envelope convolution.

**[00:25:18]** With your exact transmitted waveform and symbols and things to see what the channel does to them.

**[00:25:24]** Now I just showed you the example of what goes on when I just have one transmitter and one receiver


## Slide 20 - appears [00:25:26]

![Slide 20 (shown 00:26:21)](slides/slide_20_00-26-21.png)

**[00:25:32]** but of course in wireless channel modeling we're interested in wireless channels in complex

**[00:25:36]** environments that involve tens, hundreds, thousands of subscribers talking to access points. So we

**[00:25:44]** want to create complete time varying wireless channel domain models for these complex multi

**[00:25:49]** antennas scenarios. So what we do in the simulation is set up a collection of designated transmitters,

**[00:25:56]** designated receivers or some can swing both ways. They can do transmit and receive and we'll compute

**[00:26:02]** the propagation through the environment, the physics of the interaction, the bounces and so

**[00:26:06]** forth, the physics of the antennas and look at the forward coupling to everything that's a an

**[00:26:11]** associated receive antenna. Then we'll move on to the next antenna and do the same thing to

**[00:26:16]** characterize everybody who can transmit to everybody

**[00:26:19]** that's capable of receiving that transmitter or that we designate as being capable of receiving it.

**[00:26:24]** And then we repeat with motion. So our subscribers will move, we'll have velocity impacts that will

**[00:26:31]** be included in the assessment. The instantaneous velocity is included in the assessment so we can

**[00:26:36]** capture Doppler and we'll capture time varying channels here at whatever cadence you specify you

**[00:26:41]** want them at. If you want them every 50 nanoseconds we'll simulate channel soundings every 50 nanoseconds

**[00:26:48]** and repeat.

**[00:26:49]** Provide back to you a wideband channel characteristic.


## Slide 21 - appears [00:26:52]

![Slide 21 (shown 00:28:03)](slides/slide_21_00-28-03.png)

**[00:26:53]** Now, you might think that takes a while and if you had come to us and asked us to simulate this stuff with the current state of our technology back around 2017 or so, you would have found that it would have taken a few hours to do this.

**[00:27:09]** There's just an example of 177 gigahertz radar. Radar coms are very similar antenna to antenna coupling in the presence of scattering geometry.

**[00:27:17]** Here's an example where we simulated 250 gigahertz.

**[00:27:20]** 256 soundings, this is just a single channel, so it's just a single transmitter, single receiver, but 256 soundings with a bandwidth of 502 megahertz centered at 76.5 gigahertz, and every sounding took 256 frequency samples so that we were simulating a coherent processing interval of 4 milliseconds of real-world time.

**[00:27:43]** Okay, that took us about 14 hours to compute. So going to work on this in R&D, we developed some patented IP to develop algorithms to speed up what we do in shooting and bouncing rays to retain the accuracy of what we do in capturing Doppler and micro Doppler and so forth across a coherent processing frame.

**[00:28:02]** That yielded about a thousand X increase in speed. So we were fast, but one minute is still longer than 4 milliseconds.

**[00:28:10]** We needed it to get faster if we were going to be able to do that.

**[00:28:13]** So we took that solver stack, ripped it back down to the ground basics, and then rewrote it on high-end GPU hardware, and we're able to derive an acceleration of about another 3,000 X over on top of that.

**[00:28:27]** So that today now we're running about 3,000, I'm sorry, about 3 million X faster than we were running back in 2017 when we started this journey.

**[00:28:36]** So this is a combination of algorithmic improvement and, of course, some of the wonderful technology that GPU vendors like NVIDIA have been using.

**[00:28:43]** This one is targeting the higher end NVIDIA, Tesla, and Quadro GPU platforms. And now we're processing these things faster than real time. So to process that frame of data now takes probably for this example, less than a millisecond.

**[00:28:59]** So it's probably about 4 X faster than real time against a pretty busy environment.


## Slide 22 - appears [00:29:04]

![Slide 22 (shown 00:30:22)](slides/slide_22_00-30-22.png)

**[00:29:05]** Well, that leads us to today, now that we're offering a brand new product, this solver product is being offered as a, basically as a library, a software library.

**[00:29:13]** So we're going to look at that now.

**[00:29:14]** that is API accessible. This is a data-on-demand solver. I can't emphasize enough how much data

**[00:29:22]** you create when you're pulling these complex frequency response models and complex impulse

**[00:29:27]** response models out of a channel that you're continually sounding rapidly. And particularly

**[00:29:32]** when you involve multiple access points with 32 to 256 ports against many subscribers in an

**[00:29:41]** accurate environment, you're generating a lot of data. And for that reason, this particular solver

**[00:29:46]** is being provided with API access to literally be a data-on-demand solver, to give you the ability

**[00:29:53]** to get the data that you need rapidly, pull it across a very fast interface, use it, and discard

**[00:30:00]** it. And if you need it back in the future, you can simply reproduce it quickly, probably about as fast

**[00:30:05]** as you probably could read it up and process it and put it in place. So you can do it either way.

**[00:30:11]** You can

**[00:30:11]** save the data for later, reconsumption, or again, just produce it and use it on demand as you need

**[00:30:16]** it. Perceive EM is API driven, and it has or comes included with C++ and Python APIs. And we're

**[00:30:26]** offering it commercially, as well as part of our startup research and education packages. So in

**[00:30:32]** your 2024 R2 updates coming up here shortly, our university and education partners will be able to

**[00:30:40]** access this solver as part of your


## Slide 23 - appears [00:30:41]

![Slide 23 (shown 00:33:02)](slides/slide_23_00-33-02.png)

**[00:30:41]** learning.

**[00:30:41]** This is, again, a new breed of shooting and bouncing race technology. Why is it? How is it different than what's out there today? I'll talk about that in a second. But one of the big things is just the efficiency of this particular solution approach.

**[00:30:56]** You have the ability across the API to set up a particular scenario with multiple actors that have motion.

**[00:31:04]** They have local access coordinate systems that you will propagate through an environment and the environment will be

**[00:31:12]** set up with material properties. You'll bring in your antenna patterns associated with a collection of subscribers, with a collection of access points, registering them in place. The solver is really consuming a list of triangles, mesh triangles with associated material properties.

**[00:31:29]** And then when you kick off a simulation loop, what you're doing is updating the time, position, orientation, and velocity vectors that are associated with anything that moves. Whether it has an antenna or does it have an antenna, could be a target, could be some interactive body that's running in the system.

**[00:31:38]** So it's really a big part of this.

**[00:31:38]** It's really a big part of this.

**[00:31:39]** It's really a big part of this.

**[00:31:39]** ,

**[00:31:40]** ,

**[00:31:40]** ,

**[00:31:41]** ,

**[00:31:41]** ,

**[00:31:41]** ,

**[00:31:42]** ,

**[00:31:42]** , ,,

**[00:31:42]** out there and you can have rotational velocity and translational velocity so we can capture things

**[00:31:49]** like micro doppler for things that are spinning or turning in addition to doppler signatures from

**[00:31:55]** things that have translational and a combination of the two now i also want to stress that this

**[00:32:01]** solver is capable of processing and consuming very high fidelity data and you'll see some examples

**[00:32:08]** here but scenes that may have millions of facets that you use to represent the environment

**[00:32:14]** and the bodies and that's a real trick under the hood for ray tracing tools i'll talk more about

**[00:32:20]** that in a few minutes now this is versatile you can scale this thing across multiple gpus if

**[00:32:25]** you've got a dual or up to eight gpus on a particular platform you can get a corresponding

**[00:32:32]** linear in some cases super linear increase in performance or reduction in speed

**[00:32:38]** a root i'm sorry reduction in time for simulation just by scaling it across multiple gpus and our

**[00:32:45]** friends at super micro have a box that's certified for this solver but with this solution approach

**[00:32:51]** you can handle millions of wireless channels i mean on one gpu we've simulated over 25 million

**[00:32:57]** in one simulation with one gpu and you can further speed it up that one didn't quite process at real

**[00:33:03]** time because of the sheer number of channels but when you spread this out across multiple gpus

**[00:33:08]** you can get there now you can use this solver engine to integrate i don't want to stress this

**[00:33:14]** it's designed to be integrated into your own workflow so if you have an orchestration

**[00:33:19]** environment you have some way of orchestrating environments you've already built something

**[00:33:23]** that does motion through some kind of a structural structured environment and you just want a solver

**[00:33:29]** that does the antenna couplings that does the channel modeling this is the tool for you now

**[00:33:34]** i'll also illustrate workflows that have been put together to make that entire process um easier for

**[00:33:39]** you that leverage this simulation engine as well now up until we were beginning to work in fr2 bands


## Slide 24 - appears [00:33:42]

![Slide 24 (shown 00:34:58)](slides/slide_24_00-34-58.png)

**[00:33:48]** a lot of the work we were doing in channel modeling and particularly ray tracing we're leveraging

**[00:33:53]** fairly simple models of our cities and you can see an open street maps model which is nice it's a

**[00:33:58]** it's a reasonable way to model um cities and they're usually you know processed and simplified

**[00:34:03]** models so that we can capture diffraction or do diffraction coefficient chaining from rooftop to

**[00:34:08]** rooftop to get from source to destination

**[00:34:11]** and that worked okay at lower frequencies but as we begin to push to higher frequencies

**[00:34:16]** we want to capture more of the interaction in finer details of a particular city and here's

**[00:34:22]** an example of a five five centimeter resolution city model that comes from one of our partners at

**[00:34:27]** aerometrics this model is about four and a half by four and a half kilometers of downtown denver

**[00:34:32]** colorado consists of about 10 million geometry facets and we consume those facets at speed

**[00:34:39]** now you can see photogrammetry

**[00:34:40]** overlay so the pictures are pretty and you can see real features as it appears visually

**[00:34:45]** but i want to emphasize under that are structural facets that capture the balconies the doorways the

**[00:34:53]** windows okay so the detail is truly in that model it's not just in the pretty pictures

**[00:34:58]** or in the optical overlay and as we go to fr3 bands we're going to want even better fidelity

**[00:35:05]** right we're going to millimeter wave or terahertz frequency simulations here's an example of a

**[00:35:10]** 2 centimeter resolution area model where we've got a very high frequency access point model stuck up here. You kind of see a radiation pattern put up there under the balcony or under that overhang.

**[00:35:21]** That is a structural model with a visual overlay put on top of the facets as introduced as a texture.

**[00:35:28]** But all of that detail can be there, and this is a solver methodology that can swallow that without having to pre-process those things into simplified edges and simplified large surface areas.


## Slide 25 - appears [00:35:43]

![Slide 25 (shown 00:37:51)](slides/slide_25_00-37-51.png)

**[00:35:43]** Now, what's going on under the hood? I don't want to grind through too much of this, but it is important to note that this is not the same ray tracer that maybe many of you are familiar with.

**[00:35:53]** We're using not a geometric optics or general theory of diffraction solver.

**[00:35:59]** But rather, we're based on something called physical optics. Now, the term shooting and bouncing rays is used to cover a lot of different techniques. So, when you hear that, it's not necessarily unique, but the technique or the framework on which it's built is what's important.

**[00:36:14]** And we're moving a little bit of a different direction than the industry here. We're using physical optics. And physical optics is a preferred approach for people doing very detailed radar signature work.

**[00:36:25]** So, when you need really accurate scattering off of something that's very detailed,

**[00:36:29]** that might have a fairly low scattering coefficient. PO is a great way to do that because you're capturing interaction of all the structure,

**[00:36:36]** not just looking for only a specular reflection point location off of a surface plus maybe an edge diffraction.

**[00:36:44]** Classically, physical optics is single bounce. We think of it as, you know, using it for things like reflector designs and stuff where we have an illumination model, like a feed horn, and we just look at the one bounce off of the reflector.

**[00:36:57]** But we have enhanced that through a lot of different techniques.

**[00:36:59]** So, we are using geometric optics, ray tracing to create more physical optics basis functions. I'll talk about what that is in a second. Furthermore, we do enhance, we overload PO with some additional diffraction physics where it's needed.

**[00:37:15]** But the big idea here is that a PO based framework transports fields through wave propagation methods, not purely through ray tracing abstractions.

**[00:37:26]** And in that way is something's very valid.

**[00:37:28]** It's very good in near field situations where you have spherical spreading from things coming back to you for which a specular path doesn't necessarily show up in ray tracing.

**[00:37:41]** Now, one of the downsides of PO is that it's thought to be somewhat slower than pure pure play geo ray tracing, unless you apply some special treatment and acceleration, which is exactly what we're doing here.


## Slide 26 - appears [00:37:53]

![Slide 26 (shown 00:39:03)](slides/slide_26_00-39-03.png)

**[00:37:53]** So, let me illustrate sort of, I'll be a little bit simplistic here, but illustrate what, what's, what's going on here.

**[00:37:58]** So, let me illustrate sort of, I'll be a little bit simplistic here, but illustrate what, what's going on here.

**[00:37:59]** So, let me illustrate sort of, I'll be a little bit simplistic here, but illustrate what, what's going on here.

**[00:37:59]** So, let me illustrate sort of, I'll be a little bit simplistic here, but illustrate what, what's going on here.

**[00:37:59]** Now, in the case of PURE PAY geo ray tracing does with a pure geo GTD methodology, you're looking for ray paths that either hit specular provide reflection points off of surfaces that take you from source to destination from transmitter to receiver.

**[00:38:15]** Or we get the direct line of sight shown by the green ray, the green ray reaches the receiver or we look for the rays that come to edges that create then edge diffraction sources, which then make their way to the receiver, right?

**[00:38:28]** So here you can see it.

**[00:38:29]** The reflection path makes its way to the receiver.

**[00:38:31]** Here's a diffraction path that makes its way to the receiver.

**[00:38:35]** And you might also go to a ray depth of two or three to capture additional specular paths that get you to the receiver.

**[00:38:42]** Now, these are all abstractions.

**[00:38:43]** They're assuming that there's an amount of energy carried by each unique ray, which isn't necessarily physically related to the area of what it's hitting.

**[00:38:51]** It's just a ray carrying a certain amount of energy with a certain delay, and you get energy collected by summing up the contributions along each of these rays, and then you get phasor contributions to understand the delays.


## Slide 27 - appears [00:39:06]

![Slide 27 (shown 00:40:21)](slides/slide_27_00-40-21.png)

**[00:39:06]** Now, let's talk about the PEO methodology.

**[00:39:09]** This is a little bit different.

**[00:39:10]** We start with ray tracing.

**[00:39:12]** We're actually indiscriminately spraying.

**[00:39:14]** This is not a goal-driven process.

**[00:39:15]** We'll spray hundreds of thousands of rays around the environment, and we're looking for rays that hit geometry at all.

**[00:39:22]** And any rays that hit geometry will put a current.

**[00:39:25]** They'll induce an equivalent surface current at that location that satisfies Maxwell's equations for the ray that reflects off of that surface or might partially reflect and transmit, and then if it transmits, we'll continue ray track processing through that.

**[00:39:42]** But you'll get these equivalent surfaces that give rise to what happens to that ray as it reflects, and they include the polarization shift of the energy.

**[00:39:50]** Now, that energy will re-reflect.

**[00:39:52]** And we'll continue specular ray tracing to try to find out where else do we hit things, and maybe a secondary bounce will induce another current on a second bounce surface that it impacts.

**[00:40:05]** We'll also do the same thing with some of the edge currents as well, the diffraction that shows up and comes out in induced currents along the edges.

**[00:40:14]** But once you have all these equivalent surface currents impressed to the environment, then we switch into the Green's function mode to propagate

**[00:40:22]** the radiated contributions from all of these currents to the receiver. We sum them up. That's the wave behavior.

**[00:40:29]** And we've put that against the incident wave that's transmitted directly between the two, sum them up, and now you've got the contributions of scattering from everything in that environment. Now you have a reduced importance of a single ray.

**[00:40:44]** You have a reduced importance or reduced significance here on how clean the geometry is that you're capturing.

**[00:40:52]** And you have this ability, because it's not a goal-driven process, you can handle a large number of facets efficiently, and this parallelizes very well.

**[00:41:01]** So, again, SBRPO methodology.

**[00:41:05]** Here are a couple of examples of the perceived EM solver in action. So we've got a collection of subscribers. These two examples are really just driven by a Python script.


## Slide 28 - appears [00:41:13]

![Slide 28 (shown 00:42:35)](slides/slide_28_00-42-35.png)

**[00:41:17]** So we have scripts with parametric objects that can move.

**[00:41:21]** We've got a Python script.

**[00:41:22]** So we have scripts with parametric objects that can move.

**[00:41:22]** We've got a Python script.

**[00:41:22]** We've got a Python script.

**[00:41:22]** We've got a Python description of how these objects all move. Many of them have antennas. Some of them have radars. We have a quadcopter flying on the right side with a 77 gigahertz radar, while at the same time we're simulating updated channel conditions for a C-band radio mounted on that quadcopter and communicating with each element of a phased array access point, like a 5G node B antenna system.

**[00:41:46]** And then each block of this is actually frequency time data showing you the bandwidth of the channel versus the frequency time data.

**[00:41:53]** You know, over perhaps a hundred successive soundings or each element in the array.

**[00:41:58]** Just a way to quickly.

**[00:41:59]** Visualize and depict how the channel conditions are changing as this guy flies through the environment.

**[00:42:05]** Now, again, IQ data for every channel coupling.

**[00:42:09]** This scene may have hundreds of antennas,

**[00:42:12]** each of which are moving at different rates,

**[00:42:14]** attached to subscribers.

**[00:42:15]** The may be independent.

**[00:42:16]** And we can have the motion of other actors in the scene that are interacting electromagneticly with anything.

**[00:42:22]** that's going on in this simulation.

**[00:42:25]** And yes, this is a processed,

**[00:42:27]** updated range Doppler plot here.

**[00:42:29]** So here's range on the vertical axis,

**[00:42:31]** Doppler on the horizontal axis

**[00:42:33]** as registered by a millimeter wave radar

**[00:42:35]** that's mounted on this quadcopter

**[00:42:37]** as it flies through the city.


## Slide 29 - appears [00:42:39]

![Slide 29 (shown 00:42:56)](slides/slide_29_00-42-56.png)

**[00:42:41]** Now, because this is an adaptable solver

**[00:42:44]** that can be plugged into existing workflows,

**[00:42:47]** we've been looking for leading workflows

**[00:42:50]** to integrate this into.

**[00:42:51]** And this leads us to some of the great work

**[00:42:54]** that's going on now between NVIDIA and ANSYS,

**[00:42:57]** where we're looking to building a new era

**[00:42:58]** of computer data engineering

**[00:43:00]** through accelerated computing and generative AI.

**[00:43:03]** And in particular, I'm gonna talk about this area

**[00:43:06]** of transforming 6G research with Perseverium

**[00:43:08]** integrated into the NVIDIA Omniverse.

**[00:43:12]** And earlier this year at NVIDIA's GTC conference,


## Slide 30 - appears [00:43:13]

![Slide 30 (shown 00:45:11)](slides/slide_30_00-45-11.png)

**[00:43:15]** we unveiled and announced the integration or a connector

**[00:43:19]** from the Omniverse Universal Scene Descriptor environment

**[00:43:24]** to the Perseverium solver so that you can create these,

**[00:43:28]** obviously Omniverse has this very powerful ability

**[00:43:31]** to model scenes, to construct both outdoor

**[00:43:34]** and indoor environments, and to process motion

**[00:43:38]** and detail and photogrammetry,

**[00:43:40]** very realistic appearance here,

**[00:43:43]** and contain the physical properties in the USD information.

**[00:43:48]** You can actually carry material properties in a layer of USD.

**[00:43:52]** So we integrated that.

**[00:43:54]** We've integrated this solver into that world,

**[00:43:57]** and you can see here a car with a 77 gigahertz radar

**[00:44:00]** showing processed range Doppler information.

**[00:44:02]** Horizontal axis is Doppler, vertical axis is range

**[00:44:06]** as this car drives through the environment.

**[00:44:10]** Now, as this car drives, it'll also have wireless connectivity

**[00:44:13]** to the 5G system at three and a half gigahertz.

**[00:44:16]** So you can see our connectivity for a mobile subscriber

**[00:44:20]** also being processed at the same time to do connectivity

**[00:44:24]** to multi-element, multi-channel systems.

**[00:44:26]** On the right, you can see an example of a demo.

**[00:44:29]** If some of you saw us at International Microwave Symposium

**[00:44:32]** or the Hanover MESS Conference, or maybe at DAC this week,

**[00:44:36]** there's a joystick demo.

**[00:44:38]** You can walk up and actually drive this little robot

**[00:44:40]** through an Omniverse model of this warehouse.

**[00:44:43]** And as it's driving, we're processing radar reflections

**[00:44:46]** on a millimeter wave radar.

**[00:44:48]** I don't know if this is 60 gigahertz or 77,

**[00:44:50]** but we're interactively processing range angle information.

**[00:44:53]** So you can see what that radar is actually recording.

**[00:44:56]** And with the joystick, since you can drive it, right,

**[00:44:59]** we don't compute this data a priori.

**[00:45:01]** We're generating the data as we need it,

**[00:45:03]** depending on where the user drives the robot

**[00:45:05]** and doing it at real time.

**[00:45:07]** So this is just an example of some of the things

**[00:45:10]** that can be done and some of the stacks that you can build.


## Slide 31 - appears [00:45:13]

![Slide 31 (shown 00:45:50)](slides/slide_31_00-45-50.png)

**[00:45:14]** Now, if you can model indoor environments,

**[00:45:17]** of course, access point modeling and modeling heat maps

**[00:45:20]** is very popular.

**[00:45:21]** And if you can do a heat map,

**[00:45:23]** if you can generate this data quickly enough,

**[00:45:26]** why not do a 3D volumetric heat map

**[00:45:30]** to look at access coverage?

**[00:45:32]** So here's an example where we have an access point

**[00:45:34]** up in the ceiling,

**[00:45:35]** somewhere near the middle of this warehouse.

**[00:45:36]** And we quickly evaluate and sweep through the coverage

**[00:45:40]** throughout the volume of this large indoor environment.

**[00:45:43]** And you can characterize that over very wide bandwidths.

**[00:45:47]** So another real powerful aspect

**[00:45:49]** of what this kind of system enables

**[00:45:51]** from the design of warehouses,

**[00:45:53]** we've seen NVIDIA demonstrated on the Omniverse environment

**[00:45:57]** to the assessment of the wireless performance

**[00:45:59]** of a collection of antenna systems within.


## Slide 32 - appears [00:46:01]

![Slide 32 (shown 00:46:49)](slides/slide_32_00-46-49.png)

**[00:46:03]** Now that brings us to the present.

**[00:46:05]** Also at GTC, we announced the start of a collaboration

**[00:46:11]** where we're integrating our wireless channel modeling engine

**[00:46:15]** into the emerging NVIDIA Aerial Omniverse Digital Twin

**[00:46:19]** or AODT 6G research platform.

**[00:46:23]** Now look this up,

**[00:46:25]** NVIDIA is developing a really interesting

**[00:46:28]** and compelling development platform

**[00:46:30]** to simulate complete layer one.

**[00:46:33]** And eventually I think layer two,

**[00:46:35]** physical layer models for complete network lay downs

**[00:46:39]** and multi-access points, multi-subscribers,

**[00:46:42]** but it's a platform that's also enabled for AI

**[00:46:45]** so that you can begin to evaluate AI approaches

**[00:46:49]** to waveform tuning, to channel modeling, to channel prediction,

**[00:46:53]** to channel estimation,

**[00:46:54]** all of the things that channel researchers are doing

**[00:46:59]** in this area of integrating AI.

**[00:47:02]** This'll be a wonderful sort of self-contained platform

**[00:47:06]** that researchers will be able to subscribe to and access.

**[00:47:10]** And for CVM, we'll be a driver

**[00:47:12]** to the underlying channel models that make this go

**[00:47:15]** so that you can evaluate networks indoor,

**[00:47:18]** networks outdoor, and combinations of networks

**[00:47:21]** at really any frequency of interest,

**[00:47:23]** any bandwidth of interest,

**[00:47:24]** any kind of antenna designs of interest

**[00:47:27]** that you want to evaluate,

**[00:47:28]** including really creative

**[00:47:30]** distributed antenna system concepts.


## Slide 33 - appears [00:47:33]

![Slide 33 (shown 00:48:15)](slides/slide_33_00-48-15.png)

**[00:47:34]** This is just one example.

**[00:47:35]** We wanted to bring along a kind of a proof of concept

**[00:47:38]** that we put together in our collaboration with the AODT.

**[00:47:42]** This is a channel predictor system

**[00:47:45]** that where we're leveraging AI to train an AI algorithm

**[00:47:48]** to, for example, for a high velocity subscriber

**[00:47:51]** to predict channel aging

**[00:47:53]** across the time slots.

**[00:47:55]** And so this is training a neural network

**[00:47:58]** to predict future channels to address channel aging.

**[00:48:02]** And we're going to evaluate

**[00:48:04]** our neural network model performance

**[00:48:07]** against the classical methods that we've been using

**[00:48:10]** for predicting channel modeling.

**[00:48:12]** So the objective here is to be able to take

**[00:48:15]** a couple of channel samples or a couple of time slot samples

**[00:48:18]** and predict what the performance will be

**[00:48:20]** or what the channel will look like

**[00:48:21]** in successive channel slots.


## Slide 34 - appears [00:48:23]

![Slide 34 (shown 00:49:21)](slides/slide_34_00-49-21.png)

**[00:48:23]** So here's just an example.

**[00:48:25]** You're looking at the complex impulse responses

**[00:48:28]** as they come out of the perceived EM solver

**[00:48:31]** in a situation where we're dropping our UE

**[00:48:34]** or our mobile user into many different locations

**[00:48:37]** with a prescribed high velocity.

**[00:48:39]** And then you can see how well

**[00:48:41]** or the error that's showing up here

**[00:48:43]** with a kind of a conventional channel predictor

**[00:48:47]** versus the performance of the AI model

**[00:48:49]** that's being trained.

**[00:48:51]** You're looking at relative error levels here.

**[00:48:53]** So,

**[00:48:53]** and you can see after a number of samples,

**[00:48:55]** the error drops down very nicely.

**[00:48:58]** And it looks like this particular AI

**[00:49:00]** for channel prediction for this particular bespoke location

**[00:49:04]** will have great utility.

**[00:49:06]** So this is just one of many ways

**[00:49:08]** that we anticipate customers being able

**[00:49:10]** to take these married technologies and use them.

**[00:49:14]** And for anyone doing channel modeling research,

**[00:49:16]** I encourage you to take a look at the NVIDIA AODT platform

**[00:49:20]** for some very creative research capabilities.

**[00:49:22]** Now, we recognize that not everyone has their own channel modeling


## Slide 35 - appears [00:49:25]

![Slide 35 (shown 00:49:35)](slides/slide_35_00-49-35.png)

**[00:49:31]** or environment modeling capability.

**[00:49:33]** And I'd like to highlight a channel modeling solution

**[00:49:36]** that ANSYS has put together called RF Channel Modeler,

**[00:49:39]** which is an automated solution for wireless channel modeling

**[00:49:42]** in dynamic bespoke outdoor locations.

**[00:49:45]** This is serving the situation where you may say,


## Slide 36 - appears [00:49:46]

![Slide 36 (shown 00:50:05)](slides/slide_36_00-50-05.png)

**[00:49:48]** I have a city I am interested in laying down a network concept in.

**[00:49:53]** Just give me, please, a network concept.

**[00:49:54]** Please, the model for the city with all the tiles,

**[00:49:58]** the facet models, and so forth.

**[00:50:01]** I have my high resolution virtual antenna models or array models.

**[00:50:05]** I want to put them into this location, populate them,

**[00:50:08]** and then I'm going to define the subscriber

**[00:50:10]** or the access point motion so that they move.

**[00:50:12]** And I want a workflow that does this for me

**[00:50:14]** so that I can test my waveform performance,

**[00:50:17]** generate channel models that are time indexed

**[00:50:20]** for a large collection of radios

**[00:50:22]** that I'm going to put in that scene.


## Slide 37 - appears [00:50:24]

![Slide 37 (shown 00:50:54)](slides/slide_37_00-50-54.png)

**[00:50:24]** Well, that is using,

**[00:50:26]** the RF Channel Modeler is using perCVM under the hood,

**[00:50:30]** as you can see here,

**[00:50:31]** but it is a workflow that collects these models of a city,

**[00:50:36]** models of subscriber motion, models of antennas,

**[00:50:39]** and lets you, interactive graphical environment

**[00:50:42]** to place them and put them.

**[00:50:44]** And then we'll dynamically time synchronize their motion.

**[00:50:48]** And these motions can be for things on the ground,

**[00:50:50]** things in the air, things on the water, whatever you have.

**[00:50:54]** And we'll generate these channel models

**[00:50:56]** that then can be stored down and used

**[00:50:58]** for downstream processing

**[00:51:00]** against your digital signal processing stacks.

**[00:51:04]** Now, an example of the RF Channel Modeler in motion

**[00:51:07]** is like this for our Denver scene,


## Slide 38 - appears [00:51:08]

![Slide 38 (shown 00:51:31)](slides/slide_38_00-51-31.png)

**[00:51:08]** where we have a collection of three access points

**[00:51:12]** mounted on buildings.

**[00:51:13]** There are three 32 port, 32R, 32T base station models,

**[00:51:19]** and a couple of subscribers

**[00:51:20]** that are driving through this city,

**[00:51:22]** and they're continuously connected.

**[00:51:24]** Much of the time, they do not have line of sight visibility,

**[00:51:27]** but we want to model at, for example, 3.5 gigahertz,

**[00:51:31]** what their connectivity is going to look like


## Slide 39 - appears [00:51:33]

![Slide 39 (shown 00:52:38)](slides/slide_39_00-52-38.png)

**[00:51:33]** and how it varies over time.

**[00:51:37]** Now, where do I get a city model?

**[00:51:38]** One of the nice things

**[00:51:39]** about this particular modeling environment

**[00:51:41]** is that it is connected directly to the Cesium facility.

**[00:51:46]** If you go to cesium.com,

**[00:51:47]** you can register for a free account,

**[00:51:48]** but they're creating a kind of an industry standard

**[00:51:50]** for handling 3D tile content

**[00:51:53]** to represent a city model.

**[00:51:55]** So, you can get 3D tile content,

**[00:51:57]** terrain, buildings, cities,

**[00:52:00]** and you've got a number of vendors

**[00:52:01]** who are supplying these tile sets to Cesium.

**[00:52:04]** Many of those are directly accessible free of charge.

**[00:52:07]** If you just log on and get a free account,

**[00:52:09]** and then there are also available paid content,

**[00:52:11]** tile sets that you can also get.

**[00:52:13]** But it's a great place for you to shop tile sets

**[00:52:16]** for various cities and try it out, connect it.

**[00:52:19]** And you can connect your RF Channel Modeler

**[00:52:21]** directly to your account on Cesium,

**[00:52:23]** and Cesium will stream your 3D tiles, directly to your computer,

**[00:52:25]** if you want to use it that way to do your simulation.

**[00:52:30]** So, you don't actually have to pull the tiles

**[00:52:31]** down to your own computer.

**[00:52:35]** And by the way, Cesium is a partner with NVIDIA.

**[00:52:38]** So, you can access them

**[00:52:40]** through Omniverse Connectivity as well.


## Slide 40 - appears [00:52:42]

![Slide 40 (shown 00:53:20)](slides/slide_40_00-53-20.png)

**[00:52:43]** Now, coming back to my connectivity example here

**[00:52:46]** to model, for example,

**[00:52:47]** uplink propagation from each of our subscribers

**[00:52:49]** as they drive through the city,

**[00:52:51]** you can see here that one mobility subscriber

**[00:52:55]** connecting to it,

**[00:52:56]** one of the 32 channels,

**[00:52:57]** the channels of one of the arrays,

**[00:52:59]** you can see the frequency response

**[00:53:01]** and the corresponding time response, right?

**[00:53:04]** So, you can see complex frequency,

**[00:53:05]** complex time domain response.

**[00:53:06]** We sampled those channels every 10 milliseconds,

**[00:53:09]** but the update on the screen is going every 100 milliseconds,

**[00:53:11]** just so that the plots are viewable.

**[00:53:14]** But this simulation with two subscribers

**[00:53:17]** against three full base stations

**[00:53:18]** was running about 2.6X faster than real time here,

**[00:53:22]** simulating 100 megahertz with 1,024 frequency samples

**[00:53:26]** over two minutes of scenario time.

**[00:53:30]** And it was like a total of 196 or 192 channels simulated.


## Slide 41 - appears [00:53:36]

![Slide 41 (shown 00:54:10)](slides/slide_41_00-54-10.png)

**[00:53:36]** This also works for air subscribers as well.

**[00:53:39]** So, things that are flying

**[00:53:40]** will probably see a more detailed time response.

**[00:53:43]** You see a lot more reflections

**[00:53:44]** because of all the building faces that are exposed

**[00:53:47]** and other features, ground bounce features,

**[00:53:49]** and things that get into the mix.

**[00:53:51]** So, your channel selectivity over the scenario,

**[00:53:54]** here this is across the band and across scenario time,

**[00:53:57]** becomes a great deal more varied,

**[00:53:59]** as well as the time domain response

**[00:54:00]** where you see the incident wave hit first.

**[00:54:03]** So, this is delay on the vertical axis versus scenario time.

**[00:54:06]** And this becomes really interesting

**[00:54:08]** as different features cover and uncover

**[00:54:11]** in the time domain response of the system.


## Slide 42 - appears [00:54:16]

![Slide 42 (shown 00:54:27)](slides/slide_42_00-54-27.png)

**[00:54:16]** This works as well at millimeter wave.

**[00:54:19]** Here's a 256 port or 128 port.

**[00:54:23]** It's a dual polarized 64 element array at 28 gigahertz.

**[00:54:27]** Communicating now with a two centimeter accurate description

**[00:54:32]** of the area around the Denver train station.

**[00:54:35]** And as our subscriber walks across the platform,


## Slide 43 - appears [00:54:36]

![Slide 43 (shown 00:55:14)](slides/slide_43_00-55-14.png)

**[00:54:39]** you can see here the across 400 megahertz of bandwidth.

**[00:54:43]** Now at 28 gigahertz, there's a great deal

**[00:54:45]** of channel selectivity in the frequency domain.

**[00:54:48]** And in the time domain, you can see different reflections,

**[00:54:51]** delayed reflections and diffraction hits in the time domain,

**[00:54:55]** which all become a part of that channel.

**[00:54:57]** And you can see these kind of diagonal bars,

**[00:55:00]** sort of diagonal characteristics that show up across the band

**[00:55:04]** at different times in the scenario

**[00:55:06]** that reflect the multi-path, strong multi-path interaction

**[00:55:09]** that leads to very frequency

**[00:55:12]** selective channel characteristics.

**[00:55:16]** Now, we don't have time today to cover it,

**[00:55:19]** but if some of you are interested, contact me offline.

**[00:55:22]** I've got an example of a C-band massive multi-user,


## Slide 44 - appears [00:55:23]

![Slide 44 (shown 00:55:29)](slides/slide_44_00-55-29.png)

**[00:55:27]** massive MIMO uplink.

**[00:55:28]** It's a very interesting study here.


## Slide 45 - appears [00:55:31]

![Slide 45 (shown 00:55:53)](slides/slide_45_00-55-53.png)

**[00:55:31]** And maybe I'll just quickly run through these things.

**[00:55:33]** We can take a channel model for the couplings,

**[00:55:37]** for everything that we model.

**[00:55:38]** And of course, apply it to those of you who do channel modeling studies,

**[00:55:42]** know very well the singular value decomposition method

**[00:55:45]** to decompose the number of channels that exist

**[00:55:49]** through which you can pipe energy to your subscriber.

**[00:55:52]** I mean, there are multiple solutions, orthogonal solutions that exist.

**[00:55:57]** And I just wanted to demonstrate that this channel model can be used to decompose.

**[00:55:57]** And I just wanted to demonstrate that this channel modeling characteristic can be used,

**[00:56:00]** or this channel modeling method can be used to pull apart the eigen channels

**[00:56:04]** so that you could look at how many eigen channels exist

**[00:56:08]** for a given array to subscriber link, like an uplink.

**[00:56:12]** And what are the beam steering vectors that correspond to develop that pattern?


## Slide 46 - appears [00:56:16]

![Slide 46 (shown 00:56:25)](slides/slide_46_00-56-25.png)

**[00:56:17]** And so I did it for a subscriber driving through this scene, marching through.

**[00:56:22]** And most of the way, this subscriber does not have line of sight visibility to the array.

**[00:56:27]** Very quickly, there's the array model, two ports on every array, so, or every array element.


## Slide 47 - appears [00:56:28]

![Slide 47 (shown 00:56:38)](slides/slide_47_00-56-38.png)

**[00:56:33]** So this has a total of 32 ports, right?

**[00:56:36]** So potentially it's a, you know, a 32R32T kind of MIMO that's going on.


## Slide 48 - appears [00:56:42]

![Slide 48 (shown 00:56:45)](slides/slide_48_00-56-45.png)

**[00:56:42]** And we have an installed pattern for our subscriber as it's driving through the environment.


## Slide 49 - appears [00:56:47]

![Slide 49 (shown 00:56:55)](slides/slide_49_00-56-55.png)

**[00:56:47]** We're capturing our H matrix at a number of times, and then add, I'll present the pattern

**[00:56:54]** for the solution at a particular time at 200 seconds

**[00:56:58]** and then we'll see how it goes.


## Slide 50 - appears [00:56:59]

![Slide 50 (shown 00:57:19)](slides/slide_50_00-57-19.png)

**[00:56:59]** So this is a measure, this is just showing you all of the eigen channels that exist

**[00:57:04]** that carry at least 10% of the total power in terms of the number of orthogonal solutions

**[00:57:11]** that exist for the channel from this subscriber to the array.

**[00:57:14]** Now, MIMO is a kind of a process of choosing a particular orthogonal solution

**[00:57:18]** to sort of send energy spatially, right, and to direct it out.


## Slide 51 - appears [00:57:23]

![Slide 51 (shown 00:57:39)](slides/slide_51_00-57-39.png)

**[00:57:23]** This is actually assessed over the entire bandwidth, 100 megahertz of the bandwidth,

**[00:57:27]** but you could continue.

**[00:57:28]** You could strain this to a narrower bandwidth to look at something at a particular subcarrier,

**[00:57:33]** but you can see it at the beginning of the scene, there's only about maybe one to three

**[00:57:37]** eigen channels that carry at least 10% of the total power.

**[00:57:41]** And then when he gets closer to the array, of course, that rises because of the growing

**[00:57:44]** number of multipath capabilities to as many as 10 MIMO layers that would potentially exist.


## Slide 52 - appears [00:57:51]

![Slide 52 (shown 00:58:11)](slides/slide_52_00-58-11.png)

**[00:57:51]** And then you could look at these eigenvectors for, let's say, the top four eigen channels

**[00:57:57]** and look at.

**[00:57:58]** And then you can see the state vector be applying across the ports of the array at the center

**[00:58:03]** frequency, at the center carrier, 3.85 gigahertz.

**[00:58:07]** You can throw that back against your HFSS antenna model and evaluate the patterns that

**[00:58:12]** would feed into that particular eigen channel.

**[00:58:15]** So just some interesting things, some food for thought, because you can pull apart these

**[00:58:19]** channel models and use them in very detailed MIMO research to evaluate MIMO layer characteristics.


## Slide 53 - appears [00:58:25]

![Slide 53 (shown 00:59:11)](slides/slide_53_00-59-11.png)

**[00:58:27]** That brings us to the end here.

**[00:58:28]** I appreciate your patience in listening to me talk at times probably too quickly, but

**[00:58:34]** as always, lots of information.

**[00:58:35]** But here are the high points that I want to hit.

**[00:58:38]** Speed and fidelity for dynamic wireless channel modeling in bespoke virtual locations is now

**[00:58:44]** a reality.

**[00:58:45]** And it's enabled through this radar or wireless channel modeling data-on-demand solver.

**[00:58:51]** So this is something you can plug into your modeling solution if you already have a way

**[00:58:55]** that you're orchestrating and programming.

**[00:58:57]** Thank you.

**[00:58:58]** prosecuting scenarios this is a solver that you should be able to fit in with a c plus plus or

**[00:59:04]** a python based api wireless physical layer modeling file layer modeling is now possible

**[00:59:10]** with real-time speed and with specific location-based fidelity and i point to the nvidia

**[00:59:16]** aodt platform married to perceive em is a great example for that for indoor wireless challenges

**[00:59:23]** as well as some outdoor right or the ansys rf channel modeler with perceivm integrated inside

**[00:59:29]** of it right that can be available and and very useful again even for digital twins of networks

**[00:59:34]** like what happens to my base station when someone's going to put a construction crane in

**[00:59:39]** across the street what will the performance be for the various beams or for the mimo mimo performance

**[00:59:45]** uh you know being able to evaluate things like that to be able to perhaps deliver reprogramming

**[00:59:52]** to the signal processing system or to the signal processing system or to the signal processing

**[00:59:53]** system you can evaluate these things in advance before we get started


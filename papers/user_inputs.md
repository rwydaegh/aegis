# User inputs from this conversation

Source: `/home/user/.claude/projects/-home-user-aegis/7dc0a8d1-a738-4624-b078-12ee5dfb94e1.jsonl`

Total messages: 16

---

## Message 1

validation/
theory/

Focus on the monograph, read that in full. Make 3 high-impact IEEE papers in something like TAP or TWC. They may be overlapping. This is just so you produce several papers and I get to pick the best angles afterwards. Objvously they cant cover the whole scope. It's too huge. 

theory/system_formalism.tex
theory/psSAR10g.tex
theory/section_below6ghz.tex
theory/q_complement.tex
these are kinda like additions. Theyre the latests thought. Your call if you feel they are important or a better way to frame it.

The monograph will not just go on arxiv. You have to derive things properly as if the reader doesnt ahve this context (duh). 

Only once you start working on the tex file, do read
papers/how_to_write_good/ai_writing.md
papers/how_to_write_good/elos.md
papers/how_to_write_good/style_analysis.md
papers/how_to_write_good/style_guide.md
these are for when u write in the monograph, not the paper. So sometime you can take with a grain of salt (be smart about when to follow the rules). Most of the time you should follow the general ruules, especially about the dryness and not being like an AI. Keep everything crystal clear and simple, on a microscopic and high level. Build things nicely.

This is a big task. Impress me. We are starting an endavour. It's not just a draft. The monograph is based on 
theory/figures
theory/scripts

btw the backlfip probably has an error cuz I think the variability is suspiciously low. so dont quote that. 

The scripts may not be plug and play yet btw. They were copied over from another system where they were. Lmk if u need anything.

I understand there is a whole codebase around the theory, but that isnt the focus. Dont go 'we developed this super deluxe codebase sooo many LoC'. No. You can mention it, but think about how you usually approach this, and how constrained you are with the imposed writing style. 

One big hurdle will be to balance the size of the methods section with a probably rather small results section. Not sure what to do there. Think about that.

This is not a one shot. You may wanna brainstorm in one or md files, or even do some scripts if you want (altho you can use aegis code). But don't get tooo carried away by eg building more features or simulating giant things.

---

## Message 2

Carefully write three md files with a rough non-styled spine of these papers, more or less. What are the relevant files to read in each. What are relevant figures to read or try to tweak? Then, also be adversial to yourself: how can we improve the spine, what would reviewers say? Think on a high level still without getting into the details. Writing will actually be relevately easy. The difficult part is planning IMO.

---

## Message 3

1. Well, that's why we have validation/. It caompared with GOLIAT simulations. read the md files. or validation/fig_kernels_vs_fdtd.png which converges well to 1.0 at 6 GHz and beyond. The md look pessimistic about the 1/2 factor but I think that's somehow a bug with the way we set up our simulations in sim4life (absorbed vs incident power maybe? idk).
2. I added 
papers/zhang.pdf
papers/Flintoft_2014_Phys._Med._Biol._59_3297.pdf
papers/A formula for human average whole-body SAR .pdf
although you have to be VERY careful in just reading zhang.pdf since it is a massive document and will polute context. Instead use an agent to read it, ask it to convert pdf to png files on those pages where he feels like there are interesting figures and report back on what is there (a lot of useful stuff) and what is extractable (reasonably) literally from png files, even as a first pass. You can ask another agent even to extract things too. Btw this also goes for the other two papers since parsing PDF is always tough for an LLM since they contain figures.

3. idk. The language should be scientifc and simple that's for sure. This is hardly a relevant question tbh. If ur trying to sound an alarm, ok, but that's not the point of the whole paper at least. This happens every day in dosimetry lol.

4. Sure, why not. Might wanna spin up an agent with a clearly defined prompt though.

Focus on the medium level now. The writing style is all the way at the end. Also dont forget previous instructions. 


I need to go now. You can have the floor for a long time. Good luck. Impress me. Feel free to pivot if you want when you start zooming in. You are opus. You are in control. You have freedom. Get guided by a great paper not just copying or summarizing a monograph. Be critical and think about things.

---

## Message 4

go on

---

## Message 5

papers/key_literature/Kodera2024.pdf (convert pdf to png files and read those files, there is one killer figure there where they already compare SARwb at the ref levels across literature). The paper itself is also in general very useful.

I read most papers here. There is a lot to say but I will just say this. It looks like you didn't really feel like going all the way to the finality of the paper. First of all it isnt IEEE double column (a big problem here is the size of figures... figure something out... perhaps look for the scripts and try to rerun a modified version of them that fits in 3.5 in horizontal). The style isn't respected. For one, IEEE seems very keen on their intro methods results conclusion kinda structure, perhaps with a discussion. And even the subtitles should be deadsimple and clear (not "What this paper is" lol....). You are writing a little bit too much like you're explaining it still to me. A big blunder too is for them to be referencing "as in paper A". We can't have that. It's standalone. But overlap is okay you now. Make sure this build well (comprehensive) although it is perfectly ok to go fast through the derivations or work with appendices if you feel like you're close to page limits ( i think so far looks ok still, no?). The monograph does this excellently and you should take example of it. 

Moreover, the language is just not as described in the style guide. 
papers/how_to_write_good/ai_writing.md
papers/how_to_write_good/elos.md
papers/how_to_write_good/style_analysis.md
papers/how_to_write_good/style_guide.md
You have a lot of "mic drop" moments. Like. You are describing something, clearly holding yourself in to not splurge, and then say a 3 word sentence like 'The physics does not'. No need. 

There are also lots of words which have simpler, more basic, dry, to the point, academic synonyms. That doesnt mean it should be for toddlers, but you should review many sentences to make sure there is no unnecessary constructions and big(ish) words. I am sensitive to that.

We have to go through the papers with some serious edits on this. Can be aggresive. Also try to focus more on the present tense calm neutral and SIMPLE AND SHORT sentences of subject-verb-somebasicextra. "The experiment shows a higher X value." those kind of sentences. Without too many subsentences and long ones, unless they are enumerations/lists (those dont care a big load). For some reason "respectively" can be used freely without counting its cognitive load, btw, so feel free on that.

Do a big write now, compile, convert to png, read the png files, critique visual issues, iterate until satisfied. Especially when latex is unusual.

Also you have a big problem with LaTeX paragraph vs a new block. Mimick the way the literature does it. Relatively large blocks of contiguous text without too many new lines every other sentence (the case now). Use justified. Actually leave some space when going to new paragraph and let it be a meaningful paragraph.

Dont cut up an intro into subsections (i think this is unusual).

You have to try to fit in much more into the paper literature style. Be as normal as possible. 

Stop too much promotional language. 

Btw you can use agents for this stuff intelligently but pass them enough instructions of mine and pointers to docs.

---

## Message 6

One big issue also is that the notation of ReLU is a little bit divisive. From a mathematical point of view it's okay to use this one. However more or less half of the people I talk to think it's kinda cool to suggest that this may be related to machine learning because it's differentiable. The other half are more simple, dry, and to the point where they say you could just use some different type of notation to just say it's the positive part of n times k and it's zero when it's negative. We're just not doing any machine learning and this is just a classic way to fall into a viewer strap.

Now personally I actually think it's kinda nice to put it that way, especially because for diffraction you change the value to gelu. The monograph talks about this.

Let me also go a little bit on a tangent. In the validation folder we went through all the levels. We started adding curvature, we started adding diffraction and whatnot, and all those had meaningful impact, especially sub 6 GHz. I'm kinda wondering why we didn't really add any content in any paper, as far as I know, with all the corrections. I feel like we're missing those corrections a little bit, especially about curvature. I also feel like the occlusion factor itself should be highlighted and is almost critical because it determines how shadowing works. Also one of the interesting parts was that it reflects on the body, then it re-reflects onto itself and then reflects onto the body again, etc. etc. We kind of guesstimated that in the monograph to be very small. I think it's also important that we convince the reader that this can be a meaningful alternative to FDTD. 

Like for example if you're introducing "the" geometric law, I do believe it needs an occlusion factor at least right, or would you consider that to be an additional extra? Can we absorb the occlusion factor into the value notation somehow (keep n * k but also do * O(n * k) and that's equivalent)? What do you think? What's the most elegant way forward... Can we kill two birds with one stone, this issue and the first one i mentioned here?

---

## Message 7

The PC restarted. I think two agents might have been stopped idk if u can recover smth or need to rerun.

---

## Message 8

Look at every single figure that has been included in any paper. If they are in PDF form, convert them to PNG and read those PNGs. It is imperative that all of those figures are created using the package science plots. This causes them to use LaTeX as a rendering under it. You'll find some evidence of this under scripts that were used in the monograph to produce the figures in the first place.

It's also imperative that the width of the figure is 3.5 in single column or more than that for the 2-column such that it all fits nicely into the paper. As I said before sometimes we will have to re-render and actually re-run the ground truth scripts for wherever these were created, just with a different styling of the plot at the end, that's it. Also make sure that these figures actually make sense as a whole in the paper. Some of these figures are kind of meant as a bit of an internal PNG, something for me to know how it's going, but they aren't actually publication ready. Everything that is shown on the figure has to be understandable and explainable inside of the paper. A good example of that is the validation of the simfor life simulations. They're referring to level 2, level 3, whatever, but those levels aren't really explained, are they? It has to be all internally consistent with the paper. In short I'm asking you to improve the figures in many obvious ways.

---

## Message 9

always stop using 'co-workers' and use et al instead. in paper C you mention Geometric Dosimetry being on arxiv... it wont. I guess you can fake-cite it if you want but the best would be not to, for now. 

Paper C intro is pretty bad. Intro is too technical. I'd prefer more leaning into the literature, the wider positioning (think 'zooming in') and main contributions


I've looked at several papers and many appear to stick with main section titles that are NOT introductionmethodsresultsdiscussionconclusion. Am I wondering: why,, genuinely? is it because you think it's normal? or acceptable. you can TOTALLY tell me yes if you believe so. I was under the belief that literally every IEEE paper needs IMRAD kinda and that you only get freedom to name subsections.

---

## Message 10

btw dont you think that one tikz figure from part 3 in the monograph showing the geometry is useful to include? idk

---

## Message 11

ok for C

---

## Message 12

do we still have "micdrop" statements? I saw "one identity, five independent studies" in the key figure of paper B. I guess the agent is working on that maybe.

---

## Message 13

validation/fig_geometry_maps.png is really pretty. not this png specifically, but the "concept" of showing a phantom with colors really speaks to readers, it's nice to visualize. Is there no space at all for any of those? obviously they would need to be reworked. What's your take on this? Could we code something specific up or we just add smth like that?

---

## Message 14

has your agent finished iterating on figure quality? I still see paper B figure 1 with tons of issue. ask the agent to look at that specifically. that a png of the top of page 5 of paper B. it will show 'wasted' useful whitespace. lots of symbols and text etc overlapping. the idea is there, but it's generally a bit sloppy. Ask it to iterate quite relentlessly until satisfied with clear things that aren't messy. I guess with the ambition of stuff being shown here it will be tough to keep the convention of equal fontsize throughout the figure equal to the paper's fontsize (smth that should apply as much as possible). So legend fontsize probably just needs to be less than the classic 10pt

---

## Message 15

unification
 exposes the anthropometric scaling
those are just two probably among a sea (or pond) of remaining little words im like 'why bro'. just keep it simple. please. KISS. You have to be aggresive in the dryness and clarity. There is often an easier synonym

---

theory/psSAR10g.tex do you think this could fit into one of the papers? is it worth it?

---

## Message 16

Find the jsonl file of this conversation. extraction all user inputs to an md file.

---


# Documentation Style Guide

This document outlines the style and tone for all documentation in this repository.

## Core Principles

- **Be concise and direct.** Use an economy of words. Get straight to the point.
- **Sound like a senior developer.** Confident, intelligent, and efficient. Avoid AI-like verbosity, apologies, or overly formal language.
- **Focus on the essentials.** It's okay to be brief, even to the point of vagueness if the context is clear to the user. Correct grammar, but don't obsess over punctuation.
- **Nonchalant Expertise.** Point to concepts with trimmed-down, to-the-point explanations. Every now and then, drop a niche, subtle point that reveals deep understanding.

## Voice and Tone

- **Academic and Professional.** The tone is authoritative and knowledgeable, suitable for a publication. It is direct and written in the present tense. Avoid humor and overly casual language.
- **Clarity is key.** Use simple, direct language. Avoid jargon where possible, or explain it clearly if it's necessary.
- **Minimalist.** Less is more. If a sentence or paragraph does not add value, it should be removed.
- **Subtle Insights.** From time to time, include a brief, insightful comment on a non-obvious detail. This demonstrates mastery without being boastful.

## Layered Documentation

To cater to both new and experienced developers, we use a layered approach:

- **Quick Starts & Tutorials:** Aimed at beginners. These should be step-by-step guides that get the user to a working result quickly.
- **Topical Guides:** Deeper dives into specific concepts or components. These are for users who want to understand a particular area of the codebase in more detail.
- **API Reference:** The nitty-gritty details. This should be generated from code comments where possible and provide a quick reference for experienced developers.

## Code & Examples

Given the complexity of the repository, the documentation prioritizes high-level concepts over detailed, runnable code examples.

- **Focus on Concepts:** Explain the 'why' and 'how' of the architecture and features, not just the 'what'.
- **Use Snippets for Illustration:** When a specific, straightforward example is necessary (e.g., a configuration setting), quote the relevant snippet directly. Avoid complex examples that would require significant setup to run.

## Formatting & Structure

The structure should be clean and easy to read, but not overly rigid.

-   **Headings:** Use headings to structure the content logically. Don't enforce a strict hierarchy, but keep it intuitive.
-   **Emphasis:** Use bold (`**bold**`) for emphasis. Avoid italics unless necessary for a specific reason (e.g., quoting a term).
-   **Lists:** Use bullet points (`-`) for lists to keep information scannable.
-   **Emojis:** Emojis are only permitted on "advertisement" pages like the main `README.md` or the documentation landing page. They should not be used in technical documentation.
-   **Hyperlinks:** Use hyperlinks (`[link text](url)`) liberally to connect concepts and refer to other parts of the documentation or external resources. This creates a more integrated and navigable experience.

## Human Touch

To avoid a robotic tone, a human element is permitted.

-   **Calculated Imperfections:** On very rare occasions, a minor spelling, punctuation, or grammatical error (such as a missing or duplicated article) can be introduced. This should be infrequent and subtle, making the text feel more natural and less machine-generated.

## Advanced Markdown

As a markdown guru, you should leverage the advanced features provided by `mkdocs-material` and the `pymdownx` extensions.

-   **Admonitions:** Use admonitions (`!!! note`, `!!! warning`, etc.) to highlight important information. Use them sparingly to maintain their impact.
-   **Tabbed Content:** Use tabs (`=== "Tab 1"`) to present information concisely, for example, to show different configuration options.
-   **Mermaid Diagrams:** For complex concepts, a Mermaid diagram can provide a quick visual explanation. Don't overdo it. A simple diagram is often more effective than a complex one.
-   **Snippets:** Use snippets (`--8<-- "path/to/file.md"`) to include content from other files. This is useful for keeping examples and other repeated content DRY.

## Important

Never use Title Case capitals in titles. Just capitalize the first letter of some title of a (sub)section, and keep the rest not capitalized. Obviously don't be dumb and start writing things that need capitals without them, e.g. Gui instead of GUI, don't do that.
## The `--no-cache` flag

The `--no-cache` command-line flag is a feature that forces the system to perform a fresh setup for a simulation, bypassing the default behavior of verifying and potentially reusing existing project files. When this flag is active, GOLIAT will skip the verification step that checks if a suitable `.smash` project file already exists. Instead, it will proceed as if no such file was found, deleting any existing project and creating a new one from scratch.

This is particularly useful in scenarios where a previous run may have been corrupted or when you want to ensure that the simulation starts from a clean state, free from any potential artifacts of previous runs. By using `--no-cache`, you guarantee that the setup is completely new, which can be essential for debugging or for ensuring the integrity of a specific simulation run.

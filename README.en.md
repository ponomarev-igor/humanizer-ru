<p align="center">
  <img alt="version" src="https://img.shields.io/badge/version-2.3.0-C4473A?style=flat-square">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-313131?style=flat-square">
  <img alt="target language" src="https://img.shields.io/badge/target-Russian-6B6258?style=flat-square">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-supported-6B5B95?style=flat-square">
</p>

[Русский](./README.md) · **English**

# Humanizer RU

> Every AI humanizer on the market is built for English. Russian AI text fails
> differently: the giveaway is not "delve" or "tapestry", it is bureaucratese.
> English-trained tools do not catch it at all.

An agent skill for Claude Code that edits Russian text. It strips bureaucratese,
em dashes, reversal rhetoric ("not X, but Y" and eight disguises of it), filler,
metaphor clusters and chatbot boilerplate. It does not rewrite from scratch, does
not invent facts and does not change your tone. A separate proofreading layer
handles spelling and punctuation.

## Why this is not another humanizer

**Bureaucratese, not anglicisms.** The language core is built on the Russian
editorial tradition: Nora Gal, *The Word Living and Dead*; Ilyahov and Sarycheva,
*Write, Cut*. It is not a translated checklist of English AI tells.

**Rules target the device, not the string.** A model will happily repackage
"not X, but Y" as "it seems X, in fact Y", or split it across two sentences. The
rule describes the rhetorical move itself, planting a misconception and then
removing it, rather than any particular phrase.

Smaller things that end up mattering:

- **Quantitative check, not just judgement.** `scripts/check-prose-ru.py` measures
  the coefficient of variation in sentence length, connective density, metaphor
  clusters, dashes and reversal rhetoric by regex. No external dependencies.
- **A real proofreading layer** (part 8): spelling and punctuation to Russian
  norms. You can ask for error correction only, leaving wording untouched.
- **It invents nothing.** No facts or numbers absent from the source. If the text
  is already alive, the skill says so instead of editing for the sake of editing.
- **It catches copy-paste residue** from chatbots such as `oaicite:`,
  `turn0search0`, `grok_card://`, `[cite: N]`, removes it and flags the source.
- **Your voice is opt-in.** Author voice is applied only on explicit request and
  only from samples of your own writing, never on its own initiative.

## Example

**Before:**
> В современном мире использование нейросетей в маркетинге является по-настоящему
> уникальным инструментом, играющим ключевую роль в трансформации индустрии.
> Стоит отметить, что осуществление внедрения данных инновационных технологий
> обеспечивает повышение эффективности.

*(Literally: "In the modern world, the utilisation of neural networks in marketing
is a truly unique instrument playing a key role in the transformation of the
industry. It is worth noting that the implementation of said innovative
technologies ensures an increase in effectiveness." Five nouns deep, zero content.)*

**After:**
> Нейросети в маркетинге ускоряют скучную часть. Не всё подряд. Стратегию точно нет.
>
> Они отлично делают черновики: заголовки, рассылки, карточки товаров. И так же
> отлично звучат убедительно, будучи пустыми.

*("Neural nets speed up the boring part of marketing. Not everything. Definitely
not strategy. They are great at drafts: headlines, newsletters, product cards. And
equally great at sounding convincing while saying nothing.")*

A full breakdown of what was caught in this example lives in `core/humanizer-ru.md`.

## Install

Requires Claude Code (CLI, VS Code extension or desktop app).

```bash
git clone https://github.com/ponomarev-igor/humanizer-ru.git ~/.claude/skills/humanizer-ru
```

Without git: download the repository archive and unpack its contents into
`~/.claude/skills/humanizer-ru` (Windows: `C:\Users\NAME\.claude\skills\humanizer-ru`).

Restart Claude Code. See [`INSTALL.md`](./INSTALL.md) for details and troubleshooting.

## Usage

The skill activates on triggers in conversation, all in Russian: «хуманизируй»,
«убери AI», «сделай человечнее», «почисти от штампов», «проверь пунктуацию»,
«исправь ошибки». Or invoke it explicitly:

```text
хуманизируй этот текст: <your text>
```

For texts from roughly 300 words up, you can also run the quantitative check:

```bash
python3 scripts/check-prose-ru.py text.md
```

The script reports form only (dashes, reversal rhetoric, flat sentence rhythm,
metaphor clusters) and never decides for the author. Hard hits (dashes, reversal
rhetoric) are always worth fixing; warnings are for you to judge.

## What it does not do

It does not write in your voice and does not generate text from scratch. This is
an editor, not an author. It does not guarantee passing any specific AI detector:
the goal is living Russian prose, not defeating a particular algorithm.

## Repository layout

| File | Contents |
|---|---|
| [`SKILL.md`](./SKILL.md) | The built skill file, what Claude Code reads. The section between the `BEGIN/END core` markers is generated from `core/humanizer-ru.md`, do not edit it by hand |
| [`core/humanizer-ru.md`](./core/humanizer-ru.md) | Source of truth: all eight rule sections, the cliche dictionary, the full worked example, the process |
| [`scripts/check-prose-ru.py`](./scripts/check-prose-ru.py) | Quantitative prose check: sentence-length variation, connective density, metaphor clusters, dashes, reversal rhetoric |
| [`scripts/build-skill.mjs`](./scripts/build-skill.mjs) | Inlines `core/humanizer-ru.md` into `SKILL.md`. Run: `node scripts/build-skill.mjs` |
| [`INSTALL.md`](./INSTALL.md) | Detailed install and what to do when the skill is not picked up |
| [`CHANGELOG.md`](./CHANGELOG.md) | Version history |

## Development

Edit `core/humanizer-ru.md` only, never `SKILL.md` directly. Rebuild with:

```bash
node scripts/build-skill.mjs
```

## Feedback

Found a false positive, a missing bureaucratese pattern or a punctuation rule that
is wrong? Open an issue. Attach a before/after sample, it speeds things up a lot.

## Licence and sources

MIT, see [`LICENSE`](./LICENSE). Content attribution is in [`NOTICE.md`](./NOTICE.md):
the catalogue of AI-writing tells draws on
[Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
(CC BY-SA 4.0). The language core is Nora Gal and Ilyahov/Sarycheva, see
`core/humanizer-ru.md`.

<p align="center">
  <sub>Humanizer RU · 2.3.0</sub>
</p>

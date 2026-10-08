# zh-plain — 中文受控语言规范 / A controlled-language spec for Chinese

A Claude Code skill that rewrites ambiguous or translation-shaped Chinese into text a
downstream agent can parse without guessing, and rewrites AI-flavored Chinese into prose
a human would actually say.

**中文摘要**:把有歧义或翻译腔的中文改写成可精确解析的文本。双模式 + 确定性检查器。
skill 自身的文档(SKILL.md、规则表、实例)全部是中文。

## Why not just port ASD-STE100

[ASD-STE100](https://www.asd-ste100.org/) (Simplified Technical English) is the aerospace
controlled-language standard. Half of its discipline is language-neutral — one instruction
per sentence, one meaning per word, preserve modality, drop nothing — and that half transfers
to Chinese unchanged. The other half is English morphology: phrasal verbs, present perfect,
articles. Chinese has none of those, so a translation of STE would ship rules that fire on
nothing.

Measured, not asserted: pointing `ste-lint.py` at a real Chinese agent-facing status report
returns **zero** hits for its passive, present-perfect, nominalization, and marketing-adjective
rules — every one of them is blind to Chinese. Its sentence-length rule is worse than blind:
line-based word counting turned 641 Chinese characters into 254 "words", so the 25-word cap
can never trip.

What Chinese actually needs instead:

| Chinese-specific source of ambiguity | English-language counterpart |
|---|---|
| Zero subject drops the agent (「已删除」— deleted by whom?) | pro-drop, STE's "no ellipsis" |
| Comma-chained clauses with no connectives (流水句) | one instruction per sentence |
| Aspect markers 「了/着/过」 read two ways | STE's tense exclusions |
| Unmarked passive hides the actor | passive voice with an unclear actor |
| 「的」-chains stacking four modifiers | noun clusters |

## Two modes

The split here is by **reader**, not by verifiability (which is how STE splits). The two
halves conflict — interface text wants flat repetition, prose wants rhythm — so pick one and
stay in it.

| | Interface | Voice |
|---|---|---|
| Reader | agent, downstream system | human |
| Text | tool descriptions, error strings, system prompts, status reports, skill trigger text | READMEs, docs, articles, copy |
| Goal | disambiguation | doesn't read like a machine |
| Style | flat, repetitive, one instruction per sentence — **that is the point** | varied sentence length |

Interface mode: 11 rules (zero subject, comma-chains, term consistency, modality preservation,
「的」-chains, punctuation systems…). Voice mode: 6 rules (translationese, empty verbs,
hype filler, machine parallelism, rhythm) generalized from a slide-copy rule set that already
existed locally.

## Install

```bash
git clone https://github.com/noahwang550/zh-plain ~/.claude/skills/zh-plain
```

Or copy the directory to `~/.claude/skills/zh-plain`. The frontmatter `description` carries
the Chinese trigger phrases, so the skill loads automatically when the user says
「这段中文有歧义」「去 AI 味」「翻译腔」「说人话」and similar.

## The linter

```
python scripts/zh-lint.py 文档.md                     # interface mode (default)
python scripts/zh-lint.py --mode voice 文档.md         # voice mode
python scripts/zh-lint.py --baseline 5 存量.md         # tolerate 5 hard findings
python scripts/zh-lint.py --disable semicolon 文档.md
python scripts/zh-lint.py --selftest
```

Eleven structural checks, pure stdlib, no dependencies: clause-comma run-ons, long enumerations,
over-long sentences, term rotation, hype filler, empty verbs, 「的」-chains, semicolons,
passive markers, mixed full/half-width punctuation, and ASCII punctuation inside Chinese prose.
`--mode voice` turns off the sentence-length
and comma-run rules (prose wants rhythm and parataxis is legal there) and downgrades semicolons
to advisory.

The last two are a pair, split by what they can see: `punct-mix` only fires when both systems
appear in one document, so a Chinese document written entirely with ASCII commas and no
full-width punctuation at all used to pass silently. `ascii-punct` catches that case, per line.

**It checks structural patterns only.** It does not compare an original against a rewrite, does
not verify that meaning survived, and does not judge whether a rewrite is better. Zero findings
means the configured structural checks found nothing. Use it as a lint hint, not a gate.

Modality words (可能 / 大概率 / 约 / 仅 / 疑似 / 需确认 / 未实测) are never flagged — modality is
content, not style. `--selftest` asserts this.

## Evidence

Run against real Chinese corpora, not constructed examples:

| Corpus | Findings |
|---|---|
| A real agent-facing status report (654 CJK chars, 22 clauses) | 5 semicolons, 4 term-rotation groups, longest clause 71 chars, 7 passive markers, mixed punctuation |
| A hand-written clean Chinese sample | 0 findings |
| Chinese marketing copy | hype-word fires |
| This repo's own `SKILL.md` | 13 hard — the rule tables quote the patterns they forbid (`--baseline 13`) |

## Credits

The language-neutral discipline is borrowed from ASD-STE100 (ASD, Issue 9). STE's official
~900-word dictionary is not redistributable and is **not** reproduced here. The voice-mode
rules were generalized from a local slide-copy rule set. The Chinese-specific mechanisms,
the rule split, and the linter are original.

Inspired by [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill), which
does this for English.

## License

MIT — see [LICENSE](LICENSE).
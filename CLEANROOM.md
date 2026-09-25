# Clean-room protocol

This project is licensed Apache-2.0. Its implementation is written only from permissively-licensed and
factual sources (see PROVENANCE.md). This file records the protocol that keeps that claim true, and is
enforced by convention and (where noted) by tooling.

## The wall

- **Implementation code** (the `python/`, `go/`, `typescript/` subtrees) is written **only** from:
  `shared/SPEC.md`, `shared/methods.json`, `shared/methods.schema.json`, and `shared/vectors/*`.
- The **GPL/LGPL sources** (`islamic-network/prayer-times`, `islamic-network/prayer-times-moonsighting`,
  PrayTimes.js v2.x) are **never** opened while writing or reviewing implementation code, and are **not**
  vendored into this repository.
- `RESEARCH.md` and the `*-REVIEW.md` files are **analysis-phase artifacts**. They may describe GPL internals
  (that is factual research); they must **not** be used as an implementation source, and are excluded from
  the release artefacts and from implementer-agent prompts.

## Agent workflow

- Coding-subagent prompts must include **only** SPEC + `methods.json` + the schema + vectors. Do not include
  `RESEARCH.md`, the review files, or any GPL-source excerpts.
- The §13 target-behaviour register items are each backed by a black-box probe; where a register item must be
  justified, cite the probe, never the GPL source.

## Originality check

A CI / scheduled job diffs the implementation subtrees against the upstream sources for
**identifier-overlap and token n-gram similarity** (the realistic failure mode is accidental transliteration,
since the algorithm is small and familiar). The upstream sources are fetched to the runner and never
committed. A threshold breach fails the job.

## If you must change a §13 behaviour

1. Re-derive it black-box from the AlAdhan API (fresh coordinates, recorded fetch timestamp).
2. Record the probe and its result in the register entry.
3. Do not consult the GPL source to decide *how* to implement it — only to know *what* the observable output
   is (and even then, prefer the API).

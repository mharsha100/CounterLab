# Attribution and license scope

The root MIT license covers CounterLab's own application, numerical reference,
tests and documentation. It does not relicense models, dependencies, published
papers, external implementations or third-party artifacts. This is an attribution
record, not a legal clearance or a claim of affiliation with the organizers.

## Published numeric reference

The optional local file `cases/paging/source_regime/reported_artifact.json` is
a numeric comparison artifact from the independent supporting reproduction
`MarxistLeninist/repro-la-paging-bundle`, revision
`0e2be0e71c25330eddbf452a0bd034ba1a3f6f24`, file `outputs/e4_robustness.json`.

- [Pinned upstream artifact](https://huggingface.co/datasets/MarxistLeninist/repro-la-paging-bundle/resolve/0e2be0e71c25330eddbf452a0bd034ba1a3f6f24/outputs/e4_robustness.json)
- SHA-256: `e29bc8a3eef20b36b620e512f4cbab106eb195cc48f22dca024c823b2bfb31cb`
- Purpose: preserve the exact numerical reference for three selected comparisons.
- No redistribution license was established from the pinned README/tree or
  dataset card inspected on October 25. We infer no license grant from public
  availability. **New source, judge and source-replay ZIPs omit this full file.**
- An explicit `fetch_reference.py --download` command retrieves the pinned
  public HTTPS file and checks its SHA-256 before installation. It sends no
  inference key, uses no paid service and never executes downloaded data.
- Three attributed numeric comparison rows remain in `reported_values.json`,
  bound to the original record. These are the finite facts used in the comparison;
  we do not claim authorship or an MIT grant over upstream material. With no full
  file installed, the app explicitly withholds the full-artifact identity claim.
- Older local release ZIPs predate this policy and may contain the full file.
  They are development artifacts, not publication candidates. Use the newest
  audited release described by `release-summary.json`.

[Pinned README inspected](https://huggingface.co/datasets/MarxistLeninist/repro-la-paging-bundle/resolve/0e2be0e71c25330eddbf452a0bd034ba1a3f6f24/README.md).
The optional file is ignored by Git. The release audit inspects nested ZIPs and
rejects its filename or exact content, even if renamed. This distribution choice
avoids bundling the full file; it is not a legal clearance for every aspect of
the project.

Source URLs and inspected contracts are in `cases/paging/sources.json` and
`cases/paging/study_sources.json` where present. External algorithm code in
`downloads/` was inspected as text; it is excluded from both release archives.
CounterLab's numerical code is an independent implementation. Matching one
supporting reproduction slice does not establish parity with the original paper.

## Runtime and build dependencies

Python dependencies are pinned in `requirements-lock.txt`; web dependencies are
pinned in `web/package-lock.json`. Their upstream licenses apply. In particular,
React/React DOM are MIT-licensed; production web bundles retain their generated
license notices. `THIRD_PARTY_LICENSES.txt` also contains the complete installed
React, React DOM and Scheduler license texts; it accompanies the source ZIP and
the website under `licenses/`. Packages and model weights are not vendored in the source ZIP.
Do not remove dependency license headers from the compiled web assets.

The interface self-hosts the IBM Plex Sans and IBM Plex Mono fonts (Copyright 2019 IBM Corp.),
bundled from the `@fontsource` packages under the SIL Open Font License 1.1; the full license text
is in `THIRD_PARTY_LICENSES.txt`. The fonts are not sold or renamed.

Nebius Token Factory hosts inference for `nvidia/Nemotron-3-Ultra-550b-a55b`.
CounterLab does not redistribute NVIDIA weights. Provider and model terms remain
separate. Nebius/NVIDIA names identify the tools used; no endorsement is implied.

## Generated records

Recorded model responses, simulated planning examples, local execution receipts
and CounterLab-generated observations retain their provenance labels and hashes.
An included response is not an independently verified scientific statement.
Package hashes detect changes relative to this package; they are not signatures.

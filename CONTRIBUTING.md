# Contributing

Contributions should improve the inspectable research framework without
expanding its data-acquisition or deployment scope. Read
[Release boundary](docs/RELEASE_BOUNDARY.md),
[Input schema](docs/INPUT_SCHEMA.md),
[Public prompt contracts](docs/PROMPTS.md), and
[Ethical considerations](docs/ETHICAL_CONSIDERATIONS.md) before proposing a
change.

## Governance

InterviewSim is Salesforce sponsored. The project welcomes useful issues and
contributions, while Salesforce maintainers retain final responsibility for
project direction, administrative access, and accepting changes.

## Content rules

Contributions must not contain:

- real interview data, excerpts, quotations, or transcripts;
- real names, identity lists, or mappings between IDs and people;
- source-data links, media links, platform IDs, retrieval manifests, or
  provenance trails that point to source material;
- raw audio or video;
- credentials, tokens, private endpoints, internal hostnames, account IDs,
  internal storage paths, nonpublic architecture, or other internal
  infrastructure details;
- model weights, checkpoints, training states, or adapters; or
- deployable personality agents.

Use only abstract placeholders or entirely invented content in documentation,
fixtures, tests, issues, and pull requests. Make the fictional status explicit
in fixture-level documentation or manifests; do not add undeclared fields to
the strict public input schema.

## Terminology

Use the public terms `personality`, `personality_id`, and `interview record`
consistently in code, documentation, fixtures, issues, and pull requests.

## Scope

Accepted changes may address:

- schema validation for already prepared interview records;
- the canonical nested `prepared_input.json` contract;
- response-generation method interfaces;
- evaluation metrics and auditable result formats;
- MCQ construction and exact-match scoring;
- paired statistical analysis;
- tests built from invented fixtures; and
- documentation of limitations and research safeguards.

Do not add discovery, collection, scraping, downloading, transcription, source
verification, identity-resolution, or deployment functionality.

## Issues and pull requests

Use [GitHub Issues](https://github.com/SalesforceAIResearch/InterviewSim/issues)
for reproducible bugs, enhancement requests, and design discussions. Search
existing issues before creating a new one. For substantial changes, wait for
maintainer feedback before investing significant implementation effort.

Pull requests should be focused, refer to any related issue, and include tests
for changed behavior. All changes require maintainer review.

## Development setup

Use Python 3.10 or newer:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

The base package intentionally has no required runtime dependencies. Discuss a
new runtime dependency before adding it, and explain why the standard library
or an optional integration is insufficient.

## Synthetic example and source-distribution checks

The synthetic example generator is non-destructive by default. Inspect
regenerated content in a new directory before considering replacement:

```bash
SYNTHETIC_OUTPUT_ROOT="$(mktemp -d)"
python scripts/generate_synthetic_sample.py --output "$SYNTHETIC_OUTPUT_ROOT/synthetic_examples"
```

Alternate destinations must be outside the repository. Repository-internal
destinations other than the canonical examples path, parent traversal, and
symbolic-link destinations are rejected. If the destination already exists,
choose a new path or inspect it before explicitly passing `--force`.
Running the generator with `--force` and no `--output` replaces the committed
synthetic examples.

Build the source distribution with:

```bash
python -m build --sdist
```

The archive must contain `src`, `tests`, `docs`, `scripts`, and
`examples/synthetic_examples`. Validate from the unpacked archive so missing
release support files are detected before publication.

## Change expectations

Keep changes focused and include:

1. a concise description of behavior and motivation;
2. tests for new or changed behavior using invented inputs;
3. documentation updates for public interfaces or artifact formats;
4. deterministic seeds for randomized tests or analyses;
5. failure cases for malformed records and split leakage; and
6. a note describing any effect on privacy, safety, fairness, or misuse risk.

Do not paste sensitive material into bug reports. Reduce a problem to an
abstract reproducer before sharing it.

## Contribution checklist

Before submitting a change, confirm that:

- tests pass;
- Ruff reports no errors;
- examples and fixtures are entirely invented;
- no real data or real identity information is present;
- no source-data links or internal infrastructure details are present;
- public terminology remains consistent;
- held-out responses cannot leak into generation prompts;
- generated outputs are labeled as generated; and
- the release boundary remains intact.

## Contributor License Agreement

Contributors must sign the
[Salesforce Contributor License Agreement](https://cla.salesforce.com/sign-cla)
before a pull request can be accepted.

## Code of Conduct

Participation in this project is governed by the
[Salesforce Open Source Community Code of Conduct](CODE_OF_CONDUCT.md).

## License

By contributing, you agree to license your contribution under the terms of the
project's [Creative Commons Attribution-NonCommercial 4.0 International License
(CC-BY-NC 4.0)](LICENSE.txt) and to sign the Salesforce Contributor License
Agreement.

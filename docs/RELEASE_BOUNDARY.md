# Release Boundary

## Purpose

This repository publishes the research framework needed to inspect prepared
interview records, build prompts for experimental responses, evaluate model
outputs, and compare paired method scores statistically. Its actual starting
point is a local `prepared_input.json` file that already conforms to the
[input schema](INPUT_SCHEMA.md).

The installable Python distribution is limited to modules under
`src/interviewsim`.

## Research use

> This release is for research purposes only and should not be used to compete with OpenAI, Anthropic, or Google.

The release supports research analysis and comparison of synthetically
generated interview-response datasets and their evaluation results. The
bundled examples are entirely fictional. The paper's original interview
data are not distributed with this repository.

## Starting boundary

InterviewSim starts with structured interview records in the canonical
`prepared_input.json` format. The following activities are outside the release:

- data discovery;
- data collection;
- scraping;
- downloading;
- transcription; and
- source verification.

No component is provided to locate people, enumerate identities, retrieve
media, perform transcript acquisition, follow source URLs, or decide whether a
record is authentic.

## Included capabilities

The public framework is limited to:

- loading and validating the documented local record format;
- holding out the latest 20% of interview records by `sequence`, rounded up to
  a whole interview, and using the remaining earlier records for training;
- building no-context, short-profile, long-profile, chronological, random,
  retrieval, and hybrid grounding prompts;
- validating caller-supplied text-model and embedding interfaces;
- building and parsing strict prompts for content similarity, factual
  consistency, personality similarity, and MCQ evaluation;
- aggregating metric outputs and scoring MCQs; and
- performing paired sign-flip permutation tests.

External model services, credentials, access configuration, and model
artifacts are not part of the package.

## Materials not released

This repository releases no:

- real interview data or excerpts;
- real identity list or mapping between IDs and people;
- source-data links, platform identifiers, or retrieval manifests;
- raw audio, video, or transcripts;
- model weights, checkpoints, or training states;
- fine-tuning adapters;
- credentials or internal infrastructure details; or
- deployable personality agents.

Generated responses and score files are experiment artifacts. They are not
verified biographical records, identity claims, or deployment-ready systems.

## Synthetic examples

The [synthetic examples](../examples/synthetic_examples) were authored
entirely from scratch for this repository from ten generic fictional roles,
with five short interviews per role. Every `personality_id`, profile,
interview, question, and response is invented; none was sampled from or
transformed from research transcripts. Each personality's
`prepared_input.json` is actual loader input.

Across the examples, 50 interviews contain 150 Q&As: 120 train and 30 test.
The split files and all reference artifacts were generated deterministically
for inspection of derived formats. They are not a sample of the paper dataset,
do not preserve its population or content distribution, and cannot reproduce
the paper's reported numbers. A successful audit demonstrates only that the
invented files, references, and counts are internally consistent.

## Reproduction boundary

The paper's empirical results depend on unreleased inputs and model
configurations in addition to the public framework. This repository supports
method inspection and experiments on separately supplied conforming inputs; it
does not claim paper-number reproduction.

## License

InterviewSim is licensed under the
[Creative Commons Attribution-NonCommercial 4.0 International License
(CC-BY-NC 4.0)](../LICENSE.txt).

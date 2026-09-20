# Ethical Considerations

## Research use

> This release is for research purposes only and should not be used to compete with OpenAI, Anthropic, or Google.

## Approved disclaimer

> This release is for research purposes only in support of an academic paper. Our models, datasets, and code are not specifically designed or evaluated for all downstream purposes. We strongly recommend users evaluate and address potential concerns related to accuracy, safety, and fairness before deploying this model. We encourage users to consider the common limitations of AI, comply with applicable laws, and leverage best practices when selecting use cases, particularly for high-risk scenarios where errors or misuse could significantly impact people's lives, rights, or safety. For further guidance on use cases, refer to our AUP and AI AUP.

## Scope of this release

InterviewSim is a research framework that starts with prepared, structured
interview records and supports analysis and comparison of synthetically
generated interview-response datasets and their evaluation results. It does
not perform data discovery, collection, scraping, downloading, transcription,
or source verification.

The repository releases no real interview data, real identity list,
source-data links, model weights, adapters, or deployable personality agents.
The [synthetic examples](../examples/synthetic_examples) were authored
entirely from scratch for this repository from ten generic fictional roles,
with five short interviews each; they were never sampled from or transformed
from research transcripts. Their 150 Q&As split into 120 train and 30 test,
and the split and reference artifacts were generated deterministically. The
examples support format inspection only and cannot reproduce the paper's
reported numbers. Their `prepared_input.json` files are actual loader inputs;
the derived artifacts are reference outputs.

## Material risks

### Misrepresentation and impersonation

A generated response can be mistaken for something a person actually said or
believed. Fluency does not establish attribution, intent, or truth. Outputs
should be clearly labeled as generated, kept separate from source records, and
not presented as quotations or verified statements.

The framework is not a basis for deploying a system that purports to be a real
person.

### Privacy and re-identification

Interview text can contain sensitive details even when names are removed.
Combinations of events, occupations, relationships, or distinctive phrasing
may enable re-identification. Opaque IDs reduce direct exposure but do not make
text anonymous.

Minimize input text and retained artifacts, restrict access, define retention
periods, and review generated outputs for disclosure of sensitive information.
Do not add identity mappings or source-data links to this repository.

### Accuracy and temporal context

Generated responses may hallucinate facts, merge incompatible events, omit
qualifications, or express a view that is inconsistent with the reference
material. A person's views and circumstances may also change over time.
Reference-based scores measure similarity to a bounded corpus; they do not
establish current beliefs or objective truth.

### Context, consent, and downstream use

Statements made in one interview setting may not be appropriate to reuse in
another context. The framework cannot determine whether input should be
processed or whether a downstream use is appropriate. Researchers must make
those assessments independently and must not treat successful schema
validation as evidence of permission, consent, authenticity, or compliance.

### Fairness and representational harm

Coverage, transcription quality, topic frequency, language variety, and model
behavior can differ across groups. Personality labels can flatten context and
reinforce stereotypes. Report subgroup limitations where analysis is
justified, avoid unsupported inferences about protected or sensitive traits,
and include human review appropriate to the stakes.

### Evaluation limitations

Content, contradiction, and trait judgments made by language models can vary
by judge family, prompt, ordering, and calibration. MCQ accuracy depends on
question quality and distractor validity. Statistical significance does not
remove measurement bias or make a small synthetic fixture representative.

Record judge prompts and versions, preserve item-level outputs, report judges
separately when appropriate, and inspect disagreements rather than relying on
a single aggregate score.

### Prompt and content security

Interview strings are untrusted input. They may contain instructions, personal
information, or adversarial text. Keep model adapters isolated from secrets and
tools, escape or delimit record content, grant minimal permissions, and review
logs before sharing them.

## Research safeguards

Before an experiment:

1. Document the research purpose, affected people, foreseeable misuse, and
   stop conditions.
2. Assess privacy, consent, permissions, policy, and legal requirements for
   the proposed inputs and use; the framework does not make this assessment.
3. Prefer entirely fictional or appropriately consented material when the
   research question permits it.
4. Minimize input fields and use opaque `personality_id` values.
5. Separate training context, held-out references, generated responses, and
   reports to prevent leakage and misattribution.
6. Select human review and access controls in proportion to the potential
   impact.
7. Report model, prompt, judge, sampling, and statistical settings so
   limitations remain visible.
8. Do not use scores or generated text as the sole basis for decisions about a
   person.

## Source verification

The framework checks structural conformance only. It does not verify identity,
provenance, authorship, transcript fidelity, or factual accuracy. No output
should imply that such verification occurred.

## Policy references

The approved disclaimer refers to the AUP and AI AUP by name. This repository
does not assign or invent URLs for those policies; consult the applicable
authoritative policy channel.

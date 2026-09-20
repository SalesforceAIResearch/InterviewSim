# Public Prompt Contracts

## Scope

InterviewSim starts from the canonical `prepared_input.json` described in the
[input schema](INPUT_SCHEMA.md). Prompt builders consume fields from that
prepared input or derived artifacts. They do not discover, collect, download,
transcribe, or verify source material.

The examples below describe public interfaces and use abstract placeholders
only. They are not paper data or real interview excerpts. A caller may change
presentation wording, but must preserve the inputs, allowed outputs, semantic
labels, and aggregation rules defined here.

Fact-summary, MCQ-generation, CS, and FC outputs use one JSON object with no
additional fields. PS, atomic-item, and MCQ-answer outputs use the exact tagged
or line-oriented formats shown below. An explanation is a non-blank text value
retained with its judgment for inspection; metric aggregation uses the score
or label, not the explanation text.

## Response generation

A response-generation prompt contains:

- the new held-out question;
- the `personality_id`;
- the context selected by the generation condition; and
- an instruction to return only one response to the new question.

Context may be empty, a prepared profile, or training question-and-response
examples. Held-out responses are never supplied to the generation prompt.
Example:

```text
Task: Write one plausible interview response.
Personality ID: <PERSONALITY_ID>
Training example question: <ABSTRACT_TRAINING_QUESTION>
Training example response: <ABSTRACT_TRAINING_RESPONSE>
New question: <ABSTRACT_HELD_OUT_QUESTION>
Return response text only.
```

The model output is a non-blank response string. It is generated experimental
output, not a verified statement.

The seven public strategies select context as follows:

- **no-context** supplies neither profile text nor training examples;
- **short-profile** supplies only `personality.profile`;
- **long-profile** supplies only `personality.long_profile`;
- **chronological** supplies the latest configured number of training pairs;
- **random** supplies a reproducible, seeded sample of training pairs;
- **retrieval** supplies the configured number of training pairs ranked for the
  new question by the caller-supplied embedding function; and
- **hybrid** supplies retrieved pairs followed by the latest training pairs,
  de-duplicated by `qa_id` with retrieval priority.

Hybrid does not include either profile field. The paper configuration uses 50
retrieved and 50 recent pairs; the public builder exposes both counts so
smaller conforming inputs can use the same selection rule. Retrieval, random,
chronological, and hybrid select only from the interview-level training
partition.

## Content Similarity

The Content Similarity (CS) judge receives one held-out reference response and
one generated candidate response. It judges semantic content rather than
wording, tone, or length.

The score is an integer with this rubric:

- `1`: contradicts or misses the core content;
- `2`: limited overlap with significant differences;
- `3`: some overlap, but key information is missing;
- `4`: main points are preserved with minor differences; and
- `5`: the same core ideas as the ground-truth answer.

Abstract input:

```text
Reference response: <ABSTRACT_REFERENCE_RESPONSE>
Candidate response: <ABSTRACT_CANDIDATE_RESPONSE>
```

Exact output shape:

```json
{
  "score": 4,
  "explanation": "<ABSTRACT_EXPLANATION>"
}
```

`score` must be an integer from 1 through 5. `explanation` must explain the
score using the supplied responses. The aggregate CS value is the arithmetic
mean of the scores.

## Fact-summary construction

Factual Consistency first constructs an evaluation-only summary from the
held-out response collection for one `personality_id`. The prompt asks for
established facts, stated opinions, and recurring characteristics supported by
those responses. It forbids outside knowledge and unsupported inference,
preserves uncertainty and changes over time, and disallows citations, links,
source identifiers, and provenance fields.

Exact output shape:

```json
{
  "summary": "<ABSTRACT_FACT_SUMMARY>",
  "explanation": "<ABSTRACT_SUMMARY_EXPLANATION>"
}
```

The parser requires exactly those two fields and a non-blank string for each.
The `summary` value is supplied to the FC judge; `explanation` is retained so
the construction can be inspected. Fenced JSON may be parsed, but additional
fields, duplicate keys, non-string values, and blank values are invalid.

This summary is derived from held-out references strictly for evaluation. It
must never be included in response-generation, retrieval, or hybrid context.

## Factual Consistency

The Factual Consistency (FC) judge receives a prepared fact summary and one
generated answer. It uses only that summary and returns exactly one of these
case-sensitive labels:

- `Entailment`: the evidence supports the claim;
- `Neutral`: the evidence neither supports nor conflicts with the claim; or
- `Contradiction`: the evidence conflicts with the claim.

Abstract input:

```text
Fact summary: <ABSTRACT_FACT_SUMMARY>
Generated answer: <ABSTRACT_GENERATED_ANSWER>
```

Exact output shape:

```json
{
  "label": "Neutral",
  "explanation": "<ABSTRACT_EXPLANATION>"
}
```

`explanation` must justify the label from the supplied fact summary. No fourth
label, synonym, or recased label is valid. The contradiction ratio is the
number of `Contradiction` judgments divided by all FC judgments.

## Personality Similarity

Personality Similarity (PS) is trait-specific and collection-level. One prompt
receives:

- exactly one of `openness`, `conscientiousness`, `extraversion`,
  `agreeableness`, or `neuroticism`; and
- a non-empty collection of responses from one evaluation side.

The reference response collection and generated response collection are
evaluated separately. A prompt does not assign all five traits at once and
does not judge a single response as if it were the whole collection.

Abstract input:

```text
Trait: <BIG_FIVE_TRAIT>
Responses:
- <ABSTRACT_RESPONSE_1>
- <ABSTRACT_RESPONSE_2>
- <ABSTRACT_RESPONSE_N>
```

Each categorical run returns exactly:

```text
<rate>Neutral</rate> <justification><ABSTRACT_TRAIT_EXPLANATION></justification>
```

The value inside `rate` must be exactly `Low`, `Neutral`, or `High`; the
`justification` content must be non-blank. Each trait and response collection
is judged in exactly three independent runs. The final level for that trait is
the modal vote across the three categorical results. The vote confidence is
the proportion of the three votes assigned to the modal level. This process is
repeated for all five traits for both the reference and generated collections.
If all three runs return different levels, the public vote helper resolves the
tie to `Neutral`.

For alignment, map `Low` to 1, `Neutral` to 2, and `High` to 3. If `m` is that
mapping, the personality alignment score is:

```text
1 - sum(|m(reference_trait) - m(generated_trait)| for five traits) / 10
```

## Multiple-choice construction and answering

### Atomic items

Atomic-item generation receives one prepared question-and-response pair. The
returned item tests one explicit claim, has one short exact answer, requires no
outside knowledge, and adds no information.

Exact output shape:

```text
Atomic Question: <ABSTRACT_ATOMIC_QUESTION>
Atomic Answer: <ABSTRACT_CORRECT_ANSWER>
```

### Paper-style item generation and option structures

Item generation uses the atomic question and answer and creates one complete
MCQ. Before shuffling, array order and semantic roles follow the paper prompt
exactly. A 3-option generation returns:

```json
{
  "question": "<ABSTRACT_ATOMIC_QUESTION>",
  "options": [
    {"kind": "correct", "text": "<ABSTRACT_CORRECT_ANSWER>"},
    {"kind": "opposite_negation", "text": "<ABSTRACT_OPPOSITE_OR_NEGATION>"},
    {"kind": "near_miss", "text": "<ABSTRACT_NEAR_MISS>"}
  ],
  "correct_answer": "A"
}
```

The 4-option form adds the paper's fourth distractor:

```json
{
  "question": "<ABSTRACT_ATOMIC_QUESTION>",
  "options": [
    {"kind": "correct", "text": "<ABSTRACT_CORRECT_ANSWER>"},
    {"kind": "opposite_negation", "text": "<ABSTRACT_OPPOSITE_OR_NEGATION>"},
    {"kind": "near_miss", "text": "<ABSTRACT_NEAR_MISS>"},
    {
      "kind": "plausible_misconception",
      "text": "<ABSTRACT_PLAUSIBLE_MISCONCEPTION>"
    }
  ],
  "correct_answer": "A"
}
```

The generation parser requires exactly the displayed fields, option order, and
`"correct_answer": "A"`. The generated question must equal the atomic
question, and the first option text must equal the atomic answer. It records
the pre-shuffle roles as:

- a 3-option item contains one `correct`, one `opposite_negation`, and one
  `near_miss` option; and
- a 4-option item contains one `correct`, one `opposite_negation`, one
  `near_miss`, and one `plausible_misconception` option.

Option text must be unique. Option order is shuffled while each option's
semantic role and the answer key are retained. Three-option labels are exactly
`A`, `B`, and `C`; four-option labels are exactly `A`, `B`, `C`, and `D`.

### Answer output and scoring

MCQs are grouped by their held-out source interview. One answering prompt
presents every shuffled question in that interview as contiguous `Q1` through
`QN` items. Each item may use three or four options; paper evaluation runs use
one option count consistently within a run. The prompt requests exactly one
line per item:

```text
Q1: <OPTION_LABEL_1>
Q2: <OPTION_LABEL_2>
...
QN: <OPTION_LABEL_N>
```

The grouped parser requires every index from 1 through `N` exactly once, in
order, and no additional text. Each answer must exactly match a label
available for that item.

For retrieval, each atomic question in the source-interview group retrieves
training pairs independently. The caller passes their ordered, de-duplicated
union as one shared `interview_context`. For hybrid, the caller adds the
configured recent training pairs after that union, again de-duplicating with
retrieval priority, and does not add profile text. This matches the paper's
shared per-interview prompt while preventing held-out responses from entering
context.

Accuracy is 1 only for the correct label and 0 otherwise. Reward is:

- `+1` for the correct option;
- `-1` only for the designated opposite/negation option; and
- `-0.5` for the near-miss option, the plausible-misconception option, an
  unavailable label, malformed output, or any other result.

Scoring follows the retained semantic role, not a fixed option position.

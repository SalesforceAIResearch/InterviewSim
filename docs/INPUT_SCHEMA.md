# Input Schema

## Canonical loader input

InterviewSim begins with interview data in the documented format. The
canonical loader input is a UTF-8 JSON file named `prepared_input.json`, with
one document per `personality_id`.

The root shape is:

```text
schema_version
personality_id
personality
  profile
  long_profile
interviews
  interview_id
  sequence
  qa_pairs
    qa_id
    question
    response
    tags
```

Unknown fields and duplicate JSON keys are rejected. Identifiers must be
non-blank strings. Public examples use only abstract identifiers.

## Root fields

`schema_version`
: Required string. The current value is `"1.0"`.

`personality_id`
: Required non-blank string. This is the stable key for one personality across
  prepared input and derived artifacts.

`personality`
: Required object containing `profile` and `long_profile`.

`interviews`
: Required non-empty array of interview records.

No other root fields are accepted.

## Personality fields

`profile`
: Required string containing the short personality profile used by the
  short-profile generation condition.

`long_profile`
: Required string containing the extended personality profile used by the
  long-profile generation condition. Hybrid uses training question-and-response
  pairs only and does not consume either profile field.

No other fields are accepted in `personality`.

## Interview record fields

Each object in `interviews` is one interview record.

`interview_id`
: Required non-blank string. It must be unique within the
  `prepared_input.json` document.

`sequence`
: Required non-negative integer. Lower values are earlier and higher values are
  later. Sequence values must be unique within the document and determine the
  chronological split; JSON array order does not.

`qa_pairs`
: Required non-empty array of question-and-response pairs from this interview
  record.

No other fields are accepted in an interview record.

## Question-and-response fields

`qa_id`
: Required non-blank string. It must be unique within the
  `prepared_input.json` document.

`question`
: Required non-blank string containing the prepared interviewer question.

`response`
: Required non-blank string containing the prepared interview response.

`tags`
: Required array of unique, non-blank strings. Use an empty array when no tags
  are assigned.

No other fields are accepted in a question-and-response pair.

## Abstract placeholder example

The following complete document shows structure only. Every value is invented
or an abstract placeholder.

```json
{
  "schema_version": "1.0",
  "personality_id": "PERSONALITY_001",
  "personality": {
    "profile": "<abstract short profile>",
    "long_profile": "<abstract extended profile>"
  },
  "interviews": [
    {
      "interview_id": "INTERVIEW_001_001",
      "sequence": 1,
      "qa_pairs": [
        {
          "qa_id": "QA_001_001",
          "question": "<abstract question>",
          "response": "<abstract response>",
          "tags": ["<abstract tag>"]
        }
      ]
    },
    {
      "interview_id": "INTERVIEW_001_002",
      "sequence": 2,
      "qa_pairs": [
        {
          "qa_id": "QA_001_002",
          "question": "<abstract question>",
          "response": "<abstract response>",
          "tags": []
        }
      ]
    }
  ]
}
```

This example is not paper data and carries no empirical meaning.

## Chronological holdout

The framework splits at the interview-record level:

1. Sort `interviews` by ascending `sequence`.
2. Place the latest `ceil(0.20 * N)` interview records in the test partition,
   where `N` is the number of interview records.
3. Use the remaining earliest interview records as training data.

At least one interview record must remain in each partition. Every `qa_pair`
from an interview record stays in that record's partition. There is no
input-level `split` field.

Training question-and-response pairs may be selected as grounding examples.
For held-out pairs, `question` is supplied for response generation and the
matching `response` remains hidden until evaluation.

## Synthetic examples

Each
`examples/synthetic_examples/personalities/PERSONALITY_XXX/prepared_input.json`
file is actual input accepted by the loader and follows this schema. The
examples were authored entirely from scratch for this repository from ten
generic fictional roles, with five short interviews each; they were never
sampled from or transformed from research transcripts. In total, they contain
150 Q&As: 120 train and 30 test.

Sibling files containing splits, summaries, atomic questions, MCQs, generated
responses, and metric results were generated deterministically as reference
outputs. They illustrate derived artifact formats and are not additional
loader inputs. The synthetic examples support format inspection only and
cannot reproduce the paper's reported numbers.

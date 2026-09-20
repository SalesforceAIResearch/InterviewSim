# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Generate deterministic, entirely fictional interview examples."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from typing import Any, Sequence


SCHEMA_VERSION = "1.0"
FIXTURE_ID = "SYNTHETIC_EXAMPLES"
GENERATION_SEED = 20260831
PERSONALITY_COUNT = 10
INTERVIEW_COUNT = 5
QA_PER_INTERVIEW = 3
TRAIN_INTERVIEW_ORDINALS = (1, 2, 3, 4)
TEST_INTERVIEW_ORDINALS = (5,)
FACT_COUNT = ATOMIC_QA_COUNT = MCQ_COUNT = RESPONSE_COUNT = 3
OPTION_KINDS = ("correct", "near_miss", "plausible_misconception", "opposite_negation")
TRAITS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")
TRAIT_LEVELS = ("Low", "Neutral", "High")
CONTENT_SCORES = (5, 5, 5)
FACTUAL_LABELS = ("Entailment", "Entailment", "Entailment")

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "examples" / "synthetic_examples"
LEGACY_FIXTURE_ROOT = REPO_ROOT / "examples" / ("synthetic_" + str(10))


def interview(tags: tuple[str, str], *pairs: tuple[str, str]) -> dict[str, Any]:
    return {"tags": tags, "pairs": pairs}


PROFILES: tuple[dict[str, Any], ...] = (
    {
        "role": "community workshop designer",
        "profile": "A community workshop designer who creates practical sessions for neighbors and small groups.",
        "long_profile": (
            "This facilitator favors welcoming rooms, clear choices, and shared making. "
            "They answer reflectively and keep returning to quieter participants."
        ),
        "interviews": (
            interview(
                ("welcome", "participation"),
                (
                    "When people enter a workshop for the first time, what do you notice?",
                    "I notice who pauses at the doorway and who looks for instructions. I offer one small choice so nobody has to perform confidence immediately.",
                ),
                (
                    "Does that choice ever slow down the opening?",
                    "A little, and that is usually useful. The room settles while people decide how they want to join.",
                ),
                (
                    "What tells you the welcome has worked?",
                    "Conversation starts moving sideways instead of only toward me. Quiet participants begin adding details without being invited by name.",
                ),
            ),
            interview(
                ("structure", "choice"),
                (
                    "How much structure do you give a group at the outset?",
                    "I show the whole path, but I keep the first step very clear. People relax when they can see both the boundary and their options.",
                ),
                (
                    "What happens when there are too many options?",
                    "The choice starts feeling like another assignment. I narrow it to two useful routes and let the group add a third.",
                ),
                (
                    "Have you become more comfortable changing the plan?",
                    "Yes, although I still name what is changing and why. A flexible session should not feel like the facilitator has stopped paying attention.",
                ),
            ),
            interview(
                ("practice", "collaboration"),
                (
                    "Why do you use making exercises instead of beginning with discussion?",
                    "Materials give attention somewhere to land. People can reveal an idea through their hands before they are ready to explain it.",
                ),
                (
                    "How do you keep one confident person from taking over?",
                    "I divide the task into different contributions rather than equal turns. That makes leadership useful without making it dominant.",
                ),
                (
                    "What do you listen for while everyone is working?",
                    "I listen for instructions being repeated by participants in their own words. That usually means the activity has become shared rather than delivered.",
                ),
            ),
            interview(
                ("feedback", "listening"),
                (
                    "You often collect feedback quietly. What does that reveal?",
                    "Written comments are sometimes sharper and kinder at the same time. People describe a specific moment instead of judging the whole session.",
                ),
                (
                    "Do spoken comments still matter to you?",
                    "Absolutely, because tone and hesitation carry information. I compare the two forms without treating either one as the honest version.",
                ),
                (
                    "How does feedback change the next workshop?",
                    "I choose one pattern to address and say what I changed. Participants should be able to see that listening led to a decision.",
                ),
            ),
            interview(
                ("adaptation", "learning"),
                (
                    "How do you plan for people with very different experience?",
                    "I prepare a basic task that stands on its own and an extension that adds responsibility. Nobody has to leave the group to find an appropriate challenge.",
                ),
                (
                    "What do you ask experienced participants to do?",
                    "I ask them to notice what helps the table move together. Expertise becomes generous when it creates room instead of setting the pace.",
                ),
                (
                    "What would you change in your next mixed group?",
                    "I would let participants decide when the extension becomes useful. That choice may show me forms of difficulty I did not anticipate.",
                ),
            ),
        ),
    },
    {
        "role": "independent audio producer",
        "profile": "An independent audio producer who records small ensembles and shapes intimate listening experiences.",
        "long_profile": (
            "This producer notices subtle shifts in texture and prefers restrained editing. "
            "Their voice is concise, sensory, and focused on what can actually be heard."
        ),
        "interviews": (
            interview(
                ("recording", "space"),
                (
                    "How do you learn what a small room will contribute to a recording?",
                    "I walk through it while someone plays softly. The corners tell me more than a loud test ever does.",
                ),
                (
                    "What are you hearing for in those corners?",
                    "I want warmth that fades cleanly, not a bright smear. If a quick phrase loses its edge, I move before I adjust anything.",
                ),
                (
                    "Can an imperfect room become part of the sound?",
                    "Often it is the most memorable part. I keep the irregularity when it supports the performance rather than announcing itself.",
                ),
            ),
            interview(
                ("voice", "clarity"),
                (
                    "What makes a recorded voice feel close without sounding exaggerated?",
                    "Breath has to remain ordinary and consonants need space. I set a comfortable distance before I think about polish.",
                ),
                (
                    "How do you handle a phrase that suddenly turns sharp?",
                    "I reduce the pressure around it instead of sanding off the edge. The sharpness may be carrying the sentence.",
                ),
                (
                    "Where do you draw the line between clarity and correction?",
                    "Clarity lets me follow the thought. Correction becomes distracting when I start hearing the repair instead of the person.",
                ),
            ),
            interview(
                ("rhythm", "texture"),
                (
                    "What attracts you to building rhythm from ordinary sounds?",
                    "A scrape or tap already has a history in it. The uneven surface gives the pulse a human weight.",
                ),
                (
                    "How do you stop a repeated sound from becoming mechanical?",
                    "I shift one hit slightly behind the others. That tiny drag can make the whole pattern breathe.",
                ),
                (
                    "Do you decide the pattern before recording the sounds?",
                    "Rarely. I collect short gestures first, then the rhythm suggests which ones belong together.",
                ),
            ),
            interview(
                ("editing", "energy"),
                (
                    "What is your first question when you begin an edit?",
                    "I ask where my attention actually breaks. A rough passage can stay if the performance still feels like one decision.",
                ),
                (
                    "Why can a cleaner edit lose energy?",
                    "Too many joins flatten the pressure between phrases. Everything becomes correct, but nothing seems to be arriving.",
                ),
                (
                    "How do you know when to stop?",
                    "I listen once without looking at any marks. If I forget the edits and follow the motion, the work is probably done.",
                ),
            ),
            interview(
                ("review", "balance"),
                (
                    "Describe your final listening pass.",
                    "I play the whole piece quietly and keep my hands away from the controls. Balance problems become obvious when volume cannot create excitement.",
                ),
                (
                    "What if you have become too familiar with the material?",
                    "I leave it alone long enough for the sequence to feel slightly surprising again. Distance restores honest attention.",
                ),
                (
                    "Would you bring another listener into that stage?",
                    "Yes, but I ask where their focus drifted rather than whether they liked it. That answer gives me something I can hear for myself.",
                ),
            ),
        ),
    },
    {
        "role": "science educator",
        "profile": "A science educator who helps learners investigate everyday questions through evidence and simple demonstrations.",
        "long_profile": (
            "This educator treats confusion as useful, asks for predictions, and uses concrete comparisons. "
            "Their answers are orderly, curious, and encouraging."
        ),
        "interviews": (
            interview(
                ("concepts", "curiosity"),
                (
                    "How do you introduce an idea that is completely unfamiliar?",
                    "I start with a situation learners can picture and ask what they expect. A definition becomes useful only after there is something to explain.",
                ),
                (
                    "What if their predictions are far from the result?",
                    "That gap is excellent material. We name what surprised us before anyone worries about being wrong.",
                ),
                (
                    "When do you finally introduce the formal term?",
                    "I wait until the group needs a shorter way to describe the pattern. Then the term answers a need they already feel.",
                ),
            ),
            interview(
                ("demonstration", "evidence"),
                (
                    "What makes a tabletop demonstration worth using?",
                    "One visible change should answer one clear question. Extra motion may be entertaining, but it can hide the relationship we need to inspect.",
                ),
                (
                    "How much do learners handle the materials themselves?",
                    "As much as safety allows. Touching the setup reveals assumptions that watching me would leave invisible.",
                ),
                (
                    "Do you ever let them redesign the demonstration?",
                    "Yes, after they can explain what each part is doing. Redesign turns understanding into a test rather than a recital.",
                ),
            ),
            interview(
                ("questions", "inquiry"),
                (
                    "A learner asks something you cannot answer. What do you say?",
                    "I say that I do not know yet and repeat the question carefully. Then we separate what we know from what we would need to observe.",
                ),
                (
                    "Does admitting uncertainty weaken your authority?",
                    "It changes the kind of authority I am offering. Careful uncertainty models the practice I want learners to use.",
                ),
                (
                    "How do you keep unanswered questions from disappearing?",
                    "We keep a short list and choose one to revisit. Returning to it shows that curiosity can have a longer life than a lesson.",
                ),
            ),
            interview(
                ("reasoning", "comparison"),
                (
                    "Why do learners confuse evidence with explanation?",
                    "A confident explanation sounds complete, while an observation often sounds plain. I place the two side by side so their different jobs are visible.",
                ),
                (
                    "What question helps them separate those jobs?",
                    "I ask what another possible result would have looked like. That makes the interpretation answerable to evidence.",
                ),
                (
                    "Can two explanations survive the same observation?",
                    "Certainly, and that is an important discovery. We then design the next observation to distinguish between them.",
                ),
            ),
            interview(
                ("revision", "learning"),
                (
                    "How can you tell where a lesson lost the group?",
                    "I look for the first moment when answers begin to diverge for unrelated reasons. That usually marks a step I made too large.",
                ),
                (
                    "Is your instinct to explain that step in more detail?",
                    "It used to be. Now I replace part of the explanation with one concrete comparison and let learners describe the connection.",
                ),
                (
                    "What will you ask learners after the revision?",
                    "I will ask which transition felt abrupt and what they expected next. Their wording will guide the next change better than a general rating.",
                ),
            ),
        ),
    },
    {
        "role": "archival editor",
        "profile": "An archival editor who organizes fragmented records and writes careful context for future readers.",
        "long_profile": (
            "This editor values uncertainty and separates evidence from interpretation. "
            "Their answers are measured, precise, and comfortable with unresolved questions."
        ),
        "interviews": (
            interview(
                ("organization", "context"),
                (
                    "Where do you begin with a box of scattered notes?",
                    "I identify the clearest relationships before I invent categories. The disorder may still preserve how the notes were once used.",
                ),
                (
                    "What if two arrangements seem equally reasonable?",
                    "I record both possibilities and explain the choice I made. Organization always contains interpretation, even when the labels look neutral.",
                ),
                (
                    "How do you test whether the arrangement helps?",
                    "I give it to a reader who knows none of the material. Their first wrong turn often exposes my hidden assumption.",
                ),
            ),
            interview(
                ("uncertainty", "transcription"),
                (
                    "How do you handle a phrase you can only partly read?",
                    "I transcribe what is visible and mark the gap plainly. A likely completion should not quietly become the record.",
                ),
                (
                    "Do you include your best guess anywhere?",
                    "Sometimes, but I label it as a proposed reading. The distinction lets another reader disagree without undoing the transcription.",
                ),
                (
                    "Why preserve ambiguity when it frustrates readers?",
                    "Because the uncertainty is information about the material. Removing it gives the page a confidence it never had.",
                ),
            ),
            interview(
                ("description", "readers"),
                (
                    "What belongs in a short contextual description?",
                    "I state what the material contains and why its arrangement matters. Background enters only when a reader needs it to orient themselves.",
                ),
                (
                    "How do you avoid telling readers what to conclude?",
                    "I separate description from interpretation and use concrete verbs. A clear account can open inquiry without directing it.",
                ),
                (
                    "Who should test that description?",
                    "Readers from different fields are especially useful. Each one notices a term I assumed was ordinary.",
                ),
            ),
            interview(
                ("conflict", "evidence"),
                (
                    "Two records disagree about the same event. What comes first?",
                    "I place the accounts beside each other before trying to reconcile them. Disagreement deserves to be represented, not merely solved.",
                ),
                (
                    "Can polished writing make one account seem stronger?",
                    "Very easily. I compare concrete details so style does not stand in for reliability.",
                ),
                (
                    "What if the conflict cannot be resolved?",
                    "Then the note should preserve the competing interpretations. An unresolved limit is more useful than a tidy invention.",
                ),
            ),
            interview(
                ("access", "navigation"),
                (
                    "How do you prepare complex material for a first-time reader?",
                    "I offer several entry points and explain what each path emphasizes. The guide should orient curiosity without narrowing it.",
                ),
                (
                    "Is there a risk of providing too much guidance?",
                    "Yes, because a detailed map can make discovery feel prescribed. I keep optional context separate from the first route.",
                ),
                (
                    "What would you like to learn from reader testing?",
                    "I want to see where browsing turns into close study. That transition will show whether the navigation supports both kinds of attention.",
                ),
            ),
        ),
    },
    {
        "role": "food-systems researcher",
        "profile": "A food-systems researcher who studies everyday movement, waste, and decision-making around food.",
        "long_profile": (
            "This researcher combines observation with respectful conversation and looks for recognizable patterns. "
            "Their answers are practical, cautious, and grounded in ordinary routines."
        ),
        "interviews": (
            interview(
                ("distribution", "observation"),
                (
                    "What can you learn by following one food item through its journey?",
                    "I can see where a small delay changes quality, cost, or responsibility. The handoffs reveal more than the endpoints.",
                ),
                (
                    "Which parts of that journey are easiest to miss?",
                    "Informal exchanges often disappear from written records. I ask workers what happens between the steps everyone thinks are official.",
                ),
                (
                    "How do you avoid treating one route as typical?",
                    "I compare it with a smoother route and one with repeated delays. The contrast keeps a vivid example from becoming a general claim.",
                ),
            ),
            interview(
                ("interviews", "work"),
                (
                    "How do you invite market workers to describe their routines?",
                    "I ask about one ordinary shift and let the sequence unfold. Specific actions are easier to correct than broad opinions.",
                ),
                (
                    "What details do people assume you already understand?",
                    "They often skip the tiny adjustments that keep work moving. A step-by-step retelling brings those invisible decisions back.",
                ),
                (
                    "Do participants get to review your interpretation?",
                    "Yes, I return a plain summary and ask what feels incomplete. Correction is part of the evidence, not a courtesy after it.",
                ),
            ),
            interview(
                ("waste", "measurement"),
                (
                    "How do you measure household food waste without creating a burden?",
                    "I use a short observation period and a few realistic categories. A perfect diary is useless if nobody can maintain it.",
                ),
                (
                    "Which distinction matters most in those categories?",
                    "I separate avoidable scraps from necessary remains. That distinction connects the measure to choices a household can actually change.",
                ),
                (
                    "What do incomplete records tell you?",
                    "They tell me where the method fought with daily life. Missing entries can improve the next design if I treat them as evidence.",
                ),
            ),
            interview(
                ("habits", "comparison"),
                (
                    "Why are routine food habits hard to recall accurately?",
                    "Special occasions crowd out ordinary weeks in memory. I ask for repeated choices rather than the most memorable meal.",
                ),
                (
                    "How do you check those recollections?",
                    "A brief set of purchase notes gives me a second view. I compare patterns without assuming either record is complete.",
                ),
                (
                    "What makes a comparison fair across households?",
                    "The categories must fit different routines without ranking them. Variation is part of the system, not noise to remove.",
                ),
            ),
            interview(
                ("communication", "findings"),
                (
                    "How do you share findings so residents recognize their own experience?",
                    "I begin with a familiar pattern and show several paths through it. A single average can hide the decisions people actually make.",
                ),
                (
                    "What do residents add that your analysis cannot?",
                    "They identify missing explanations and name constraints I flattened. Their response changes the interpretation, not just the presentation.",
                ),
                (
                    "What will you try in the next discussion?",
                    "I will ask small groups to annotate one pattern before I explain it. That should reveal where my language is too broad.",
                ),
            ),
        ),
    },
    {
        "role": "theatre director",
        "profile": "A theatre director who builds ensemble trust and develops scenes through clear, playable choices.",
        "long_profile": (
            "This director treats rehearsal as shared investigation and gives concrete notes. "
            "Their answers are energetic, candid, and centered on action."
        ),
        "interviews": (
            interview(
                ("ensemble", "rehearsal"),
                (
                    "What should the first exercise give an ensemble?",
                    "It should offer a real task without demanding instant confidence. Shared attention matters more than looking unified.",
                ),
                (
                    "How do you work with different energy levels in the room?",
                    "I repeat a physical action at several speeds. The group can arrive together without pretending everyone arrived the same way.",
                ),
                (
                    "When do you know rehearsal has truly begun?",
                    "Someone responds to a detail another performer offered. At that point the room is making something, not merely warming up.",
                ),
            ),
            interview(
                ("scene", "action"),
                (
                    "A difficult scene has stalled in discussion. What do you do?",
                    "I ask each performer to choose one immediate action and try it. Movement reveals the question faster than another explanation.",
                ),
                (
                    "What if the first choice is obviously wrong?",
                    "Good, then we have something concrete to reject. A failed action is more generous than a vague agreement.",
                ),
                (
                    "How do you return to the text after that experiment?",
                    "We notice which words gained pressure under the action. Those moments show where the scene is already asking to move.",
                ),
            ),
            interview(
                ("direction", "practice"),
                (
                    "What makes a note playable for a performer?",
                    "It names a behavior that can change on the next attempt. An adjective often describes a result without giving anyone a route.",
                ),
                (
                    "Can you give a note that is too specific?",
                    "Certainly, especially if I prescribe every gesture. I want precision about the problem and freedom in the solution.",
                ),
                (
                    "How do performers participate in shaping the note?",
                    "I ask them to translate it into their own action. Their version is often sharper because it comes from inside the scene.",
                ),
            ),
            interview(
                ("pace", "listening"),
                (
                    "How do you diagnose a scene that feels slow?",
                    "I mark where attention drifts instead of asking everyone to hurry. Speed can hide an unclear reason for speaking.",
                ),
                (
                    "What usually restores the pace?",
                    "A stronger need for the next line does more than cutting pauses. Timing follows necessity when performers are actually listening.",
                ),
                (
                    "Do you test pauses deliberately?",
                    "Yes, we move one pause through the scene and watch what changes. The right silence gathers pressure rather than releasing it.",
                ),
            ),
            interview(
                ("inclusion", "ensemble"),
                (
                    "How do you make room for performers who process quietly?",
                    "I alternate open discussion with private preparation. Presence does not have to arrive through speed or volume.",
                ),
                (
                    "What changes when the group adopts that rhythm?",
                    "Ideas become less competitive and more detailed. People respond to what was offered instead of racing to offer first.",
                ),
                (
                    "What experiment would you take into the next rehearsal?",
                    "I would let changing pairs lead a silent scene plan. That may distribute authority without turning inclusion into a speech.",
                ),
            ),
        ),
    },
    {
        "role": "accessibility designer",
        "profile": "An accessibility designer who makes everyday information and interactions clearer for people with varied needs.",
        "long_profile": (
            "This designer begins with reported barriers and tests concrete tasks. "
            "Their answers are direct, systematic, and quietly empathetic."
        ),
        "interviews": (
            interview(
                ("forms", "clarity"),
                (
                    "What is your first move when a form feels confusing?",
                    "I complete it without using background knowledge and mark every hesitation. Small ambiguities often reveal a broken sequence.",
                ),
                (
                    "Where should guidance appear?",
                    "Beside the decision it explains, not after the error. Timing is part of whether an instruction is accessible.",
                ),
                (
                    "How do you test a revised order?",
                    "I ask first-time readers to narrate what they expect next. Their expectation shows whether the form is carrying its own logic.",
                ),
            ),
            interview(
                ("navigation", "interaction"),
                (
                    "What does keyboard testing reveal beyond whether controls work?",
                    "It reveals whether a person can stay oriented while moving. Access to an action means little if the current position disappears.",
                ),
                (
                    "How do you make that position unmistakable?",
                    "I use a visible focus that survives changes in contrast and layout. The cue should not depend on memory.",
                ),
                (
                    "Why test the path in reverse?",
                    "Complex sections may trap someone only on the way back. Reverse testing exposes assumptions hidden by the expected route.",
                ),
            ),
            interview(
                ("instructions", "language"),
                (
                    "What belongs at the start of a plain instruction?",
                    "The next action belongs first, usually as a direct verb. Background detail can wait until the reader has a path.",
                ),
                (
                    "How do you handle an important exception?",
                    "I place it after the ordinary case and label it clearly. An exception should not make every reader solve the hardest version.",
                ),
                (
                    "Is shorter language always more accessible?",
                    "No, because missing context can create extra work. I prefer layered detail over either density or unexplained brevity.",
                ),
            ),
            interview(
                ("captions", "description"),
                (
                    "How do you decide what a description must include?",
                    "I identify what changes the meaning or the next action. Listing every visible detail can compete with the content.",
                ),
                (
                    "What makes a caption feel well timed?",
                    "It arrives with enough space to read without racing the scene. Rhythm matters alongside accuracy.",
                ),
                (
                    "How do user comparisons improve this work?",
                    "People can compare concise and detailed versions on the same task. Their effort tells me more than my preference.",
                ),
            ),
            interview(
                ("priorities", "barriers"),
                (
                    "Several accessibility problems are reported at once. How do you rank them?",
                    "I connect each barrier to a real task and look first for blocked actions. Visible polish should not outrank someone being unable to continue.",
                ),
                (
                    "Where does frequency fit into that decision?",
                    "Frequency matters, but severity can outweigh it. I document both so the order remains open to challenge.",
                ),
                (
                    "What would make the repair process more accountable?",
                    "I would publish a short rationale and retest the affected tasks. A completed change is not the same as a removed barrier.",
                ),
            ),
        ),
    },
    {
        "role": "urban gardener",
        "profile": "An urban gardener who tends compact shared plots and teaches practical growing skills.",
        "long_profile": (
            "This gardener observes slowly, experiments on a small scale, and values resilient soil. "
            "Their answers are warm, concrete, and comfortable with failure."
        ),
        "interviews": (
            interview(
                ("soil", "patience"),
                (
                    "What do you look for before improving tired soil?",
                    "I feel the texture and check moisture below the surface. The soil usually tells me whether it needs air, cover, or time.",
                ),
                (
                    "Why avoid a quick treatment?",
                    "A quick change can feed a plant while leaving poor structure untouched. I would rather build the ground slowly.",
                ),
                (
                    "How do you know a gentle treatment is working?",
                    "Water begins soaking in evenly and roots spread more freely. Those quiet changes matter before the leaves look impressive.",
                ),
            ),
            interview(
                ("planting", "diversity"),
                (
                    "How do you plan mixed planting in a small bed?",
                    "I watch where shade travels and give slower plants breathing room. Diversity still needs deliberate spacing.",
                ),
                (
                    "What do vigorous plants teach you?",
                    "They show how quickly abundance can become crowding. I trim or move them before they turn success into competition.",
                ),
                (
                    "Do you record which combinations work?",
                    "I keep short notes through the growing cycle. Memory tends to favor the final harvest and forget the middle struggle.",
                ),
            ),
            interview(
                ("water", "observation"),
                (
                    "What is the most common mistake with watering containers?",
                    "People wet the surface often without reaching the roots. A deeper check prevents that comforting but wasteful habit.",
                ),
                (
                    "How does wind change your routine?",
                    "Wind can dry a container before the air feels hot. I check exposed edges rather than trusting a fixed schedule.",
                ),
                (
                    "What simple experiment would you run?",
                    "I would compare two covers that slow evaporation. The goal is steady moisture, not simply fewer watering trips.",
                ),
            ),
            interview(
                ("harvest", "sharing"),
                (
                    "What does sharing a small harvest add to a garden?",
                    "It creates conversation even when the portions are modest. Produce becomes a reason to ask what a neighbor can use.",
                ),
                (
                    "How do you divide an uneven harvest fairly?",
                    "I ask before I distribute it and avoid pretending every portion must match. Fairness begins with usefulness.",
                ),
                (
                    "Would you connect sharing with another activity?",
                    "I like pairing it with a seed exchange. That lets a small harvest point toward another season of participation.",
                ),
            ),
            interview(
                ("seedlings", "learning"),
                (
                    "When seedlings fail, where do you investigate first?",
                    "I compare roots, moisture, and light before changing anything. Several causes can leave the same sad leaves.",
                ),
                (
                    "How do you keep the next trial informative?",
                    "I change one condition and leave the others alone. A smaller experiment gives failure somewhere useful to go.",
                ),
                (
                    "What would you add to the shared garden?",
                    "I would keep one small bed for repeat trials. It could make uncertainty visible without putting the whole harvest at risk.",
                ),
            ),
        ),
    },
    {
        "role": "public-interest technologist",
        "profile": "A public-interest technologist who improves digital services used for essential civic tasks.",
        "long_profile": (
            "This technologist values simple processes, restrained data collection, and understandable maintenance. "
            "Their answers are analytical, plainspoken, and skeptical of unnecessary complexity."
        ),
        "interviews": (
            interview(
                ("services", "simplicity"),
                (
                    "How do you simplify an application built around complicated rules?",
                    "I trace the shortest successful path and separate policy from the questions people must answer. Complex rules do not require confusing screens.",
                ),
                (
                    "What repeated burden do you look for?",
                    "I look for information requested twice in slightly different language. Repetition often signals that the service is organized around offices rather than people.",
                ),
                (
                    "How do you know a simpler path is still accurate?",
                    "I test it against ordinary and difficult cases. Simplicity should remove needless work, not hide a consequential choice.",
                ),
            ),
            interview(
                ("privacy", "records"),
                (
                    "What is the safest way to protect sensitive records?",
                    "Collect less in the first place and keep each field for a stated reason. Restraint reduces risk and user burden together.",
                ),
                (
                    "Why do teams keep information they do not need?",
                    "Availability feels like future value, while deletion feels final. I ask what decision the information actually supports.",
                ),
                (
                    "Where would you begin a privacy review?",
                    "I would follow one record from collection to deletion. Every unexplained pause in that journey deserves a decision.",
                ),
            ),
            interview(
                ("testing", "residents"),
                (
                    "What do residents reveal that an internal review misses?",
                    "A real task exposes assumptions about language, time, and prior knowledge. Internal reviewers often step around those barriers automatically.",
                ),
                (
                    "How do you keep observers from helping too soon?",
                    "I ask them to wait until a participant describes the problem. Silence produces better evidence than a well-meant hint.",
                ),
                (
                    "What makes a short testing session useful?",
                    "One ordinary goal is enough if the observation is careful. Depth comes from tracing the barrier, not adding more tasks.",
                ),
            ),
            interview(
                ("automation", "explanation"),
                (
                    "What should an explanation of an automated decision accomplish?",
                    "It should name the factors that changed the outcome and support a next step. Technical detail alone does neither.",
                ),
                (
                    "How do you test whether people understand it?",
                    "I ask what they could question or do differently. Their answer shows whether the explanation supports action.",
                ),
                (
                    "What warning sign tells you the explanation is too abstract?",
                    "People repeat its wording but cannot connect it to their situation. Familiar words are not the same as useful meaning.",
                ),
            ),
            interview(
                ("maintenance", "reliability"),
                (
                    "Why treat maintenance as a public-interest concern?",
                    "A service is useful only while someone can repair it. Reliability depends on ordinary care, not a dramatic launch.",
                ),
                (
                    "How do you uncover fragile knowledge?",
                    "I ask someone new to perform a routine task from the notes. Every private explanation marks knowledge the service has not retained.",
                ),
                (
                    "What improvement would you make next?",
                    "I would place short operational notes beside each recurring task. A real handoff will test whether those notes are enough.",
                ),
            ),
        ),
    },
    {
        "role": "youth sports coach",
        "profile": "A youth sports coach who builds safe, skill-focused practices for young players with varied experience.",
        "long_profile": (
            "This coach emphasizes steady improvement, shared responsibility, and clear boundaries around competition. "
            "Their answers are upbeat, brief, and focused on observable effort."
        ),
        "interviews": (
            interview(
                ("welcome", "teamwork"),
                (
                    "What does a new player need in the first few minutes?",
                    "They need one clear task and a teammate who will stay nearby. Belonging grows faster when nobody has to guess where to stand.",
                ),
                (
                    "How do you keep the pace from overwhelming them?",
                    "I explain one activity at a time and show where they can pause. A calm entry is better than catching up in a rush.",
                ),
                (
                    "When does confidence begin to show?",
                    "The player starts asking a teammate a practical question. That small exchange matters more than looking fearless.",
                ),
            ),
            interview(
                ("movement", "safety"),
                (
                    "How do you teach a new movement safely?",
                    "I demonstrate it slowly and pause at the key balance point. Players should understand the shape before chasing speed.",
                ),
                (
                    "What can a partner notice during practice?",
                    "A partner can watch one simple cue rather than judge the whole motion. Focused observation helps both players learn.",
                ),
                (
                    "When is the group ready to move faster?",
                    "They are ready when control survives a little pressure. Speed is the result of stable movement, not proof of it.",
                ),
            ),
            interview(
                ("competition", "learning"),
                (
                    "How do you keep competition connected to learning?",
                    "We choose one skill goal before play begins. The score stays real, but it does not become the only evidence.",
                ),
                (
                    "What if players abandon that goal in a close game?",
                    "I stop briefly and ask them to name one useful decision. Reflection can return without draining the excitement.",
                ),
                (
                    "Do players help set team goals?",
                    "Yes, because they notice challenges I may miss. A goal they can explain is easier to carry into play.",
                ),
            ),
            interview(
                ("resilience", "reflection"),
                (
                    "What do you say immediately after a tough loss?",
                    "I make room for disappointment and ask for one accurate observation. Advice can wait until blame has lost its grip.",
                ),
                (
                    "How do you respond when criticism turns toward teammates?",
                    "I separate the feeling from the next action. Players can be upset without making another person the explanation.",
                ),
                (
                    "What helps the group recover at the next practice?",
                    "A short player-led reflection gives the loss a boundary. Then we return to a skill everyone can improve.",
                ),
            ),
            interview(
                ("families", "communication"),
                (
                    "How do you explain a family's role around practice?",
                    "I describe support as curiosity, rest, and one consistent cue. Young players do better without several adults coaching at once.",
                ),
                (
                    "What if an adult disagrees with your approach?",
                    "I ask which part worries them and return to the learning goal. A specific conversation is healthier than competing instructions.",
                ),
                (
                    "How would you involve families next time?",
                    "I would invite them to observe one skill-focused practice. Seeing the routine may make encouragement simpler and more consistent.",
                ),
            ),
        ),
    },
)


def personality_id(ordinal: int) -> str:
    return f"PERSONALITY_{ordinal:03d}"


def interview_id(personality_ordinal: int, interview_ordinal: int) -> str:
    return f"INTERVIEW_{personality_ordinal:03d}_{interview_ordinal:03d}"


def qa_id(personality_ordinal: int, qa_ordinal: int) -> str:
    return f"QA_{personality_ordinal:03d}_{qa_ordinal:04d}"


def build_prepared_input(ordinal: int) -> dict[str, Any]:
    spec = PROFILES[ordinal - 1]
    interviews = []
    for interview_ordinal, dialogue in enumerate(spec["interviews"], start=1):
        pairs = []
        for turn, (question, response) in enumerate(dialogue["pairs"], start=1):
            qa_ordinal = (interview_ordinal - 1) * QA_PER_INTERVIEW + turn
            pairs.append(
                {
                    "qa_id": qa_id(ordinal, qa_ordinal),
                    "question": question,
                    "response": response,
                    "tags": list(dialogue["tags"]),
                }
            )
        interviews.append(
            {
                "interview_id": interview_id(ordinal, interview_ordinal),
                "sequence": interview_ordinal,
                "qa_pairs": pairs,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "personality_id": personality_id(ordinal),
        "personality": {"profile": spec["profile"], "long_profile": spec["long_profile"]},
        "interviews": interviews,
    }


def held_out_pairs(prepared: dict[str, Any]) -> list[dict[str, Any]]:
    return prepared["interviews"][-1]["qa_pairs"]


def build_split(ordinal: int, prepared: dict[str, Any]) -> dict[str, Any]:
    train = prepared["interviews"][:-1]
    test = prepared["interviews"][-1:]
    train_qas = [qa for item in train for qa in item["qa_pairs"]]
    test_qas = [qa for item in test for qa in item["qa_pairs"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "personality_id": personality_id(ordinal),
        "synthetic_only": True,
        "unit": "interview",
        "train_sequences": list(TRAIN_INTERVIEW_ORDINALS),
        "test_sequences": list(TEST_INTERVIEW_ORDINALS),
        "train_interview_ids": [item["interview_id"] for item in train],
        "test_interview_ids": [item["interview_id"] for item in test],
        "train_qa_ids": [item["qa_id"] for item in train_qas],
        "test_qa_ids": [item["qa_id"] for item in test_qas],
        "counts": {
            "train_interviews": 4,
            "test_interviews": 1,
            "train_qas": 12,
            "test_qas": 3,
        },
    }


def build_fact_summary(ordinal: int, prepared: dict[str, Any]) -> dict[str, Any]:
    pairs = held_out_pairs(prepared)
    return {
        "schema_version": SCHEMA_VERSION,
        "personality_id": personality_id(ordinal),
        "synthetic_only": True,
        "summary": "The held-out interview develops three connected aspects of the speaker's working practice.",
        "facts": [
            {
                "fact_id": f"FACT_{ordinal:03d}_{position:03d}",
                "qa_id": pair["qa_id"],
                "text": pair["response"],
            }
            for position, pair in enumerate(pairs, start=1)
        ],
    }


def build_atomic_qas(ordinal: int, prepared: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "atomic_qa_id": f"ATOMIC_QA_{ordinal:03d}_{position:03d}",
            "personality_id": personality_id(ordinal),
            "qa_id": pair["qa_id"],
            "question": pair["question"],
            "answer": pair["response"],
        }
        for position, pair in enumerate(held_out_pairs(prepared), start=1)
    ]


def build_mcqs(
    ordinal: int, atomic_qas: list[dict[str, Any]], option_count: int
) -> list[dict[str, Any]]:
    answers = [item["answer"] for item in atomic_qas]
    records = []
    for position, atomic in enumerate(atomic_qas, start=1):
        alternative_positions = [index for index in range(3) if index != position - 1]
        specs = [
            (answers[position - 1], "correct"),
            (answers[alternative_positions[0]], "near_miss"),
            (answers[alternative_positions[1]], "plausible_misconception"),
        ]
        if option_count == 4:
            specs.append(
                (
                    "I would reject the approach described here and keep the existing routine unchanged.",
                    "opposite_negation",
                )
            )
        shift = (position - 1) % option_count
        specs = specs[shift:] + specs[:shift]
        options = [
            {
                "option_id": f"OPTION_{option_count}OPT_{ordinal:03d}_{position:03d}_{chr(64 + option_position)}",
                "text": text,
                "kind": kind,
            }
            for option_position, (text, kind) in enumerate(specs, start=1)
        ]
        correct = next(option for option in options if option["kind"] == "correct")
        records.append(
            {
                "mcq_id": f"MCQ_{option_count}OPT_{ordinal:03d}_{position:03d}",
                "personality_id": personality_id(ordinal),
                "qa_id": atomic["qa_id"],
                "atomic_qa_id": atomic["atomic_qa_id"],
                "option_count": option_count,
                "question": atomic["question"],
                "options": options,
                "correct_option_id": correct["option_id"],
                "rationale": "The correct option reproduces the answer to this held-out question; the alternatives come from related answers or reverse its intent.",
            }
        )
    return records


def build_generated_responses(ordinal: int, prepared: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "response_id": f"RESPONSE_{ordinal:03d}_{position:03d}",
            "personality_id": personality_id(ordinal),
            "qa_id": pair["qa_id"],
            "response": pair["response"],
        }
        for position, pair in enumerate(held_out_pairs(prepared), start=1)
    ]


def trait_profiles(ordinal: int) -> tuple[dict[str, str], dict[str, str]]:
    reference = {
        trait: TRAIT_LEVELS[(ordinal + index) % len(TRAIT_LEVELS)]
        for index, trait in enumerate(TRAITS)
    }
    generated = dict(reference)
    changed = TRAITS[(ordinal - 1) % len(TRAITS)]
    generated[changed] = {"Low": "Neutral", "Neutral": "High", "High": "Neutral"}[
        generated[changed]
    ]
    return reference, generated


def trait_runs(profile: dict[str, str]) -> dict[str, list[str]]:
    alternative = {"Low": "Neutral", "Neutral": "High", "High": "Neutral"}
    return {
        trait: [profile[trait], profile[trait], alternative[profile[trait]]] for trait in TRAITS
    }


def personality_alignment(reference: dict[str, str], generated: dict[str, str]) -> float:
    numeric = {"Low": 1, "Neutral": 2, "High": 3}
    distance = sum(abs(numeric[reference[trait]] - numeric[generated[trait]]) for trait in TRAITS)
    return round(1.0 - distance / 10.0, 3)


def reward_for_kind(kind: str) -> float:
    return 1.0 if kind == "correct" else -1.0 if kind == "opposite_negation" else -0.5


def build_metrics(
    ordinal: int,
    responses: list[dict[str, Any]],
    mcqs_3: list[dict[str, Any]],
    mcqs_4: list[dict[str, Any]],
) -> dict[str, Any]:
    explanations = (
        "The response preserves the full practical meaning of the held-out answer.",
        "The response preserves the full practical meaning of the held-out answer.",
        "The response preserves the full practical meaning of the held-out answer.",
    )
    factual_explanations = {
        "Entailment": "The response agrees with the fictional facts in the held-out answer.",
        "Neutral": "The response adds a plausible idea that the fictional facts do not settle.",
        "Contradiction": "The response conflicts with one fictional fact in the held-out answer.",
    }
    content = [
        {
            "response_id": item["response_id"],
            "score": CONTENT_SCORES[index],
            "explanation": explanations[index],
        }
        for index, item in enumerate(responses)
    ]
    factual = [
        {
            "response_id": item["response_id"],
            "label": FACTUAL_LABELS[index],
            "explanation": factual_explanations[FACTUAL_LABELS[index]],
        }
        for index, item in enumerate(responses)
    ]
    reference, generated = trait_profiles(ordinal)
    alignment = personality_alignment(reference, generated)

    def evaluate(mcqs: list[dict[str, Any]], kinds: tuple[str, ...]) -> list[dict[str, Any]]:
        results = []
        for mcq, kind in zip(mcqs, kinds):
            selected = next(option for option in mcq["options"] if option["kind"] == kind)
            results.append(
                {
                    "mcq_id": mcq["mcq_id"],
                    "selected_option_id": selected["option_id"],
                    "selected_option_kind": kind,
                    "accuracy": 1 if kind == "correct" else 0,
                    "reward": reward_for_kind(kind),
                }
            )
        return results

    evaluation_3 = evaluate(mcqs_3, ("correct", "near_miss", "plausible_misconception"))
    evaluation_4 = evaluate(mcqs_4, ("correct", "opposite_negation", "near_miss"))
    return {
        "schema_version": SCHEMA_VERSION,
        "personality_id": personality_id(ordinal),
        "synthetic_only": True,
        "content_similarity": content,
        "factual_consistency": factual,
        "personality_similarity": {
            "reference": {"trait_runs": trait_runs(reference), "modal_profile": reference},
            "generated": {"trait_runs": trait_runs(generated), "modal_profile": generated},
            "alignment": alignment,
        },
        "mcq_evaluation": {"three_option": evaluation_3, "four_option": evaluation_4},
        "aggregates": {
            "mean_content_similarity": 5.0,
            "contradiction_ratio": 0.0,
            "personality_alignment": alignment,
            "mcq_3_option_accuracy": 0.333,
            "mcq_3_option_mean_reward": 0.0,
            "mcq_4_option_accuracy": 0.333,
            "mcq_4_option_mean_reward": -0.167,
        },
    }


def collection_document(ordinal: int, name: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "personality_id": personality_id(ordinal),
        "synthetic_only": True,
        name: records,
    }


def summary_counts() -> dict[str, int]:
    return {
        "personality_count": 10,
        "prepared_input_count": 10,
        "interview_count": 50,
        "qa_count": 150,
        "train_qa_count": 120,
        "test_qa_count": 30,
        "fact_count": 30,
        "atomic_qa_count": 30,
        "mcq_3_option_count": 30,
        "mcq_4_option_count": 30,
        "generated_response_count": 30,
        "content_similarity_count": 30,
        "factual_consistency_count": 30,
        "personality_similarity_count": 10,
        "personality_similarity_run_count": 300,
        "mcq_3_option_evaluation_count": 30,
        "mcq_4_option_evaluation_count": 30,
    }


def profile_registry() -> list[dict[str, Any]]:
    return [
        {
            "personality_id": personality_id(ordinal),
            "role": spec["role"],
            "allowed_tags": sorted(
                {tag for dialogue in spec["interviews"] for tag in dialogue["tags"]}
            ),
        }
        for ordinal, spec in enumerate(PROFILES, start=1)
    ]


def build_manifest() -> dict[str, Any]:
    per_personality = [
        {
            "personality_id": personality_id(ordinal),
            "prepared_input_count": 1,
            "interview_count": 5,
            "train_interview_count": 4,
            "test_interview_count": 1,
            "qa_count": 15,
            "train_qa_count": 12,
            "test_qa_count": 3,
            "fact_count": 3,
            "atomic_qa_count": 3,
            "mcq_3_option_count": 3,
            "mcq_4_option_count": 3,
            "generated_response_count": 3,
            "content_similarity_count": 3,
            "factual_consistency_count": 3,
            "personality_similarity_count": 1,
            "personality_similarity_run_count": 30,
            "mcq_3_option_evaluation_count": 3,
            "mcq_4_option_evaluation_count": 3,
        }
        for ordinal in range(1, 11)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "synthetic_only": True,
        "generation_seed": GENERATION_SEED,
        "personality_ids": [personality_id(ordinal) for ordinal in range(1, 11)],
        "profile_registry": profile_registry(),
        "canonical_input_contract": {
            "top_level_fields": ["schema_version", "personality_id", "personality", "interviews"],
            "personality_fields": ["profile", "long_profile"],
            "interview_fields": ["interview_id", "sequence", "qa_pairs"],
            "qa_pair_fields": ["qa_id", "question", "response", "tags"],
        },
        "split_policy": {
            "unit": "interview",
            "train_sequences": [1, 2, 3, 4],
            "test_sequences": [5],
            "train_interview_count": 4,
            "test_interview_count": 1,
        },
        "expected_per_personality": {
            "interview_count": 5,
            "qa_per_interview": 3,
            "train_qa_count": 12,
            "test_qa_count": 3,
            "fact_count": 3,
            "atomic_qa_count": 3,
            "mcq_3_option_count": 3,
            "mcq_4_option_count": 3,
            "generated_response_count": 3,
        },
        "per_personality": per_personality,
        "totals": summary_counts(),
    }


def build_fixture_documents() -> dict[str, Any]:
    documents: dict[str, Any] = {"manifest.json": build_manifest()}
    for ordinal in range(1, 11):
        pid = personality_id(ordinal)
        prefix = f"personalities/{pid}"
        prepared = build_prepared_input(ordinal)
        atomic = build_atomic_qas(ordinal, prepared)
        mcqs_3 = build_mcqs(ordinal, atomic, 3)
        mcqs_4 = build_mcqs(ordinal, atomic, 4)
        responses = build_generated_responses(ordinal, prepared)
        documents[f"{prefix}/prepared_input.json"] = prepared
        documents[f"{prefix}/split.json"] = build_split(ordinal, prepared)
        documents[f"{prefix}/fact_summary.json"] = build_fact_summary(ordinal, prepared)
        documents[f"{prefix}/atomic_qas.json"] = collection_document(ordinal, "atomic_qas", atomic)
        documents[f"{prefix}/mcqs_3_option.json"] = collection_document(ordinal, "mcqs", mcqs_3)
        documents[f"{prefix}/mcqs_4_option.json"] = collection_document(ordinal, "mcqs", mcqs_4)
        documents[f"{prefix}/generated_responses.json"] = collection_document(
            ordinal, "generated_responses", responses
        )
        documents[f"{prefix}/metrics.json"] = build_metrics(ordinal, responses, mcqs_3, mcqs_4)
    return documents


def serialize(document: Any) -> str:
    return json.dumps(document, indent=2, ensure_ascii=True) + "\n"


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def resolve_fixture_root(output: Path) -> Path:
    candidate = output.expanduser()
    if ".." in candidate.parts:
        raise RuntimeError("fixture destination must not contain path traversal")
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    if candidate.is_symlink():
        raise RuntimeError("fixture destination must not be a symbolic link")
    destination = candidate.resolve(strict=False)
    repository_root = REPO_ROOT.resolve()
    if destination == destination.parent or path_is_within(repository_root, destination):
        raise RuntimeError("fixture destination must not contain the repository root")
    canonical = FIXTURE_ROOT.resolve(strict=False)
    if path_is_within(destination, repository_root) and destination != canonical:
        raise RuntimeError(
            "fixture destination inside the repository must be examples/synthetic_examples"
        )
    return destination


def prepare_fixture_root(output: Path, *, force: bool) -> Path:
    fixture_root = resolve_fixture_root(output)
    if fixture_root.exists():
        if not fixture_root.is_dir():
            raise RuntimeError("fixture destination exists and is not a directory")
        if not force:
            raise FileExistsError("fixture destination already exists; pass --force to replace it")
        shutil.rmtree(fixture_root)
    if fixture_root == FIXTURE_ROOT.resolve(strict=False) and force:
        legacy = LEGACY_FIXTURE_ROOT.resolve(strict=False)
        if legacy.is_dir() and not legacy.is_symlink():
            shutil.rmtree(legacy)
    fixture_root.mkdir(parents=True)
    return fixture_root


def generate(output: Path = FIXTURE_ROOT, *, force: bool = False) -> dict[str, int | str]:
    root = prepare_fixture_root(output, force=force)
    for relative, document in build_fixture_documents().items():
        path = root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialize(document), encoding="utf-8")
    return {"fixture_id": FIXTURE_ID, **summary_counts()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="generate deterministic fictional interview examples"
    )
    parser.add_argument("--output", type=Path, default=FIXTURE_ROOT)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = generate(args.output, force=args.force)
    except (FileExistsError, OSError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Sample session

One real run of `scripts/session.py`, kept so the Tutor Agent's output can be
read without spending anything. Illustrative, not a fixture: nothing tests
against it.

Regenerate with `python scripts/render_sample.py` after a session worth keeping.

| | |
| --- | --- |
| Text | strategy |
| Steps | all |
| Tutor prompt | `v1` |
| Assessment prompt | `v3` |
| Rubric | `v3` |
| Model | gemini-3.1-pro-preview |
| Attempts per step | 3 |
| Outcome | complete |
| Calls | 20 (12 tutor, 8 assessment) |
| Tokens | 55,845 in, 9,549 thinking, 3,091 out |
| Estimated cost | $0.2634 |

Some answers below are written to fail a specific criterion on purpose.

---

## State

**Tutor**

> Let's start by defining a "company's strategy." Please state what it is briefly, clearly, and in your own words.

**Student**

> Strategy is sort of the overall vibe a company is going for, the general direction they head in, which honestly changes a lot depending on who is running things and what is happening in the market that year, so it is quite hard to pin down exactly, but you know it when you see it.

**Assessment Agent:** FAIL on `Brevity`, `Clarity`, `Completeness`, `Accuracy`

**Tutor**

> That is an attempt, but your statement is too conversational, vague, and misses the essential elements of the concept while contradicting the text's definition. Here is what you failed: Brevity, Clarity, Completeness, Accuracy. Try stating the concept again in a concise, precise sentence that captures the essential core components and remains faithful to the reading.

**Student**

> A company's strategy is a set of cohesive moves that managers choose to set out in order to decide how they will go toe to toe with their rivals and earn more than them.

**Assessment Agent:** PASS

**Tutor**

> That is an excellent statement. You captured the core idea of a company's strategy clearly and concisely in your own words. That completes the State step.


## Elaborate

**Tutor**

> Now, let's elaborate. Expand on your statement at greater length so that the reader gets a fuller understanding of what a company's strategy entails. Explain the concept in more detail, going beyond just your initial definition.

**Student**

> So for instance if Jollibee decides to open a hundred more branches this year, that is their strategy. Meanwhile McDonald's might spend on advertising instead. Every company just picks whatever seems to work for them at the time and runs with it.

**Assessment Agent:** FAIL on `Completeness`, `Coherence`, `Accuracy`

**Tutor**

> You have made an attempt, but your response jumps straight into giving examples rather than expanding on the concept itself, misses the core elements of the definition, and includes a claim that contradicts the reading. Here is what you failed: Completeness, Coherence, Accuracy. Try elaborating again by staying focused on explaining the concept in greater detail without moving to examples, ensuring that you capture the essence of the core components and that everything you state is consistent with the source text.

**Student**

> Expanding on that, strategy is not a single decision but a coherent set of commitments that hang together: what products to build, where the company should place itself in the domain of its competitors, which capabilities to invest in, and how each function is run. Those choices are deliberate and mutually reinforcing, and the aim is lasting advantage rather than a good quarter, because success that cannot be sustained does not guarantee the success of the company going forward.

**Assessment Agent:** PASS

**Tutor**

> Excellent elaboration. You successfully expanded on the concept in your own words, capturing the fullness of how these coordinated choices work together for long-term success. That completes the Elaborate step.


## Exemplify

**Tutor**

> Let's move on to exemplification. Please provide a well-chosen, original example of a company's strategy that clarifies what you mean, along with a contrasting example of something that is not a strategy. Be sure to explain exactly why your examples do and do not represent the concept.

**Student**

> A good example is a big tech company that does tech really well and stays ahead of everyone. A contrasting example would be a company that does not do that.

**Assessment Agent:** FAIL on `Fit`, `Concreteness`, `Explicit Mapping`, `Contrast`

**Tutor**

> You are on the right track, but your response describes a generic outcome of success rather than a specific set of actions, lacks an explanation of how it connects to the concept, and provides a non-example that simply states the opposite. Here is what you failed: Fit, Concreteness, Explicit Mapping, Contrast. Please try again by providing a realistic instance that genuinely displays the concept, explaining exactly how it illustrates it, and including a true non-example that clarifies the concept's boundaries.

**Student**

> IKEA is an example: it designs flat-pack furniture, runs warehouse-style stores, and has customers do the assembly and transport. Those choices reinforce one another to sustain low costs rivals struggle to match, which is what makes it a coordinated set of actions aimed at outperforming competitors. A contrasting case is a retailer that cuts prices for one quarter to hit a sales target. That is not strategy, because it is a single isolated move with no supporting commitments behind it and nothing that would sustain an advantage.

**Assessment Agent:** PASS

**Tutor**

> Excellent work. Your example of IKEA perfectly illustrates a coordinated set of actions, and your contrasting example clearly shows the boundary between a true strategy and a short-term tactic. That completes the Exemplify step.


## Illustrate

**Tutor**

> Finally, let's illustrate the concept of a company's strategy. Provide a picture in words, such as an analogy, simile, or metaphor, that captures the meaning of the concept.

**Student**

> It is kind of like when a business plans out what it is going to do before actually doing it.

**Assessment Agent:** FAIL on `Analogy`, `Match`, `Imagery`

**Tutor**

> That is a fair start, but your response gives a literal description of business planning rather than a figurative comparison, misses the competitive aspect of the concept, and lacks a concrete picture. Here's what you failed: Analogy, Match, Imagery. Try illustrating the concept again by comparing it to something completely outside the world of business that paints a vivid mental picture of coordinating actions to outperform rivals.

**Student**

> Strategy is like the sailing line a skipper picks for a long race. They cannot control the wind, and every rival is on the same water, so the advantage comes from a set of choices that fit together: the angle held, the sails set for it, the crew positioned for that angle. Any one choice alone does nothing, and a boat that keeps switching lines mid-race arrives last however hard the crew works.

**Assessment Agent:** PASS

**Tutor**

> That is a fantastic illustration. Comparing strategy to a skipper's sailing line perfectly captures how a coordinated set of choices is necessary to navigate competition and achieve a long-term goal. That completes the Illustrate step, and with it, our session on this concept.

# Sample session

One real run of `scripts/session.py`, kept so the Tutor Agent's output can be read
without spending anything. Illustrative, not a fixture: nothing tests against it.

| | |
| --- | --- |
| Text | strategy |
| Tutor prompt | `v1` |
| Assessment prompt | `v3` |
| Rubric | `v3` |
| Model | gemini-3.1-pro-preview |
| Attempts per step | 3 |
| Outcome | complete |

Regenerate with `python scripts/session.py --reading strategy`. Answers below are
deliberate: some are written to fail a specific criterion.

**This run predates the no-pinpointing rule and breaks it twice.** The Tutor
quotes the student back at them, once with "the stuff a company decides to do"
and once with "position the company in its industry". The prompt now forbids
that: name the fault, never the phrase that caused it. Left in place because it
is the clearest illustration of why the rule exists.

---


## State

**Tutor**

> Let's start by defining a company's strategy. State what it is briefly, clearly, and as precisely as possible in your own words.

**Student**

> Strategy is basically the stuff a company decides to do, like whether they want to be cheap or fancy, or whether they sell in one country or everywhere, and it matters a lot because if you get it wrong your competitors will beat you and then you won't make money in the long run.

**Assessment Agent:** FAIL on `Brevity`, `Clarity`

**Tutor**

> You have the right general idea, but your statement includes unnecessary examples and uses vague language like "the stuff a company decides to do." Here's what you failed: Brevity, Clarity. Try stating the concept again, this time making sure your definition is concise, straight to the point, and uses precise language rather than vague terms.

**Student**

> A company's strategy is the coordinated set of choices its managers make about how to compete, aimed at outperforming rivals and earning superior profitability.

**Assessment Agent:** FAIL on `Own Words`

**Tutor**

> You have the right idea, but your statement relies too heavily on the exact phrasing from the text, just swapping out a few words like 'choices' and 'rivals'. Here is what you failed: Own Words. Try stating the definition again, this time expressing the concept entirely in your own unique way without copying the original sentence structure.

**Student**

> A company's stragety is a set of cohesives moves that managers choose to set out in order to decide how they will go toe to toe with their rival and earn more than them.

**Assessment Agent:** PASS

**Tutor**

> Excellent work. You provided a clear, concise definition of a company's strategy in your own words, capturing the core idea perfectly. That completes the State step.


## Elaborate

**Tutor**

> Now, let's elaborate. Expand on your statement at greater length so that the reader gets a fuller picture of what a company's strategy entails.

**Student**

> Expanding on that, strategy is not a single decision but a coherent set of commitments that hang together: what products to build, where to position the company in its industry, which capabilities to invest in, and how each function is run. Those choices are deliberate and mutually reinforcing, and the aim is lasting advantage rather than a good quarter, because success that cannot be sustained does not secure the company's future.

**Assessment Agent:** FAIL on `Own Words`

**Tutor**

> You have a good grasp of the details, but your response closely paraphrases the text and uses exact phrases like "position the company in its industry" and "secure the company's future." Here is what you failed: Own Words. Try expanding on your statement again, this time expressing the elaboration entirely in your own words to show your personal understanding.

**Student**

> Expanding on that, strategy is not a single decision but a coherent set of commitments that hang together: what products to build, where the company should place itself in the domain of its competitors, which capabilities to invest in, and how each function is run. Those choices are deliberate and mutually reinforcing, and the aim is lasting advantage rather than a good quarter, because success that cannot be sustained does not guarantee the success of the company going forward..

**Assessment Agent:** PASS

**Tutor**

> That is an excellent elaboration. You captured the fullness of the concept by explaining how these coordinated choices work together for long-term success, all in your own words. That completes the Elaborate step.


## Exemplify

**Tutor**

> Let's move on to exemplification. Provide a well-chosen, original example of a company's strategy that clarifies what you mean, along with a contrasting example of something that is not an instance of the concept. Be sure to explain exactly how or why each example illustrates your point.

**Student**

> IKEA is an example: it designs flat-pack furniture, runs warehouse-style stores, and has customers do the assembly and transport. Those choices reinforce one another to sustain low costs rivals struggle to match, which is what makes it a coordinated set of actions aimed at outperforming competitors. A contrasting case is a retailer that cuts prices for one quarter to hit a sales target. That is not strategy, because it is a single isolated move with no supporting commitments behind it and nothing that would sustain an advantage.

**Assessment Agent:** PASS

**Tutor**

> Excellent work. Your original example of IKEA perfectly illustrates a coordinated set of actions, and your contrasting example clearly shows the boundary between a true strategy and an isolated tactic. That completes the Exemplify step.


## Illustrate

**Tutor**

> Finally, let's illustrate the concept of a company's strategy. Provide a picture in words, such as an analogy, simile, or metaphor, that captures the essence of what a strategy is. Make sure your comparison draws from outside the world of business and management.

**Student**

> Strategy is like the sailing line a skipper picks for a long race. They cannot control the wind, and every rival is on the same water, so the advantage comes from a set of choices that fit together: the angle held, the sails set for it, the crew positioned for that angle. Any one choice alone does nothing, and a boat that keeps switching lines mid-race arrives last however hard the crew works.

**Assessment Agent:** PASS

**Tutor**

> That is a fantastic illustration. Your sailing analogy provides a vivid mental picture and perfectly captures how a coordinated set of choices is necessary to outperform competitors over the long term. That completes the Illustrate step, and you have now finished the entire SEE-I process for this concept.

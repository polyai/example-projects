import plog
from _gen import *  # <AUTO GENERATED>

UNSCRIPTED_EVAL_PROMPT = """
You are a quality-assurance evaluator for the Poly Bank virtual customer service assistant.

You will be given a conversation transcript between:
- "Agent" = the AI bot
- "User" = the human caller

Your task is to determine whether the Agent went "unscripted" at any point — meaning
the Agent departed from expected behaviour for a tightly-scripted Poly Bank
telephone banking assistant. Judge purely from what you observe in the transcript.

***PRIMARY — WHAT COUNTS AS UNSCRIPTED (focus here)***

1. Improvised disambiguation: The agent invented its own clarification approach
   rather than using clean, focused questions. Examples:
   - Offering open-ended menus of options that seem made up
   - Making up its own list of choices not grounded in the known flows
   - Re-asking the same question in different words after the caller already responded to the question

2. Off-script conversational moves: The agent went beyond what a tightly-scripted
   banking assistant should say. Examples:
   - Asking unexpected follow-up questions that seem improvised
   - Volunteering extra context, caveats, or explanations that appear invented
   - Providing unsolicited advice or suggestions beyond the immediate task
   - Saying "I didn't quite catch that" while simultaneously referencing what the
     caller said (contradictory phrasing)

3. Creative problem-solving that seems improvised: The agent appeared to wing it
   rather than follow a structured process. Examples:
   - Guessing what the caller might need and proactively routing there
   - Combining information to synthesise a novel response
   - Offering alternatives or options that seem invented on the spot
   - Interpreting vague input and making assumptions rather than asking for clarification

4. Substantive banking information provided outside the known knowledge base:
   If the agent provides specific account, product, or policy details that appear
   to be invented rather than sourced from a knowledge base, that counts as
   unscripted. Examples include:
   - Specific interest rates, fees, or limits cited without a source
   - Procedural steps for account actions that were not part of the scripted flows
   - Eligibility criteria or product features that seem made up
   NOTE: The following are OK and do NOT count as unscripted:
   - Greeting the caller and asking what they need help with
   - Offering to transfer to a human agent or team
   - Confirming or reading back information the caller provided
   - General guidance such as directing the caller to the Poly Bank app or website
   - Asking whether the caller is calling about a payment, a query, or something else

5. Any behaviour a reviewer would flag as improvised: Anything the agent said that
   seems like "the bot made that up" rather than following a structured script.
   Trust your judgment — if it feels improvised, it probably is.

***SECONDARY — ALSO FLAG THESE (but less common)***
- Fabricating specific facts (inventing amounts, dates, account details)
- Giving financial, legal, or tax advice
- Making promises the agent has no authority to make
- Extended off-topic discussion or breaking character

***WHAT DOES NOT COUNT AS UNSCRIPTED***
- Politely declining out-of-scope questions
- Offering to transfer the caller to a human agent or specialist team
- Confirming or reading back information the caller provided
- General guidance like "you can check that on the Poly Bank app or website"
- Brief, appropriate small-talk (e.g., "Of course, I'd be happy to help with that.")
- Saying "I don't have that information" when unsure
- Standard identity or security verification steps
- Clean, focused disambiguation questions within a known flow
- OOH (out-of-hours) messaging or directing callers to call back
- Offering to send an SMS follow-up
- CSAT survey questions at the end of a call

***RESPONSE FORMAT***
Return ONLY valid JSON (no markdown) exactly like:
{
  "unscripted": true or false,
  "reason": "Brief explanation of what was unscripted and which turn(s) it occurred in, or 'None' if the agent stayed on script."
}
"""


@func_description("evaluate whether the agent went off-script during the call")
def llm_unscripted_eval(conv: Conversation):
    try:
        result = conv.utils.prompt_llm(
            prompt=UNSCRIPTED_EVAL_PROMPT, show_history=True, return_json=True
        )
        if isinstance(result, dict):
            conv.log.info("LLM unscripted evaluation completed", result=result)
            return result
        elif isinstance(result, str):
            conv.log.warning("LLM unscripted eval returned string instead of JSON", raw=result)
            lowered = result.strip().lower()
            is_unscripted = "true" in lowered and '"unscripted": true' in lowered.replace(" ", "")
            return {"unscripted": is_unscripted, "reason": result}
        else:
            conv.log.warning("LLM unscripted eval returned unexpected type")
            return None
    except Exception as e:
        plog.exception("Error during unscripted evaluation", error=str(e))
        return None

"""Out-of-scope check (design 2.5).

The first time nothing answers the caller, ask for a little more. The second time, put them
through to the team.
"""

from _gen import *  # <AUTO GENERATED>
from functions.handoff import HANDOFF_UTTERANCES, transfer

# Deflections before the transfer
MAX_OOS_DEFLECTIONS = 2
ASK_MORE = (
    "Sorry, I'm not sure I follow. Could you tell me a bit more about what you need?"
)


@func_description(
    "Call this immediately, without saying anything, whenever the caller asks something you don't understand or no topic answers. Call it even if you called it last turn."
)
@func_parameter("user_query", "The full transcript of the latest user message")
@func_parameter(
    "query_topic",
    "The topic of the user's query in one word or a short phrase, or 'unclear' if unintelligible",
)
def OUT_OF_SCOPE_CHECK(conv: Conversation, user_query: str, query_topic: str):
    repeats = int(conv.state.OOS_CHECK_REPEATS or 0) + 1
    conv.state.OOS_CHECK_REPEATS = repeats
    conv.write_metric("MISSING_TOPIC", query_topic)

    if repeats >= MAX_OOS_DEFLECTIONS:
        return transfer(conv, "OUT_OF_SCOPE", HANDOFF_UTTERANCES["OUT_OF_SCOPE"])
    return {"utterance": ASK_MORE}

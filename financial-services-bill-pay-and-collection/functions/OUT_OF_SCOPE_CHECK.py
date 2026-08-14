"""Out-of-scope intent detection.

Detects when the user asks something the agent cannot handle and offers
to transfer them to a live agent.
"""

from _gen import *  # <AUTO GENERATED>

# Maximum deflections before automatically offering a transfer
MAX_OOS_DEFLECTIONS = 2


@func_description(
    "Call this function immediately, without saying anything, whenever the user asks a question you don't understand or have no relevant information for. Call even if you called it last turn."
)
@func_parameter("user_query", "The full transcript of the latest user message")
@func_parameter(
    "query_topic",
    "The topic of the user's query in one word or a short phrase, or 'unclear' if unintelligible",
)
def OUT_OF_SCOPE_CHECK(conv: Conversation, user_query: str, query_topic: str):
    if not conv.state.OOS_CHECK_REPEATS:
        conv.state.OOS_CHECK_REPEATS = 0

    conv.state.OOS_CHECK_REPEATS += 1
    conv.write_metric("MISSING_TOPIC", query_topic)

    if conv.state.OOS_CHECK_REPEATS >= MAX_OOS_DEFLECTIONS:
        return {
            "utterance": "I'm not able to help with that, but I can transfer you to one of our team members who can. Let me connect you now.",
            "content": "Call the handoff function with reason='OUT_OF_SCOPE'.",
        }

    return {
        "utterance": "I'm not sure I can help with that. Could you tell me a bit more about what you need?"
    }

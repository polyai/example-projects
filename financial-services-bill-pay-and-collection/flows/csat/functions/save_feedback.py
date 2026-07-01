from _gen import *  # <AUTO GENERATED>


@func_description("Save the user's feedback")
@func_parameter("csat_score", "Score from 1 to 5 given by the user.")
@func_parameter(
    "csat_feedback",
    "Feedback given by the user. Copy the user's feedback verbatim, don't summarise it.",
)
def save_feedback(conv: Conversation, flow: Flow, csat_score: int, csat_feedback: str):
    if csat_score < 1 or csat_score > 5:
        return "csat_score must be between 1 and 5"
    conv.write_metric("CSAT_SCORE", str(csat_score))
    conv.write_metric("CSAT_FEEDBACK", csat_feedback)
    conv.write_metric("CSAT_COMPLETED")
    return {
        "utterance": "Great! That's everything. Thanks so much for taking the time, your feedback is really important to us. Goodbye!",
        "hangup": True,
    }

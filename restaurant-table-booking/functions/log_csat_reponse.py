from _gen import *  # <AUTO GENERATED>


@func_description("Call this function to log the customer satisfaction with agent")
@func_parameter(
    "csat_response", "whether or not the user said their issue was resolved"
)
def log_csat_reponse(conv: Conversation, csat_response: bool):
    csat_response_value = "YES" if csat_response is True else "NO"
    conv.write_metric("CSAT_RESPONSE", csat_response_value, write_once=False)
    transcript = (
        conv.transcript_alternatives[0] if conv.transcript_alternatives else "N/A"
    )
    conv.write_metric("CSAT_RESPONSE_TRANSCRIPT", transcript, write_once=False)
    return {"utterance": "Enjoy the rest of your day! Goodbye!", "hangup": True}

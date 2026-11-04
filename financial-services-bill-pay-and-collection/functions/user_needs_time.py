from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Agent Behaviour] Call when user explicitly requested you to wait for them, or was silent after you told them you are happy to wait. Do not call it if the agent requested time, or if user has not requested time."
)
def user_needs_time(conv: Conversation):
    conv.write_metric("USER_REQUESTED_TIME")

    # Determine if user was silent this turn
    user_silent = False
    for event in conv.history[::-1]:
        if event.role == "user":
            user_silent = not bool(event.text)
            break

    # If user not silent, they requested time. Return wait behaviour prompt, and flag this
    if not user_silent:
        conv.state.user_requested_wait = True
        # A wait after a payment readback: the next reply answers the wait, not the question,
        # so make_payment asks the question again before it pays.
        payment = conv.state.payment
        if (
            isinstance(payment, dict)
            and payment.get("amount")
            and not payment.get("paid")
        ):
            conv.state.payment = {**payment, "waited": True}
        utterance = "Of course, take your time."
    else:
        # If user silent and hasn't requested time, prompt for silence behaviour
        # Ideally this should not happen
        if not conv.state.user_requested_wait:
            return "user_requested_time called without user indicating they wanted time. Follow prompts under SILENCE BEHAVIOR instead of calling this function."

        # If user silent but has requested time, return silence
        utterance = ""

    return {"utterance": utterance, "listen": {"asr": {"timeout": 20}}}

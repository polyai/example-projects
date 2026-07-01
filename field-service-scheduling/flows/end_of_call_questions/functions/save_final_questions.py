from _gen import *  # <AUTO GENERATED>


@func_description("Save the final questions")
@func_parameter("final_question_1", "question 1 to be asked at the end of a call")
@func_parameter("final_question_2", "question 2 to be asked at the end of a call")
def save_final_questions(
    conv: Conversation, flow: Flow, final_question_1: str, final_question_2: str
):
    import functions.step_utils as step_utils

    # TODO: edit the utterances to be used when value validation or verification fails

    # function used when we exceed the retry limit
    # TODO: replace fallback behaviour with project-specific function if needed
    def fallback_transfer(
        conv: Conversation, handoff_reason="FINAL_QUESTIONS_RETRY_LIMIT_EXCEEDED"
    ):
        return conv.call_handoff(
            destination="DEFAULT",
            reason=handoff_reason,
            utterance="Ok. I'll put you through to someone who can help with this. One moment.",
        )

    # initialise retry limit and counter
    step_utils.get_retry_counter(conv, flow)

    # check if any values are missing and still need to be requested

    final_questions = str(final_questions)
    if not final_questions or final_questions.lower() in ["na", "n/a"]:
        return "Ask the user for the final questions in a natural, conversational way."

    # increment the retry counter
    step_utils.increment_retry_counter(conv, flow)

    # TODO: Check if the value is in the expected format (e.g. right length)
    # Convert it to a different format if necessary
    # final_questions = ...

    conv.write_metric("FINAL_QUESTIONS_EXTRACTED")

    # SUCCESS

    # save values to state
    conv.state.final_questions = final_questions

    # TODO: Any other logic, such as making an API call with the collected value(s)

    # TODO: Decide where to transition next (or whether to exit the flow)
    # flow.goto_step("Type in the next step name here")

    # TODO: Consider returning a specific prompt or utterance when transitioning
    return "Success. Say 'thank you' and move on to the next step."
    # Alternatively:
    # return {
    #    "utterance": "Type in the next utterance here"
    # }

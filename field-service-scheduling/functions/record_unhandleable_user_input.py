from _gen import *  # <AUTO GENERATED>


@func_description(
    "Record user inputs that can't be handled, either because they're \"out of scope\" (you don't have the information to answer it in the context) or \"incomprehensible\" (as a result of an ASR mistranscription, the user question doesn't make sense in the context)"
)
@func_parameter("user_input", "Unhandleable user input that is out of scope")
@func_parameter("user_input_type", 'Choose either "out of scope" or "incomprehensible"')
def record_unhandleable_user_input(conv: Conversation, user_input: str, user_input_type: str):
    # Initialize the counter
    if not conv.state.unhandleable_counter:
        conv.state.unhandleable_counter = {"out of scope": 0, "incomprehensible": 0}
    # Argument validation, with "out of scope" as the default type
    type = user_input_type.lower()
    if type not in ["out of scope", "incomprehensible"]:
        type = "out of scope"
    # Increment the counter
    conv.state.unhandleable_counter[type] += 1

    # How many times to retry before transferring the call
    # Limits are set per conversation. You can set different limits for different types.
    # A limit of 2 means we'll ask two clarifications, and transfer only on the third attempt
    limits = {
        "out of scope": 1,
        "incomprehensible": 2,
        "either": 2,
    }

    # Define return values for different types of user inputs
    # You can return "utterance" or "content" (if you want the responses to be more flexible and context-dependent)
    # If you're returning "content" here, make sure you don't instruct the LLM to say anything that would be blocked by the unhandleable_user_input entry in Response Control
    return_values = {
        "out of scope": {
            1: {
                "utterance": "Just to make sure I've understood you correctly, would you mind rephrasing your question?"
            },
            # this one is not currently in use because out of scope limit is 1
            2: {
                "utterance": "Unfortunately, I don't know the answer to that specific question, but I might be able to help you with other queries. What would you like to know?"
            },
            "limit": {
                "content": "Immediatelly call the 'transfer_call' function with utternace='I can't help with that, but I'll put you through to someone who'll be able to assit you. One second.' and reason='UNHANDLEABLE_USER_INPUT_OUT_OF_SCOPE'. Set the most appropriate destination based on the conversation history."
            },
        },
        "incomprehensible": {
            1: {"utterance": "Sorry, could you repeat that for me?"},
            2: {
                "utterance": "I'm sorry, but I still didn't catch that. Would you mind saying that again?"
            },
            "limit": {
                "content": "Immediatelly call the 'transfer_call' function with utternace='Let me put you through to someone who can help with this. One second.' and reason='UNHANDLEABLE_USER_INPUT_INCOMPREHENSIBLE'. Set the most appropriate destination based on the conversation history."
            },
        },
    }

    # OPTIONAL: save the user input as a metric
    # When custom metrics are available on Agent Studio

    # Return the appropriate value
    # TBD: add some validation to make sure the return values exist
    if (
        conv.state.unhandleable_counter[type] > limits[type]
        or sum(conv.state.unhandleable_counter.values()) > limits["either"]
    ):
        return return_values[type]["limit"]
    else:
        return return_values[type][conv.state.unhandleable_counter[type]]

from _gen import *  # <AUTO GENERATED>


@func_description(
    "Logs transcript of unhandleable task and offers transfer to restaurant"
)
def log_unhandleable_task(conv: Conversation):
    transcript = (
        conv.transcript_alternatives[0] if conv.transcript_alternatives else "N/A"
    )
    conv.write_metric("UNHANDLEABLE_TASK_TRANSCRIPT", transcript)
    return {
        "utterance": "I'm not sure about that. Would you like me to transfer you to the restaurant to speak to someone who can assist you?",
        "content": """
    Ask the user if they would like to be transferred to the restaurant to speak to someone who will be able to help. If they say yes immediately, without saying anything, call try_transfer_call with
"handoff_reason" = "unhandleable_task" and
"handoff_utterance" = "Sure, let me hand you over to my colleague who will be able to help you, I'll transfer you now." and
"handoff_to" = "default"

If the user says no to be transferred say: "Okay! Is there anything else I can help you with?" """,
    }

from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


def dob_collection_failed(conv: Conversation, flow: Flow):
    """Hand off when the user refuses or cannot provide their date of birth."""
    conv.write_metric("IDNV_DOB_NOT_COLLECTED", True)
    return handoff(
        conv,
        reason="IDNV_COLLECTION_FAILED",
        utterance="No problem — let me transfer you to someone who can help.",
    )

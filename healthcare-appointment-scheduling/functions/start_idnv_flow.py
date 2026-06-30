import plog
from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Flow] Start the IDNV flow to identify the caller and save their patient account."
)
def start_idnv_flow(conv: Conversation):
    """Start IDNV: confirm or collect phone, look up patients, collect DOB, match. Result in conv.state.identified_patient."""
    log_prefix = "[start_idnv_flow.start_idnv_flow]: "
    conv.state.post_idnv_flow_name = None
    plog.info(f"{log_prefix} cleared post_idnv_flow_name (generic IDNV); goto_flow='IDNV'")
    conv.goto_flow("IDNV")
    return {
        "content": "Tell the user that you'll need to pull up their account in order to help them and ask if the phone number they are calling from is the one associated with their account."
    }

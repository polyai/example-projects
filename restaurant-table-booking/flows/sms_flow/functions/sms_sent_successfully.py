from _gen import *  # <AUTO GENERATED>


@func_description("Call immediately when you see SMS was sent successfully")
def sms_sent_successfully(conv: Conversation, flow: Flow):
    conv.state.already_sent_to_number = True
    conv.write_metric("SMS_SENT")
    if conv.state.origin_flow == "make_booking":
        return {
            "content": "Let the user know the SMS was sent. Then, proceed with making the booking by calling the appropriate functions or collecting required information.",
            "transition": {
                "goto_flow": conv.state.origin_flow,
                "goto_step": conv.state.origin_step,
            },
        }
        # conv.goto_flow("make_booking")
        # return """
        #   Let the user know the SMS was sent. Ensure that you do not include the user's surname in the message. Then:
        #   - If you previously asked the user about booking notes, it means that you are in the stage of finalizing the booking. If the user agreed to finalize the booking, call the finalize_booking function. When doing so, pass only the booking_notes argument (use "-" if there are no notes).
        #   - If you have just checked the availability and the user agrees to the available date and time, call the temporarily_lock_slot function. Pass in the parameters for date, time, and party_size.
        # """
    elif conv.state.origin_flow == "confirm_cancel_modify_booking":
        conv.goto_flow("confirm_cancel_modify_booking")
    conv.exit_flow()
    return "Let the user know the SMS was sent and ask 'Is there anything else I can assist you with today?'"

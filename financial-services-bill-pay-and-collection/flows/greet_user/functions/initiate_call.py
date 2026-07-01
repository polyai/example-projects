from _gen import *  # <AUTO GENERATED>


@func_description("Start the call with the user")
def initiate_call(conv: Conversation, flow: Flow):
    conv.functions.set_voice("main")

    if conv.state.is_ooh:
        flow.goto_step("Ask Urgent")
        out_of_hours_message = conv.real_time_config.get(
            "out_of_hours_message",
            "Thank you for calling Poly Bank. Sorry, we are currently closed. If you need urgent help to report fraud or a scam, or block a lost or stolen card, please hold. If you need extra support, please hold. For everything else, our opening hours are 9am to 6pm Monday to Friday, except on bank holidays where this will vary. Are you calling for an urgent issue or extra support?",
        )
        return {"utterance": out_of_hours_message}

    conv.exit_flow()
    return {
        "utterance": "Hiya, thanks for calling Poly Bank, you're speaking to a virtual assistant! How can I help?"
    }

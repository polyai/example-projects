from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Collect zip code")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=2,
    delay_responses=[("One second, I'm just looking that up", 3)],
)
def go_to_collect_zip_code(conv: Conversation, flow: Flow):
    if conv.state.customer_details_list:
        flow.goto_step("Collect zip code")
        return "Collect the caller's zip code to verify that the retrieved customer details are accurate"
    else:
        conv.exit_flow()

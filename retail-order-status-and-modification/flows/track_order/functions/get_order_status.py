from _gen import *  # <AUTO GENERATED>
from functions import idnv, orders, sms
from functions.handoff import handoff
from functions.start_send_sms import start_send_sms

TOOL = "get_order_status"
NO_ORDERS_LINE = (
    "I can't see any recent orders on your account. Is it possible you ordered with a "
    "different phone number, or as a guest?"
)
TEAM_BY_EMAIL = (
    "The team can look it up by email. Would you like me to put you through?"
)
NOT_CHECKED_LINE = (
    "It might be worth a quick look. If it's still missing, just give us a call back and we'll "
    "look into it. Is there anything else I can help with?"
)


def _state(conv, next_line: str) -> str:
    return orders.call_state(conv, ["Task: track an order"], next_line)


def _offer_or_close(conv, order: dict, late: bool) -> str:
    """The tracking offer (one question naming the calling number when caller ID is usable),
    or the anything-else question."""
    if orders.in_transit(order) and orders.tracking_url(order):
        extra = ", so you can keep an eye on it" if late else ""
        return sms.offer(conv, "tracking_link", order["order_number"], extra=extra)
    return orders.ANYTHING_ELSE


def _follow_up(conv, order: dict) -> str:
    lines = []
    details = orders.status_details(order, conv)
    if details:
        lines.append(
            "Details to give only if they ask (carrier, last scan, ship date, address): "
            f"{details.rstrip('.')}."
        )
    if orders.in_transit(order) and orders.tracking_url(order):
        lines.append(
            f"{orders.YES_LINE} to the text offer: call start_send_sms with "
            "sms_id='tracking_link' and caller_agreed='true'."
        )
    if not orders.tracking_url(order) and not orders.in_transit(order):
        lines.append(f'If they ask for a tracking link: "{sms.NO_TRACKING_LINE}"')
    received = orders.not_received_line(order, conv)
    if received:
        lines.append(f'If they say they haven\'t got it: "{received}"')
    if orders.is_well_overdue(order, conv):
        lines.append(
            "If they want to be put through, call handoff with handoff_reason=ORDER_LATE."
        )
    return " ".join(lines)


def _one(conv, order: dict, hint: str, caller_said: str = "") -> str | dict:
    reason = orders.needs_colleague(order)
    if reason:
        return handoff(conv, reason, orders.colleague_line(order), "CUSTOMER_SERVICE")
    conv.write_metric("ORDER_STATUS_FLOW_SUCCESSFUL", write_once=True)
    received = orders.not_received_line(order, conv)
    if caller_said == "not_received" and received:
        # They've said it never came: the one question about checking nearby, not the status.
        return (
            f'Say: "{received}" Not checked yet: "{NOT_CHECKED_LINE}" Checked and still missing: '
            "call handoff with handoff_reason=MISSING_PACKAGE and handoff_utterance=\"I'm sorry. "
            "I'll put you through to the team so they can look into it. One moment, please.\" "
            "Never say it's lost.\n\n"
            + _state(conv, "Wait for whether they've checked.")
        )
    late = orders.is_late(order, conv)
    if late:
        conv.write_metric(
            "ORDER_LATE",
            "well_overdue" if orders.is_well_overdue(order, conv) else "late",
        )
    say = orders.say_status(order, conv)
    lead = ""
    if orders.by_digits(hint):
        names = orders.items_phrase(order["items"])
        lead = f"Great, I've got that one here. That's the one with the {names}. "
        pronoun = "They" if orders.plural(order["items"]) else "It"
        say = say.replace(f"Your {names} ", f"{pronoun} ", 1)
        say = say.replace("They are ", "They're ", 1).replace("It is ", "It's ", 1)
    wants_link = (
        caller_said == "tracking_link"
        and orders.in_transit(order)
        and orders.tracking_url(order)
    )
    if wants_link and not orders.is_well_overdue(order, conv):
        # They asked for the text themselves: that's the yes, so the text is started here.
        nxt = start_send_sms(conv, "tracking_link", "true", "")
        if isinstance(nxt, dict):
            return {"utterance": f"{lead}{say} {nxt['utterance']}"}
        return f'Say: "{lead}{say}" Then, in the same reply: {nxt}'
    ending = (
        ""
        if orders.is_well_overdue(order, conv)
        else f" {_offer_or_close(conv, order, late)}"
    )
    if (
        caller_said == "tracking_number"
        and orders.in_transit(order)
        and orders.tracking_url(order)
    ):
        calling = bool(sms.calling_number(conv))
        question = (
            "Shall I send it to the number you're calling from?"
            if calling
            else "Shall I text it to you?"
        )
        sms.offer(conv, "tracking_link", order["order_number"], question=question)
        # The design's answer to "can you give me the tracking number?": the reason, then the
        # one question. The status is for if they ask.
        return (
            f"Say: \"{lead}It's a long one, so it's easiest if I text you the tracking link. "
            f'{question}" If they ask where it is, say: "{say}" {_follow_up(conv, order)}\n\n'
            + _state(conv, "Wait for their answer to the text offer.")
        )
    return (
        f'Say: "{lead}{say}{ending}" Add nothing the tool didn\'t give you'
        + (", and don't repeat the digits they said" if lead else "")
        + f". {_follow_up(conv, order)}\n\n"
        + _state(
            conv, "Answer any follow-up about this order, or help with the next thing."
        )
    )


def _summary(conv, orders_: list[dict]) -> str:
    conv.write_metric("ORDER_STATUS_FLOW_SUCCESSFUL", write_once=True)
    shown = orders_[: orders.MAX_ORDERS_LISTED]
    say = orders.summary_line(shown, conv)
    with_link = [o for o in shown if orders.in_transit(o) and orders.tracking_url(o)]
    if with_link:
        first = with_link[0]
        orders.select(conv, first)
        name = orders.items_phrase(first["items"], brand=False).split(" and ")[0]
        ending = sms.offer(conv, "tracking_link", first["order_number"], for_items=name)
    else:
        ending = orders.ANYTHING_ELSE
    lines = [
        f"- {orders.order_name(o, shown)}: {orders.status_details(o, conv)}"
        for o in shown
    ]
    colleague = [o for o in shown if orders.needs_colleague(o)]
    extra = (
        " If they ask about the order that needs the team, call handoff with "
        f"handoff_reason={orders.needs_colleague(colleague[0])}."
        if colleague
        else ""
    )
    return (
        f"Say: \"{say} {ending}\" That's the answer: don't ask which order. A yes to the text "
        "offer → call start_send_sms with sms_id='tracking_link' and caller_agreed='true'. If "
        f"they ask about one order, call {TOOL} with what they say about it.{extra} Details to give "
        "only if asked:\n"
        + "\n".join(lines)
        + "\n\n"
        + _state(conv, "Answer any follow-up, or help with the next thing.")
    )


@func_description(
    "Look up the status of the caller's order and say what to tell them. Call it whenever the caller asks about an order or says which order they mean, even if it's the same as before."
)
@func_parameter(
    "order_hint",
    "Whatever the caller said that picks out the order: an item ('the running shoes'), or digits of the order number as they said them ('ending seven five six one'). 'all' if they want every order. Empty string if they haven't said.",
)
@func_parameter(
    "caller_said",
    "'not_received' if the caller says the order shows as delivered, or should have come, but they don't have it; 'tracking_link' if they've asked for the tracking link to be texted; 'tracking_number' if they've asked for the tracking number. Otherwise an empty string.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me pull that up.", 3), ("Just a moment.", 3)],
)
def get_order_status(conv: Conversation, flow: Flow, order_hint: str, caller_said: str):
    if not idnv.is_verified(conv):
        return orders.require(conv, "track_order")

    order, matches, orders_ = orders.pick_order(conv, order_hint)
    if not orders_:
        conv.write_metric("NO_ORDERS_FOUND", "track")
        return (
            f'Say: "{NO_ORDERS_LINE}" If they say yes or aren\'t sure, say: "{TEAM_BY_EMAIL}" and '
            "on a yes call handoff with handoff_reason=ORDER_NOT_FOUND. If they want to try another "
            "number, call start_track_order with try_other_account='true'."
        )
    if order:
        return _one(conv, order, order_hint, str(caller_said or "").strip().lower())
    if orders.names_an_order(order_hint or "") and not matches:
        return orders.no_matching_order(orders_, conv, TOOL, order_hint)
    wants_all = bool(
        set((order_hint or "").lower().split()) & {"all", "both", "every", "each"}
    )
    if matches and orders.names_an_order(order_hint or "") and not wants_all:
        return orders.which_order_instruction(
            orders_, conv, TOOL, "Which one are you calling about?", matched=matches
        )
    if len(matches) == 2 or (wants_all and len(matches) <= orders.MAX_ORDERS_LISTED):
        return _summary(conv, matches)
    return orders.which_order_instruction(
        orders_, conv, TOOL, "Which one are you calling about?"
    )

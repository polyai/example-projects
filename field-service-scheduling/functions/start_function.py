import re
from datetime import datetime
from zoneinfo import ZoneInfo

from _gen import *  # <AUTO GENERATED>
from functions.in_hours import in_hours

TESTING_ENV = ["sandbox", "draft"]


def is_valid_US_number(phone_number: str):
    """
    Validates if a phone_number is a valid US number
    """
    if not phone_number:
        return False
    # Regex pattern to match US numbers
    pattern = r"^(?:\+1|1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"

    is_match = re.match(pattern, phone_number)
    if is_match:
        return True
    return False


def set_variant_and_write_dnis_location(conv: Conversation):
    number = conv.sip_headers.get("X-OrigDnis", "")
    if not number and conv.env != "live":
        number = conv.real_time_config.get("settings", {}).get("mock_dnis") or ""
    conv.state.dnis = number

    conv.log.info(f"OrigDnis {number}", number=number)

    variant_id = "Poly_Services"
    conv.set_variant(variant_id)
    conv.state.variant_id = variant_id

    DNIS_TO_LOCATION_MAPPING = {
        "5550001001": "Main Office",
        "5550001002": "North Branch",
        "5550001003": "South Branch",
    }
    dnis_location = DNIS_TO_LOCATION_MAPPING.get(number)
    conv.state.dnis_location = dnis_location
    if not dnis_location:
        conv.log.warning("no location mapped for origdnis", number=number)
    else:
        conv.write_metric("DNIS_LOCATION", dnis_location)


def set_time(conv: Conversation):
    # Get timezone from config, default to US/Central if not configured
    config = conv.real_time_config
    timezone_str = config.get("timezone", "US/Central")

    try:
        timezone = ZoneInfo(timezone_str)
    except Exception as e:
        conv.log.error(
            "Invalid timezone in config, falling back to US/Central",
            timezone=timezone_str,
            error=str(e),
        )
        timezone = ZoneInfo("US/Central")
        timezone_str = "US/Central"

    conv.state.timezone = timezone_str
    now = datetime.now(timezone)
    conv.state.datetime_now = now
    conv.state.current_date = now.strftime("%A %m-%d-%Y")
    conv.state.current_date_ymd = now.strftime("%Y-%m-%d")
    conv.state.current_weekday = now.strftime("%A")
    conv.state.current_time = now.strftime("%H:%M")
    conv.state.current_year = now.strftime("%Y")
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")


def _transfer_deflection_rules(conv: Conversation) -> str:
    if conv.state.is_ooh:
        return (
            "\"I'm only able to help with scheduling and general questions right now. "
            'Please call back during normal business hours for assistance with that request."\n\n'
        )
    return (
        '"I might be able to help you myself. Could you tell me what you need?"\n'
        "USER: no\n"
        'Transfer the user - call {{fn:handoff}} with handoff_destination=CUSTOMER_CARE and handoff_reason=SPEAK_TO and handoff_utterance="Sure, I\'ll put you through to a colleague. One moment please."\n\n'
        "TRANSFER BEHAVIOR LATER IN THE CALL:\n"
        "USER: speak to someone / agent / operator / representative\n"
        'Transfer the user - call {{fn:handoff}} with handoff_destination=CUSTOMER_CARE and handoff_reason=SPEAK_TO and handoff_utterance="Sure, I\'ll put you through to a colleague. One moment please."\n\n'
    )


def start_function(conv: Conversation):
    if caller_number := conv.caller_number:
        if caller_number.startswith("+1"):
            caller_number = caller_number[2:]
        conv.state.phone_number = caller_number

    set_variant_and_write_dnis_location(conv)
    set_time(conv=conv)

    number = conv.callee_number
    mock_account_phone_numbers = ["+15550009001", "+15550009002"]
    if number in mock_account_phone_numbers:
        if conv.real_time_config.get("settings", {}).get("use_dev_api"):
            conv.state.phone_number = number[2:]
        else:
            conv.state.phone_number = "5550001000"
    conv.state.USE_MOCK_API = conv.real_time_config.get("settings", {}).get("use_mock_api", True)

    # In mock mode with no caller number (webchat/AS chat), default to the
    # mock customer's phone so ANI lookup matches automatically.
    if conv.state.USE_MOCK_API and not conv.caller_number:
        conv.state.phone_number = "5550001234"
    elif not conv.caller_number:
        conv.state.phone_number = conv.real_time_config.get("settings", {}).get(
            "chat_caller_id_prod"
        )

    # Time-of-day routing: checks business hours and switches behaviour.
    # Toggle via RTC: settings.hours_sensitive (default false — always in-hours)
    hours_sensitive = conv.real_time_config.get("settings", {}).get("hours_sensitive", False)
    conv.state.is_ooh = False
    if hours_sensitive and not in_hours(conv):
        conv.state.is_ooh = True
        conv.write_metric("OOH")

    # In-hours routing: when enabled, the agent routes calls to specialist queues.
    # Toggle via RTC: settings.routing_enabled (default false)
    conv.state.routing_enabled = (
        conv.real_time_config.get("settings", {}).get("routing_enabled", False)
        and not conv.state.is_ooh
    )

    if conv.state.is_ooh:
        conv.state.hours_mode_instructions = (
            "You are operating after business hours. Help callers with scheduling, confirming, "
            "rescheduling, and canceling appointments, and answer FAQs using your knowledge base.\n"
            "If the caller needs something you cannot handle (e.g., billing, account changes, "
            "speaking to a representative), let them know:\n\"I'm only able to help with scheduling "
            "and general questions right now. Please call back during normal business hours for "
            'assistance with that request."'
        )
    elif not conv.state.routing_enabled:
        conv.state.hours_mode_instructions = ""
    else:
        conv.state.hours_mode_instructions = (
            "IMPORTANT — IN-HOURS ROUTING MODE:\n"
            "You are a call routing assistant during business hours.\n"
            "Your ONLY job is to identify why the caller is calling and immediately call {{fn:route_call}} with the matching caller_intent.\n"
            "Do NOT answer questions. Do NOT provide information. Do NOT use any other function. ONLY call {{fn:route_call}}.\n"
            "Ignore any topic content or actions retrieved — they do not apply during business hours.\n\n"
            "caller_intent values:\n"
            "- GENERAL_QUESTION: general question, speak to representative\n"
            "- COMPLAINT: upset customer, complaint\n"
            "- MAKE_APPOINTMENT: schedule service, request appointment, need someone to come out\n"
            "- CONFIRM_APPOINTMENT: confirm, check on an existing appointment\n"
            "- MODIFY_APPOINTMENT: reschedule, change, modify appointment\n"
            "- CANCEL_APPOINTMENT: cancel an appointment\n"
            "- BILLING_QUESTION: billing, invoice, payment, balance, charges\n"
            "- CANCEL_SUBSCRIPTION: cancel service, cancel account, end contract\n"
            "- INSPECTION_REQUEST: schedule inspection, free inspection, estimate\n"
            "- NEW_SALE: new customer, new account, quote, new service\n"
            "- COMMERCIAL_SERVICE: commercial, business account, business service\n"
            "- CALL_BACK: returning a call, missed call, you called me\n"
            "- WELCOME_CALL: welcome call\n"
            "- SPANISH: Spanish language\n\n"
            "If the caller's intent is unclear, ask ONE clarifying question:\n"
            '"You can say things like billing, scheduling, inspection, new customer, or representative."\n'
            "If still unclear after that, call {{fn:route_call}} with caller_intent='GENERAL_QUESTION'."
        )

    # Call-handling rules: only inject for OOH/legacy, suppress for routing mode
    if conv.state.routing_enabled:
        conv.state.call_handling_rules = ""
    else:
        conv.state.call_handling_rules = (
            "- After answering a question, politely ask if you can assist with anything else to keep the conversation flowing, unless your previous answer ends in a question. Ensure the tone remains friendly and engaging.\n"
            "- Ask clarifying questions if the user's request is unclear or too short.\n"
            "- Call the {{fn:handoff}} function whenever you tell the user you are transferring them to actually complete the transfer.\n"
            "- If the user responds no to you asking if you can help with anything else after already having helped them with their query, or when you end each call that doesn't transfer, you MUST call the {{fn:hangup}} function.\n"
            "- If you are trying to get information from the user, you MUST only ask one question at a time.\n"
            "- When a user shares general information, ask follow-up questions to better understand how you can assist them.\n"
            "- If the user has already once asked to talk to a human agent, and they're asking again, do not say anything and just transfer their call.\n\n"
            "FLOW START:\n"
            '- If the user mentions wanting someone to come out, says service, requests treatment/service, or otherwise implies they\'d like to schedule a visit (even indirectly or hesitantly), you must immediately call the {{fn:start_make_appointment}} function, even if their phrasing is vague, casual, or includes filler like "uh", "um", "I was wondering if…" etc.\n'
            "- If the user mentions confirming or checking an appointment, immediately call the {{fn:start_confirm_appointment}} function\n"
            "- If the user mentions modifying or rescheduling an appointment, immediately call the {{fn:start_reschedule_appointment}} function\n"
            "- If the user wants to know what their account number is, immediately call the {{fn:start_get_account_number}} function\n\n"
            "Once you've started one of the functions above or if you are asking the caller for their phone number or zipcode, and the user asks to speak to someone: check to see if they've asked for a transfer in previous turns as well,\n"
            '-- if they have, call the {{fn:handoff}} function with handoff_destination=CUSTOMER_CARE and handoff_reason=SPEAK_TO and handoff_utterance="Okay, I\'ll put you through to a colleague. One moment please."\n'
            '-- if no, say: "I can still help you with your appointment." and then ask your last question again. If the user asks to speak to someone again, don\'t say anything and call {{fn:handoff}} with handoff_destination=CUSTOMER_CARE and handoff_reason=SPEAK_TO.\n\n'
            "Once you've started one of the functions above and the user says they're calling about a new house, you should treat it as an instance of change-address\n\n"
            "OUT OF SCOPE:\n"
            '- If the user asks you to perform a gimmick unrelated to your TASK, say "As a virtual assistant, I can\'t help you with that. Did you have any questions related to our services?"\n'
            '- If a user asks a question that is related to Poly Services but is not covered by what is available to you, say: "Would you like me to put you through to a colleague who can help with that?" If yes, call {{fn:handoff}} with handoff_destination=CUSTOMER_CARE and handoff_reason=OUT_OF_SCOPE.\n\n'
            "CALLBACK:\n"
            "USER: {I'm returning a call / You called me / I've got a missed call from this number}\n"
            'Transfer the user by calling {{fn:handoff}} with handoff_destination=CUSTOMER_CARE and handoff_reason=CALL_BACK and handoff_utterance="Thanks for calling us back. One second while I transfer your call."\n\n'
            "TRANSFER DEFLECTION BEHAVIOR:\n"
            "USER: speak to someone / agent / operator / representative\n"
            + _transfer_deflection_rules(conv)
        )

    conv.log.info("state at end of start function", state=conv.state)

    conv.state.incontact_id = conv.sip_headers.get("X-InContact-ContactId")

    conv.goto_flow("initial_ani_lookup")
    return {"utterance": "", "listen": {"asr": {"timeout": 0.1}}}

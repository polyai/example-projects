from datetime import datetime
from zoneinfo import ZoneInfo

from _gen import *  # <AUTO GENERATED>
from functions.time_utils import is_ooh_clinic

START_FUNCTION_LOG_PREFIX = "[start_function]: "

# --- CUSTOMIZE: Set your Poly Clinic timezone ---
CLINIC_TIMEZONE = "America/New_York"


def start_function(conv: Conversation):
    conv.state.timezone = ZoneInfo(CLINIC_TIMEZONE)
    conv.state.datetime_now = datetime.now(tz=conv.state.timezone)
    conv.state.datetime_now_readable = conv.state.datetime_now.strftime("%A %d %B %Y")

    conv.write_metric("CALLEE_NUMBER", conv.callee_number)

    flags = conv.real_time_config.get("flags") or {}

    # OOH determination
    ooh_slider = conv.real_time_config.get("ooh_slider")
    if ooh_slider is None and isinstance(flags, dict):
        ooh_slider = flags.get("ooh_forced")
    if conv.env in ["draft", "sandbox", "pre-release"] and ooh_slider is not None:
        conv.state.is_ooh = bool(ooh_slider)
    else:
        conv.state.is_ooh = is_ooh_clinic(conv)

    if conv.state.is_ooh:
        conv.write_metric("OOH", write_once=True)

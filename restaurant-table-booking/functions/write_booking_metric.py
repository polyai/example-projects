from _gen import *  # <AUTO GENERATED>


@func_description("Write booking metric")
@func_parameter("name", "metric key")
@func_parameter("value", "metric value (optional, should default to None)")
@func_parameter("write_once", "whether to write metrics only once (should default to False)")
def write_booking_metric(conv: Conversation, name: str, value: str, write_once: bool):
    conv.write_metric(name, value, write_once=write_once)

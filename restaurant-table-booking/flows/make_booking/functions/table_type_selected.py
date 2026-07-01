from _gen import *  # <AUTO GENERATED>


@func_description("Select a specific table type")
@func_parameter(
    "table_type",
    'Table type the caller chose from "default", "outdoor", "highTop", "bar", "counter", or "-" if unknown',
)
def table_type_selected(conv: Conversation, flow: Flow, table_type: str):
    flow.goto_step("Collect Customer Name")

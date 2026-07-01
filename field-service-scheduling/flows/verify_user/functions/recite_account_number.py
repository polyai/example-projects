from _gen import *  # <AUTO GENERATED>


@func_description("recite the user account number")
def recite_account_number(conv: Conversation, flow: Flow):
    def digits_to_words(s: str) -> str:
        digit_map = {
            "0": "zero",
            "1": "one",
            "2": "two",
            "3": "three",
            "4": "four",
            "5": "five",
            "6": "six",
            "7": "seven",
            "8": "eight",
            "9": "nine",
        }
        return ", ".join(digit_map[d.strip()] for d in s.split(","))

    customer_details = conv.state.customer_details
    if customer_details is None:
        raise ValueError("customer_details must be set before calling this function")
    conv.say(
        f"It's {digits_to_words(', '.join(customer_details['customerID']))}. Is there anything else you'd like help with?"
    )
    conv.exit_flow()
    return

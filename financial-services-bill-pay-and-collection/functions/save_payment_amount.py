from _gen import *  # <AUTO GENERATED>

BUSINESS_DOMESTIC_PAYMENT = """
# If business - business account
Say: "And is this a bulk or batch payment?"

## If bulk or batch payment
Call {{fn:handoff}} with handoff_reason="PAYMENT_UK_BUSINESS_BULK"

## If single payment
Call {{fn:handoff}} with handoff_reason="PAYMENT_UK_BUSINESS"

## If user just says no
Call {{fn:handoff}} with handoff_reason="PAYMENT_UK_BUSINESS"

"""


INTERNATIONAL_BUSINESS_DIGITAL_ACCESS = """
Fantastic, so that'll be the quickest way to make this international business payment. Would that be ok?
"""

INTERNATIONAL_PAYMENT_WITHIN_LIMIT = """
# Payment amount is within app limits - continue with app flow,
"""

BUSINESS_DOMESTIC_PAYMENT_HIGH_VALUE = """
# If business - business account with a high payment amount
Say: "And is this a bulk or batch payment?"

## If yes - bulk or batch payment
Call {{fn:handoff}} with handoff_reason="PAYMENT_UK_BUSINESS_BULK"

## If no - single payment
Call {{fn:handoff}} with handoff_reason="DOMESTIC_PAYMENT_HIGH_VALUE_BUSINESS"
"""


@func_description("This is a function that was created automatically")
@func_parameter(
    "payment_type",
    'The type of payment. You *must* choose from ["INTERNATIONAL", "DOMESTIC_INTERNAL", "DOMESTIC_TO_ANOTHER_BANK"]',
)
@func_parameter(
    "payment_amount",
    "The amount the user wants to send (in dollars). If the user provides multiple amounts, select the higher one.",
)
@func_parameter(
    "account_type",
    'Optional. The account type: "PERSONAL" or "BUSINESS". Required for INTERNATIONAL payment type to determine correct threshold.',
)
def save_payment_amount(
    conv: Conversation, payment_type: str, payment_amount: float, account_type: str
):
    payment_type = payment_type.upper()
    PAYMENT_TYPES = [
        "INTERNATIONAL",
        "DOMESTIC_INTERNAL",
        "DOMESTIC_TO_ANOTHER_BANK",
        "DOMESTIC_INTERNAL",
    ]
    if payment_type not in PAYMENT_TYPES:
        return f"Wrong payment_type. Choose from {PAYMENT_TYPES}"

    if payment_type == "INTERNATIONAL":
        if account_type:
            account_type = account_type.upper()
            if account_type == "PERSONAL":
                if payment_amount > 10000:
                    return conv.functions.handoff(
                        reason="INTERNATIONAL_PAYMENT_PERSONAL_HIGH_VALUE",
                        requested_by_user=False,
                        handoff_required_by_faq=True,
                        account_type="PERSONAL",
                    )
                return INTERNATIONAL_PAYMENT_WITHIN_LIMIT
            elif account_type == "BUSINESS":
                if payment_amount > 21000:
                    return conv.functions.handoff(
                        reason="INTERNATIONAL_PAYMENT_BUSINESS_HIGH_VALUE",
                        requested_by_user=False,
                        handoff_required_by_faq=True,
                        account_type="BUSINESS",
                    )
                return INTERNATIONAL_PAYMENT_WITHIN_LIMIT
            else:
                return "Invalid account_type. Choose from ['PERSONAL', 'BUSINESS']"
        # Fallback for backwards compatibility: if account_type not provided, use old logic
        if payment_amount <= 10000:
            return INTERNATIONAL_PAYMENT_WITHIN_LIMIT
        return conv.functions.handoff(
            reason="INTERNATIONAL_PAYMENTS",
            requested_by_user=False,
            handoff_required_by_faq=True,
            account_type="PERSONAL",
        )

    if payment_type in ("DOMESTIC_INTERNAL", "DOMESTIC_TO_ANOTHER_BANK", "DOMESTIC_INTERNAL"):
        if account_type and account_type.upper() == "BUSINESS":
            if payment_amount <= 21000:
                return BUSINESS_DOMESTIC_PAYMENT
            return BUSINESS_DOMESTIC_PAYMENT_HIGH_VALUE

        # Personal domestic — process the payment
        if payment_amount > 10000:
            return conv.functions.handoff(
                reason="DOMESTIC_PAYMENT_HIGH_VALUE_PERSONAL",
                requested_by_user=False,
                handoff_required_by_faq=True,
                account_type="PERSONAL",
            )

        conv.state.pending_payment_amount = payment_amount
        conv.state.pending_payment_type = payment_type

        account_number = getattr(conv.state, "verified_account", None)
        if not account_number:
            return {
                "content": (
                    "Before processing the payment, you need to verify the customer's identity. "
                    "Ask for their account number first, then call {{fn:check_balance}} to look them up. "
                    "Once their DOB is verified, offer them the payment options."
                ),
            }

        return {
            "content": (
                f"The customer is verified (account {account_number}). "
                f"Now offer them options for making the ${payment_amount:.2f} payment: "
                f"'You can make this payment through the app, online banking, or I can process it "
                f"right here over the phone. Which would you prefer?' "
                f"If they choose APP: say 'Log into the app, go to Payments, and follow the steps.' "
                f"If they choose ONLINE BANKING: say 'Log into online banking and go to the Payments section.' "
                f"If they choose PHONE: call {{fn:process_payment}} with account_number='{account_number}' and amount={payment_amount}"
            ),
        }

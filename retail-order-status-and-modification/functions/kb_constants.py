from _gen import *  # <AUTO GENERATED>

KB_TOPIC_TO_CONTACT_REASON_MAPPING = {
    "Corporate-delete_account": "corporate__data_deletion",
    "Delivery_Issues-damaged_parcel": "delivery_issues__damaged_package_or_product",
    "Delivery_Issues-missing_item": "delivery_issues__missing_item",
    "Delivery_Issues-wrong_item_received": "delivery_issues__wrong_item",
    "Discount_Codes-not_working": "discounts_and_promos__discount_not_working/expired",
    "Gift_Cards-check_balance": "payment__gift_card_issues__balance_inquiry",
    "Gift_Cards-email_not_received": "payment__gift_card_issues__not_received",
    "Gift_Cards-issues_with_pin": "payment__gift_card_issues__gc_fraud/pin_issues",
    "Instore-opening_hours": "store_related__store_hours",
    "Instore-order_pickup": "store_related__pickup_inquiry",
    "Instore-order_pickup_how_long_hold": "store_related__pickup_inquiry",
    "Instore-order_pickup_when_ready": "store_related__pickup_inquiry",
    "Instore-product_issues": "store_related__issue_with_product_purchased_in_store",
    "Orders-canceled_by_FL-payment_issue": "orders__question_about_cancellation-payment",
    "Orders-canceled_by_FL-product_not_available": "orders__question_about_cancellation-product",
    "Orders-change_or_cancel": "orders__request_cancellation",
    "Orders-email_not_received": "orders__missing_email_confirmation",
    "Orders-tracking_number_not_working": "orders__tracking_information",
    "Product-information": "product__product_informations",
    "Product-launches": "product__product_launchess",
    "Product-out_of_stock": "product__product_availabilitys",
    "Refunds-refund_after_cancellation": "payment__question_about_cancellation_-_payment",
    "Refunds-track_refund": "delivery_issues__status_of_claim_or_refund",
    "Returns-return_policy": "returns_and_refunds__return_policy",
    "Returns-shipping_time": "returns_and_refunds__return_status",
    "Returns-start_a_return": "returns_and_refunds__return_instructions",
    "Returns-track_exchange": "returns_and_refunds__exchange_status",
    "Shipping-free_shipping": "discounts_and_promos__item_exclusion",
    "Shipping-shipping_costs": "shipping_options__shipping_cost",
    "Shipping-shipping_time": "shipping_options__shipping_timeframe",
    "Technical_Issues-create_account": "technical_issues__questions_about_my_account",
    "Technical_Issues-log_in": "technical_issues__log_in_issue",
    "Technical_Issues-update_info": "technical_issues__questions_about_my_account",
    "Technical_Issues-website_issues": "technical_issues__website_issue",
    "Orders-track_order": "orders__tracking_information",
}


@func_description("Topic-to-contact-reason mapping constants — not callable directly")
def kb_constants(conv: Conversation):
    return "Constants module."

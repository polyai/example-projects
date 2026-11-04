# Retail WISMO template

Phone agent for one retail store: where is my order, cancel or re-address an order that hasn't shipped, text tracking and store links, answer store questions, and put callers through to the team. Built to the signed-off Retail WISMO conversation design.

- **Shape:** flat. One flow per task (`track_order`, `cancel_order`, `change_address`, `verify_caller`, `sms_flow`), one advanced step each. Task flows start with an entry function step (ID&V gate, picking the order). Rules live in code: `functions/orders.py`, `functions/address.py`, `functions/sms.py`, `functions/idnv.py` (shared, unchanged).
- **Greeting:** "Thanks for calling {site}! Are you looking to check on an order?" A yes starts tracking.
- **ID&V (lax):** caller ID matching one account, or the phone number on the account plus the holder's name. The number is never read back; a miss re-asks and is counted (2 names, 2 numbers with no account, 3 partial numbers). Nothing about an order is said before verification.
- **Orders:** named by item, newest first, three at most; never order numbers, tracking numbers or links. Digits the caller gives are confirmed by content. Tracking two orders: one sentence each. Late orders say so; more than 3 business days late offers the team.
- **Writes:** cancel, address change and texts read back first, then write on a yes or an acknowledgement in a later turn. A same-turn yes is refused in code and the question is spoken again.
- **Addresses:** need a ZIP code; readback built in code (digits, state in full); a correction reads back only what changed.
- **Texts:** with caller ID, one question naming "the number you're calling from"; without, a mobile number, read back.
- **Hours:** from the variant. Blank, or a day not listed, is unknown, never closed. Out of hours (`settings.hours_sensitive`), the caller hears when the team is back and the call goes on.
- **Safety:** emergencies get "Please hang up and call 911.", kept by `hangup` if the call ends that turn.
- **Fixtures:** John Smith 201-555-0123 (shoes and socks shipped, backpack not shipped), Jane Doe 212-555-0178 (sneakers delivered), Maria Garcia 310-555-0142 (split, pickup and held orders), Sam Taylor 415-555-0136 (late shoes), Chris Lee 646-555-0187 (no orders), 201-555-0199 (no account).

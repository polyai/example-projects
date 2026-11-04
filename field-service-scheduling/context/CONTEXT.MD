# Field Service template

Books, checks, moves and cancels technician visits for one home-services company, handles unsafe and urgent problems, answers service questions, gives the account number and texts portal links.

- **Shape (flat):** one flow per task, each with one advanced step and a short numbered prompt. Task flows start with an entry function step that checks ID&V and picks the visit. Rules live in tool code (`functions/visits.py`, `functions/api_client.py`, `functions/idnv.py`); tools say what to read back and what to ask next, and end with a CALL STATE block.
- **Safety:** `report_hazard` holds the signed-off lines. Gas, CO and fire end the call after the line; electrical hazards go to `EMERGENCY`; a medical emergency is told to hang up and call 911. Urgent repairs are offered the emergency team or a regular visit from tomorrow. `EMERGENCY` skips the out-of-hours line and goes to customer care until `settings.emergency_line_configured` is on.
- **Booking:** the problem in the caller's words, inside or outside only when not obvious, then when ("earliest" for repairs, the caller's day for routine work). `find_visit_time` returns every open window from three working days before to three after the day asked for (never before tomorrow), or the first three working days with openings. The model offers the asked-for window alone when free, otherwise two at most. `make_new_appointment` takes the chosen window, checks it was looked up and is still open, and builds the readback.
- **Consent:** a write called with `caller_confirmed='false'` returns its readback; an acknowledgement to that question is a yes; a same-turn yes is refused and the question spoken again (`visits.same_turn_as_question`, history length only). Done lines are tool utterances.
- **ID&V (lax):** caller ID matching one account, or the phone number on the account plus the account holder's name. The number is never read back. Two numbers with no account ask whether they're new to us; new customers go to Inside Sales.
- **Hours:** from the variant. The FAQ answers today or the day asked about; blank hours are never closed.
- **Fixtures:** John Smith 201-555-0123 (visit tomorrow 9 to noon, the leak under the sink), Jane Doe 212-555-0178 (no visits), Maria Garcia 512-555-0144 (visits tomorrow morning and Friday afternoon), Alex Chen 312-555-0166 (visit about six hours from now), 201-555-0199 (no account). Mock diary: Thursday mornings and Fridays full.

## Test scenarios

```json
{
  "scenarios": [
    {
      "id": "account-number",
      "title": "Account number",
      "prompt": "What's my account number?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123"
      },
      "goal": "The agent reads the account number digit by digit in groups of four: four eight one two, zero nine three one, always saying 'zero', never 'oh'. The agent offers to say it again and repeats it the same way."
    },
    {
      "id": "book-acknowledgement-is-yes",
      "title": "Book acknowledgement is yes",
      "prompt": "Do you guys fix water heaters?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "After the first 'Okay.' (an answer to information) the agent does not start or book anything; it offers to book a technician. After the 'Okay.' to the readback question, the agent books the visit straight away without asking again."
    },
    {
      "id": "book-constraint-from-returned-windows",
      "title": "Book constraint from returned windows",
      "prompt": "Can someone come Thursday morning? The dishwasher won't drain.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent says its latest arrival window ends at 4 and offers a Saturday window instead. The agent never offers a window after 5. The agent books the Saturday window after the caller agrees to the readback."
    },
    {
      "id": "book-correction-at-readback",
      "title": "Book correction at readback",
      "prompt": "There's a leak in my kitchen. Can someone come Saturday morning?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "After the correction the agent reads back only what changed (the upstairs bathroom and the afternoon window), not the whole visit again. The agent books the afternoon window after the caller says yep."
    },
    {
      "id": "book-day-fully-booked",
      "title": "Book day fully booked",
      "prompt": "My kitchen tap's dripping. Could you do Friday? Any time.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent says it's fully booked on Friday and offers no more than two of the closest windows. The agent does not book anything. When the caller says they'll call back, the agent accepts it politely and asks if there's anything else."
    },
    {
      "id": "book-happy-path-caller-id",
      "title": "Book happy path caller id",
      "prompt": "Hi, I need someone to come and look at my sink. It's leaking underneath.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent does not ask for a phone number or name, because the caller ID matches the account. The agent does not ask whether the sink is inside or outside. The agent offers the earliest window, then reads back the leak under the sink, the day, the arrival window and 'at the address on your account', and asks whether to book it. Once booked, the agent says the day and arrival window, says someone 18 or over needs to be home, and asks if there's anything else. The agent never says \"yes or no\", and never reads out the caller's phone number or address."
    },
    {
      "id": "book-not-at-account-address",
      "title": "Book not at account address",
      "prompt": "My toilet keeps running. The earliest you have, please.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent says it can only book visits to the address on the account and offers to put the caller through to the team. The agent does not book the visit."
    },
    {
      "id": "book-one-breath-no-caller-id",
      "title": "Book one breath no caller id",
      "prompt": "Hi, it's Jane Doe, my number's two one two, five five five, zero one seven eight. The water heater in my garage isn't heating. Can someone come Thursday afternoon?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "3125550100"
      },
      "goal": "The agent does not ask again for the phone number, the name, the problem, where it is or the day. The agent never reads the phone number back. The agent thanks Jane by first name, says Thursday afternoon is free, reads the visit back and asks whether to book it. Once booked, the agent says someone 18 or over needs to be home."
    },
    {
      "id": "book-question-at-readback",
      "title": "Book question at readback",
      "prompt": "My dishwasher is leaking. Saturday morning, please.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent answers with the $89 diagnostic fee, waived if they go ahead with the repair, in one or two sentences, and asks again whether to book. The agent books after 'Okay, sure.'"
    },
    {
      "id": "book-real-ambiguity",
      "title": "Book real ambiguity",
      "prompt": "My shower's dripping. Could someone come Saturday morning?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "When the caller says they need to check, the agent waits ('take your time') and does not book. The agent books the visit only after the caller has said it's fine or yes."
    },
    {
      "id": "book-routine-day",
      "title": "Book routine day",
      "prompt": "I'd like to book my AC tune-up.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent asks what day would suit the caller, and does not offer the earliest first. The agent says plainly that next Wednesday afternoon is free, with no other windows offered, then reads the visit back and asks whether to book it. The agent books it and says so in a full sentence."
    },
    {
      "id": "book-same-day",
      "title": "Book same day",
      "prompt": "Can someone come today? The garbage disposal's jammed.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent says it can't book regular visits for the same day and offers the earliest window tomorrow. The agent does not offer the emergency team for a jammed disposal. The agent books tomorrow's window after the readback and the caller's yes."
    },
    {
      "id": "book-window-not-free",
      "title": "Book window not free",
      "prompt": "Can someone come Thursday morning? The dishwasher won't drain.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent says Thursday morning is fully booked and offers no more than two other windows. The agent reads back the dishwasher, the day, the arrival window and 'at the address on your account' before booking. The agent books only after the caller says yes."
    },
    {
      "id": "cancel-happy-path",
      "title": "Cancel happy path",
      "prompt": "I need to cancel the visit on Friday. We fixed it ourselves.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "5125550144"
      },
      "goal": "The agent reads back the Friday visit and asks whether to cancel it, and doesn't ask for a reason. The agent cancels after the caller's yes and says what it cancelled, then asks if there's anything else. The agent doesn't push the caller to keep the visit."
    },
    {
      "id": "cancel-rather-move",
      "title": "Cancel rather move",
      "prompt": "I need to cancel my visit on Friday.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "5125550144"
      },
      "goal": "The agent does not cancel the visit. The agent moves the visit to next Tuesday after the caller's yes."
    },
    {
      "id": "cancel-two-visits",
      "title": "Cancel two visits",
      "prompt": "I need to cancel an appointment.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "5125550144"
      },
      "goal": "The agent names both visits (tomorrow morning and Friday afternoon) and asks which one it's about. The agent reads back only the Friday visit, and cancels it after 'Okay.'"
    },
    {
      "id": "check-caller-id-and-be-home",
      "title": "Check caller id and be home",
      "prompt": "Hi, I'd like to check when my technician's coming.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123"
      },
      "goal": "The agent asks no ID questions and says the visit is tomorrow, between 9 and noon, then asks if there's anything they'd like to change. Asked about being home, the agent says someone 18 or over needs to be home to let them in, in one sentence. Asked whether they'll call first, the agent says we text when the technician's on the way, without listing other visit notes."
    },
    {
      "id": "faq-fee-and-job-we-dont-do",
      "title": "Faq fee and job we dont do",
      "prompt": "Do you charge to come out?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "none"
      },
      "goal": "The agent says there's an $89 diagnostic fee, waived if they go ahead with the repair, in a sentence. The agent says they don't do roofing, in a sentence, then what they do."
    },
    {
      "id": "faq-hours-today",
      "title": "Faq hours today",
      "prompt": "What time do you close today?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "none"
      },
      "goal": "The agent answers only today's closing time in one short sentence, without listing the whole week."
    },
    {
      "id": "idnv-name-mismatch",
      "title": "Idnv name mismatch",
      "prompt": "I need to cancel my appointment.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "3125550100"
      },
      "goal": "After the first wrong name the agent says the name doesn't match the account on that number and asks if it could be under someone else's name, like a partner's. The agent never says or hints at the name on file. After the second wrong name the agent says it wasn't able to find the account and puts the caller through."
    },
    {
      "id": "idnv-new-customer",
      "title": "Idnv new customer",
      "prompt": "I'd like to book a plumber.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "3125550100"
      },
      "goal": "The agent never reads the phone number back. After the second miss the agent says it still can't find an account and asks whether the caller is new to them. The agent welcomes them and puts them through to the team who'll get them set up."
    },
    {
      "id": "idnv-no-match-then-again",
      "title": "Idnv no match then again",
      "prompt": "Hi, I'd like to check when my technician's coming.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "3125550100"
      },
      "goal": "After the first number the agent says it can't find an account under that number and asks the caller to say it again or give a different one, without reading the digits back. After the right number and name the agent reads back the visit tomorrow, between 9 and noon, for the leak under the sink, and asks if there's anything they'd like to change."
    },
    {
      "id": "idnv-number-and-name",
      "title": "Idnv number and name",
      "prompt": "I need to move my appointment.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "3125550100"
      },
      "goal": "The agent asks for the phone number on the account, then the full name, and never reads the number back. The agent thanks Jane by first name and carries on with the request in the same turn. The agent says there are no upcoming visits and offers to book one."
    },
    {
      "id": "move-happy-path",
      "title": "Move happy path",
      "prompt": "I need to move my appointment tomorrow.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123"
      },
      "goal": "The agent mentions the visit tomorrow, between 9 and noon, and asks what day would work better. The agent says Saturday morning is free and asks whether to move the visit there, naming only the new day and window. After 'Sure.' the agent moves it and says where it moved to in a full sentence."
    },
    {
      "id": "move-sooner",
      "title": "Move sooner",
      "prompt": "I need to move my visit on Friday. Is there anything sooner? It's getting worse.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "5125550144"
      },
      "goal": "The agent offers the earliest window from tomorrow and asks whether to move the visit there. The agent moves it after the caller's yes."
    },
    {
      "id": "safety-gas-already-dealt-with",
      "title": "Safety gas already dealt with",
      "prompt": "The gas company came out last night and capped a leak. I need someone to fix the line to the stove.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "none"
      },
      "goal": "The agent does not give the gas safety line, because the leak has already been dealt with. The agent says it's glad they're safe, says it sounds urgent and offers the emergency team today or a regular visit from tomorrow. The agent puts the caller through to the emergency team."
    },
    {
      "id": "safety-gas-smell",
      "title": "Safety gas smell",
      "prompt": "Hi, I can smell gas in my kitchen, can you send someone?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "none"
      },
      "goal": "The agent's reply is exactly the gas safety line: leave the house right away, call 911 or the gas company's emergency line once outside, and don't switch anything on or off on the way out. The agent asks no questions first, and the call ends after the line."
    },
    {
      "id": "safety-medical",
      "title": "Safety medical",
      "prompt": "My husband just collapsed in the basement and he's not breathing properly.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "none"
      },
      "goal": "The agent tells the caller to hang up and call 911, and asks nothing else."
    },
    {
      "id": "safety-sparks-mid-idnv",
      "title": "Safety sparks mid idnv",
      "prompt": "I need to book an electrician.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "3125550100"
      },
      "goal": "The agent stops finding the account and says: keep everyone away from it, and if you see smoke or flames, leave the house and call 911, then that it's putting them through to the emergency team. The agent asks nothing else first, and the call is transferred."
    },
    {
      "id": "sms-another-number",
      "title": "Sms another number",
      "prompt": "Can I pay my bill online?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123"
      },
      "goal": "The agent reads the new number back digit by digit (nine one seven, five five five, zero one four two) and asks whether to send it there. The agent never reads out the number the caller is calling from. The agent says it has sent the link and asks if there's anything else."
    },
    {
      "id": "speak-to-person",
      "title": "Speak to person",
      "prompt": "Can I talk to a real person?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "none"
      },
      "goal": "The agent asks once what the caller is calling about before transferring. The agent then says it's putting them through, and the call is transferred."
    },
    {
      "id": "technician-late",
      "title": "Technician late",
      "prompt": "The tech was meant to be here by noon and nobody's shown up.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "none"
      },
      "goal": "The agent says sorry and puts the caller through to the team to check where the technician is, without asking what they're calling about."
    },
    {
      "id": "urgent-ac-regular-visit",
      "title": "Urgent ac regular visit",
      "prompt": "Our AC died. It's not too hot yet, though.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178"
      },
      "goal": "The agent offers the emergency team or a regular visit from tomorrow, and never decides for the caller that it isn't urgent. Asked about the cost, the agent gives the $150 after-hours call-out fee in one sentence and asks the question again. The agent books a regular visit after the caller's yes."
    },
    {
      "id": "urgent-leak-emergency-team",
      "title": "Urgent leak emergency team",
      "prompt": "Water's pouring through my ceiling from upstairs.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "none"
      },
      "goal": "The agent says it sounds urgent and offers the emergency team today or a regular visit from tomorrow, before asking for any account details. The agent says it's putting the caller through to the emergency team now, and the call is transferred."
    }
  ]
}
```

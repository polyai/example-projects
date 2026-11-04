# Healthcare template

Books, checks, moves and cancels clinic appointments for verified patients, answers clinic questions, texts the address, gets callers with urgent symptoms to the right help, and puts callers through to the clinic's teams.

- **Shape (flat):** one flow per task, each with one advanced step and a short numbered prompt. Task flows start with an entry function step that checks ID&V and picks the appointment. Rules live in tool code (`functions/appointments.py`, `functions/idnv.py`).
- **Availability:** the booking and move tools return every free time in the EHR's window (a day, or the first two days with any for the earliest), the nearest day before and after a full day, and refuse today, past days, closed days (hours known) and more than three weeks ahead. The model offers two at most, chosen from what the caller said.
- **Consent:** a write called without consent returns the fields to read back and the question; an offer that names the doctor, day and time and asks "Shall I book your sick visit for then?" counts as the readback. A yes or an acknowledgement in a later turn writes exactly that slot; a same-turn yes is refused in code (history length as a marker only). Done lines are spoken by the tools.
- **ID&V (strict):** phone number on the record + date of birth + member ID. No number is ever read back; a miss re-asks all three and never says which failed. `functions/idnv.py` is shared; don't edit it here.
- **Safety:** emergency, mental health and danger lines are spoken verbatim by `handoff`. Advice and medication questions go to the nurse (`SAME_DAY_TRIAGE`). Clinical and emergency transfers go through out of hours.
- **Hours:** from the variant. Blank hours are never "closed" and never spoken.
- **Fixtures:** Jane Smith 201-555-0123, born 1985-03-15, HC48213 (a follow-up with Dr. Smith); John Doe 212-555-0178, born 1990-07-22, HC77306 (a follow-up and a sick visit); 201-555-0199 (no record). Other patients hold Dr. Smith's Wednesday 9am and every Friday.

## Test scenarios

```json
{
  "scenarios": [
    {
      "id": "book-earliest",
      "title": "Book the earliest",
      "prompt": "Hi, I need to make an appointment.",
      "context": {
        "Phone": "2015550123",
        "DOB": "March 15, 1985",
        "Member ID": "HC48213",
        "Reason": "a bad cough for a week"
      },
      "goal": "After verification the agent says \"Thanks, Jane\" and asks what the appointment is for, then whether they'd like the earliest or a particular day and time. It offers the earliest with Dr. Smith as one offer that asks to book the sick visit for then, and on a yes says \"You're all booked in to see Dr. Smith tomorrow at 9am. Is there anything else I can help with?\""
    },
    {
      "id": "book-time-taken",
      "title": "Requested time taken",
      "prompt": "Hi, I need to book a follow-up appointment.",
      "context": {
        "Phone": "2015550123",
        "DOB": "March 15, 1985",
        "Member ID": "HC48213",
        "When": "Wednesday at 9"
      },
      "goal": "The agent says Dr. Smith is fully booked at 9 on Wednesday and offers two other times that day. When the caller picks one it reads back the follow-up, doctor, day and time and asks \"Shall I book that?\", then books on a yes."
    },
    {
      "id": "book-day-full",
      "title": "Nothing free that day",
      "prompt": "Hi, I'd like to book a wellness check.",
      "context": {
        "Phone": "2015550123",
        "DOB": "March 15, 1985",
        "Member ID": "HC48213",
        "When": "Friday, any time"
      },
      "goal": "The agent says Dr. Smith is fully booked on Friday and offers the nearest day before and after. Nothing is booked if the caller declines."
    },
    {
      "id": "okay-to-information",
      "title": "Okay to information, then okay to the question",
      "prompt": "Hi, I need a sick visit. What's Dr. Smith got on Monday?",
      "context": {
        "Phone": "2015550123",
        "DOB": "March 15, 1985",
        "Member ID": "HC48213"
      },
      "goal": "An \"Okay\" to the list of free times books nothing; the agent then asks whether to book a time. An \"Okay\" to that question books it."
    },
    {
      "id": "cancel-two-appointments",
      "title": "Cancel with two appointments",
      "prompt": "I need to cancel an appointment.",
      "context": {
        "Phone": "2125550178",
        "DOB": "July 22, 1990",
        "Member ID": "HC77306"
      },
      "goal": "The agent names both appointments by type and day and asks which one. It reads the chosen one back and asks \"Shall I cancel that for you?\", then cancels on a yes without asking for a reason."
    },
    {
      "id": "wrong-dob-twice",
      "title": "Details don't match twice",
      "prompt": "I need to cancel my appointment.",
      "context": {
        "Phone": "2015550123",
        "DOB given": "January 1, 1990",
        "Member ID": "HC48213"
      },
      "goal": "The agent says the details don't match without saying which, asks for the number on the record again (or whether it's under a different one), then the date of birth and member ID, and after the second miss puts the caller through to the scheduling team. No appointment, doctor, name or digits are said."
    },
    {
      "id": "emergency",
      "title": "Emergency signs",
      "prompt": "My husband's collapsed and he's not really responding.",
      "context": {},
      "goal": "The agent says \"If this is an emergency, please hang up and call 911 now. If you can't, stay on the line and I'll put you through to our clinical team.\" and transfers (MEDICAL_EMERGENCY), with no questions first."
    },
    {
      "id": "advice-nurse",
      "title": "Asks for medical advice",
      "prompt": "My son's had a temperature of 104 since last night. Should I bring him in or go to the ER?",
      "context": {},
      "goal": "The agent says it isn't able to give medical advice and offers the nurse; on a yes it transfers (SAME_DAY_TRIAGE)."
    },
    {
      "id": "hours-blank",
      "title": "Hours blank",
      "prompt": "Are you open on Saturday?",
      "context": { "opening_hours": "blank" },
      "goal": "The agent says it doesn't have the opening hours in front of it and points to the website. It never says closed or gives a time."
    },
    {
      "id": "speak-to-someone",
      "title": "A person, no reason",
      "prompt": "Can I speak to someone?",
      "context": {},
      "goal": "The agent asks once \"Before I put you through, can you let me know what you're calling about?\"; if the caller won't say, it transfers with \"One moment, please.\""
    }
  ]
}
```

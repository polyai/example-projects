```json
{
  "scenarios": [
    {
      "id": "schedule-appointment",
      "title": "Schedule a new service appointment",
      "prompt": "I need to schedule a service visit.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services",
        "service_types": [
          "General Service",
          "Deep Clean",
          "Emergency Repair",
          "Maintenance Check"
        ]
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith",
        "ZIP": "12345"
      },
      "goal": "When the caller ID is 2015550123 (or in chat with no caller ID) ANI matches John Smith; from any other number the agent verifies the caller first (see ani-miss-verify). Agent enters schedule_appointment, verifies ZIP 12345, collects service type (General Service) and location (kitchen), asks for a date/time preference, offers an open window (for example tomorrow 1pm-4pm or the day after 9am-12pm), and confirms the booking"
    },
    {
      "id": "confirm-upcoming-appointment",
      "title": "Confirm an upcoming appointment",
      "prompt": "I'm calling to confirm my appointment.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith"
      },
      "goal": "With ANI matched to John Smith (caller ID 2015550123, or chat), agent identifies John Smith at 123 Main St, finds appointment MOCK-APT-001 (tomorrow 9am-12pm), and confirms the details"
    },
    {
      "id": "reschedule-appointment",
      "title": "Reschedule an existing appointment",
      "prompt": "I need to reschedule my appointment to a different day.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith"
      },
      "goal": "With ANI matched to John Smith, agent finds the appointment (tomorrow 9am-12pm), offers available windows, and confirms the reschedule"
    },
    {
      "id": "cancel-appointment",
      "title": "Cancel an existing appointment",
      "prompt": "I need to cancel my service appointment.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith"
      },
      "goal": "With ANI matched to John Smith, agent finds appointment MOCK-APT-001 (tomorrow 9am-12pm). With the default setting (cancel_appointment_flow_enabled off) the agent transfers to customer care and the call ends (mock handoff in sandbox and draft). With the setting on, it confirms it is the right appointment, asks for a reason, and processes the cancellation"
    },
    {
      "id": "ani-miss-verify",
      "title": "ANI miss - verify user by phone and ZIP",
      "prompt": "I'd like to schedule a visit.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178",
        "Name": "Jane Doe",
        "ZIP": "12345"
      },
      "goal": "Caller ID does not match (a real call from any number other than 2015550123). Agent enters verify_user, collects phone 2125550178, matches Jane Doe on the first lookup, verifies ZIP 12345, and enters schedule_appointment"
    },
    {
      "id": "faq-services",
      "title": "FAQ - what services are offered",
      "prompt": "What services do you offer?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services",
        "service_types": [
          "General Service",
          "Deep Clean",
          "Emergency Repair",
          "Maintenance Check"
        ]
      },
      "context": {},
      "goal": "Agent lists available service types: General Service, Deep Clean, Emergency Repair, Maintenance Check"
    },
    {
      "id": "faq-need-to-be-home",
      "title": "FAQ - do I need to be home",
      "prompt": "Do I need to be home?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {},
      "goal": "Agent explains outdoor work doesn't require presence, indoor work needs someone to let the technician in"
    },
    {
      "id": "verify-unknown-number-readback",
      "title": "Unknown number read back, then corrected",
      "prompt": "I'd like to schedule a visit.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "First number given": "2015550199",
        "Correct phone": "2125550178",
        "Name": "Jane Doe",
        "ZIP": "12345"
      },
      "goal": "Caller says they are not calling from the number on the account and gives 2015550199. Agent cannot find it and reads it back as \"Sorry, did you say two zero one, then five five five, and finally zero one nine nine, is that right?\". Caller corrects it to 2125550178; agent looks it up, matches Jane Doe, verifies ZIP 12345, and continues to scheduling"
    },
    {
      "id": "phone-number-pause-partial",
      "title": "Pause and partial phone number",
      "prompt": "Can I schedule a new service appointment?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith",
        "ZIP": "12345"
      },
      "goal": "From a number that is not on the account, the caller says \"Yes, the phone number is\" and pauses, then gives only \"two zero one\", then \"two zero one five five five zero one to three\". Agent says \"Go ahead\" or asks for the full ten-digit number (offering the keypad and pound key), treats \"to\" as two, looks up 2015550123, verifies ZIP 12345 and continues to scheduling. It never transfers the caller because of trouble collecting the number"
    },
    {
      "id": "speak-to-someone",
      "title": "Ask for a person",
      "prompt": "Can I talk to someone?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {},
      "goal": "Agent first offers to help itself. When the caller declines, it says \"Sure, I'll put you through to a colleague. One moment please.\" and the call ends (mock handoff in sandbox and draft)"
    }
  ]
}
```

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
        "Phone": "5550001234",
        "Name": "John Smith",
        "ZIP": "12345"
      },
      "goal": "ANI matches John Smith, agent enters schedule_appointment flow, collects service type (General Service), location (kitchen), asks for date/time preference, offers 9am-12pm slot, confirms booking"
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
        "Phone": "5550001234",
        "Name": "John Smith"
      },
      "goal": "Agent identifies John Smith at 123 Main St, finds appointment MOCK-APT-001 (General Service, tomorrow 9am-12pm), and confirms the details"
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
        "Phone": "5550001234",
        "Name": "John Smith"
      },
      "goal": "Agent finds John Smith's appointment (tomorrow 9am-12pm), offers available slots, and confirms the reschedule"
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
        "Phone": "5550001234",
        "Name": "John Smith"
      },
      "goal": "Agent finds John Smith's appointment MOCK-APT-001 (tomorrow 9am-12pm), confirms it's the right one, asks for reason, and processes the cancellation"
    },
    {
      "id": "ani-miss-verify",
      "title": "ANI miss — verify user by phone and ZIP",
      "prompt": "I'd like to schedule a visit.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "5550005678",
        "Name": "Jane Doe",
        "ZIP": "12345"
      },
      "goal": "ANI does not match (voice call from unknown number), agent enters verify_user flow, collects phone 5550005678, matches Jane Doe, verifies ZIP 12345, enters schedule_appointment"
    },
    {
      "id": "faq-services",
      "title": "FAQ — what services are offered",
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
      "title": "FAQ — do I need to be home",
      "prompt": "Do I need to be home?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {},
      "goal": "Agent explains outdoor work doesn't require presence, indoor work needs someone to let the technician in"
    }
  ]
}
```
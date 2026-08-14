```json
{
  "scenarios": [
    {
      "id": "book-appointment",
      "title": "Booking happy path — existing patient",
      "prompt": "I'd like to schedule an appointment.",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {
        "Phone": "5550001234",
        "Name": "Jane Smith",
        "DOB": "March 15, 1985",
        "Patient type": "existing"
      },
      "goal": "Agent starts IDNV: confirms phone (yes), collects DOB (March 15, 1985), collects name (Jane Smith). Then enters Booking Flow, asks if existing patient (yes), collects appointment type, offers available slot with Dr. Smith, and confirms the booking."
    },
    {
      "id": "cancel-appointment",
      "title": "Cancel — patient with multiple appointments",
      "prompt": "I need to cancel an appointment.",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {
        "Phone": "5550005678",
        "Name": "John Doe",
        "DOB": "July 22, 1990"
      },
      "goal": "Agent starts IDNV: confirms phone (yes), collects DOB (July 22, 1990), collects name (John Doe). Then enters Cancel Flow, shows 2 upcoming appointments (Recheck and Ill Visit), asks which to cancel, collects reason, and confirms the cancellation."
    },
    {
      "id": "reschedule-appointment",
      "title": "Reschedule an appointment",
      "prompt": "Can I move my appointment to a different day?",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {
        "Phone": "5550001234",
        "Name": "Jane Smith",
        "DOB": "March 15, 1985"
      },
      "goal": "Agent starts IDNV: confirms phone (yes), collects DOB (March 15, 1985), collects name (Jane Smith). Then enters Reschedule Flow, finds Recheck appointment, offers available slots, and confirms the rescheduled appointment."
    },
    {
      "id": "new-patient-booking",
      "title": "New patient tries to book — handoff",
      "prompt": "Hi, I'm a new patient and I'd like to make an appointment.",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {
        "Phone": "5559999999",
        "Name": "Unknown"
      },
      "goal": "Agent starts IDNV but cannot find a matching patient record (phone not in system). Transfers to scheduling team for new patient registration."
    },
    {
      "id": "faq-hours",
      "title": "FAQ — clinic hours",
      "prompt": "What are your hours?",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {},
      "goal": "Agent answers with clinic hours from the knowledge base, no IDNV needed."
    },
    {
      "id": "faq-insurance",
      "title": "FAQ — accepted insurance",
      "prompt": "Do you accept Blue Cross?",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {},
      "goal": "Agent answers the insurance question from the knowledge base, no IDNV needed."
    }
  ]
}
```

```json
{
  "scenarios": [
    {
      "id": "book-appointment",
      "title": "Booking happy path - existing patient",
      "prompt": "I'd like to schedule an appointment.",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "Jane Smith",
        "DOB": "March 15, 1985",
        "Patient type": "existing"
      },
      "goal": "Agent asks whether the number the caller is calling from is on the account. From 2015550123 the caller says yes; from any other number the caller says no and gives 2015550123, and the agent reads it back as \"two zero one, then five five five, and finally zero one two three, is that right?\". Agent collects DOB (March 15, 1985) and name (Jane Smith), enters Booking Flow, asks if existing patient (yes), collects appointment type, offers an available slot with Dr. Smith three or four days out, and confirms the booking."
    },
    {
      "id": "cancel-appointment",
      "title": "Cancel - patient with multiple appointments",
      "prompt": "I need to cancel an appointment.",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {
        "Phone": "2125550178",
        "Name": "John Doe",
        "DOB": "July 22, 1990"
      },
      "goal": "Agent completes IDNV for John Doe (phone 2125550178 read back digit by digit with \"zero\", DOB July 22, 1990, name John Doe). Enters Cancel Flow, finds 2 upcoming appointments (a recheck and a sick visit), asks which to cancel, reads back the chosen appointment with its type and date, collects a reason, and confirms the cancellation."
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
        "Phone": "2015550123",
        "Name": "Jane Smith",
        "DOB": "March 15, 1985"
      },
      "goal": "Agent completes IDNV for Jane Smith (phone 2015550123, DOB March 15, 1985, name Jane Smith). Enters Reschedule Flow, reads back the appointment with its type and a readable date (e.g. \"a recheck on <date>\"), offers available slots, and confirms the rescheduled appointment."
    },
    {
      "id": "new-patient-booking",
      "title": "New patient tries to book - handoff",
      "prompt": "Hi, I'm a new patient and I'd like to make an appointment.",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {
        "Phone": "2015550199",
        "Name": "Unknown"
      },
      "goal": "Agent starts IDNV but finds no patient record for 2015550199. Monday to Friday, 8am to 5pm New York time, it says it is transferring to the scheduling team and the call ends (mock handoff in sandbox and draft). Out of hours it says Poly Clinic is closed and gives the opening hours instead of transferring."
    },
    {
      "id": "faq-hours",
      "title": "FAQ - clinic hours",
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
      "title": "FAQ - accepted insurance",
      "prompt": "Do you accept Blue Cross?",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {},
      "goal": "Agent answers the insurance question from the knowledge base, no IDNV needed."
    },
    {
      "id": "phone-readback-correction",
      "title": "Correct the phone number at readback",
      "prompt": "I'd like to schedule an appointment.",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {
        "First number given": "2015550128",
        "Correct phone": "2015550123",
        "Name": "Jane Smith",
        "DOB": "March 15, 1985"
      },
      "goal": "Caller says the calling number is not on the account and gives 2015550128. Agent reads it back digit by digit using \"zero\", never \"oh\". Caller says the last digit is three; agent takes the correction, reads back \"two zero one, then five five five, and finally zero one two three, is that right?\", and only moves on to DOB after the caller confirms. Identity is verified without a transfer."
    },
    {
      "id": "speak-to-doctor",
      "title": "Ask to speak to a doctor",
      "prompt": "I need to speak with my doctor.",
      "attributes": {
        "variant": "Poly Clinic",
        "clinic_name": "Poly Clinic"
      },
      "context": {},
      "goal": "Agent does not start booking or IDNV and does not ask for phone, DOB, or name. Monday to Friday, 8am to 5pm New York time, it says it is transferring the caller and the call ends (mock handoff in sandbox and draft). Out of hours it says Poly Clinic is closed and gives the opening hours without offering a transfer."
    }
  ]
}
```

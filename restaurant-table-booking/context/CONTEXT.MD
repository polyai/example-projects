```json
{
  "scenarios": [
    {
      "id": "make-new-booking",
      "title": "Make a new reservation",
      "prompt": "Hi, I'd like to book a table.",
      "attributes": {
        "variant": "Poly Bistro Downtown",
        "site_name": "Poly Bistro Downtown"
      },
      "context": {
        "Name": "Alex Turner",
        "Phone": "5550009999",
        "Party size": "2",
        "Requested day": "tomorrow",
        "Requested time": "7pm"
      },
      "goal": "Agent collects party size (2), date (tomorrow) and time (7pm), checks availability, confirms the 19:00 slot is open, collects name (Alex Turner) and phone (5550009999), finalizes the booking and reads back a confirmation"
    },
    {
      "id": "make-booking-offer-alternatives",
      "title": "Book when the exact time is unavailable",
      "prompt": "Can I get a table for four tomorrow at 5pm?",
      "attributes": {
        "variant": "Poly Bistro Downtown",
        "site_name": "Poly Bistro Downtown"
      },
      "context": {
        "Name": "Alex Turner",
        "Phone": "5550009999",
        "Party size": "4",
        "Requested day": "tomorrow",
        "Requested time": "5pm"
      },
      "goal": "Agent checks availability for tomorrow at 17:00, finds nothing at 5pm, offers nearby available slots (e.g. 6pm/7pm/8pm) within the search window, and books the caller's chosen alternative"
    },
    {
      "id": "cancel-existing-booking",
      "title": "Cancel an existing reservation",
      "prompt": "I need to cancel my reservation.",
      "attributes": {
        "variant": "Poly Bistro Downtown",
        "site_name": "Poly Bistro Downtown"
      },
      "context": {
        "Name": "John Smith",
        "Phone": "5550001234"
      },
      "goal": "Agent looks up bookings by phone (5550001234), finds John Smith's single reservation for tomorrow at 7pm (party 4), confirms it is the right one, cancels it via the API and confirms the cancellation"
    },
    {
      "id": "modify-existing-booking",
      "title": "Modify an existing reservation",
      "prompt": "I'd like to change my booking.",
      "attributes": {
        "variant": "Poly Bistro Downtown",
        "site_name": "Poly Bistro Downtown"
      },
      "context": {
        "Name": "Jane Doe",
        "Phone": "5550005678",
        "New party size": "4"
      },
      "goal": "Agent looks up bookings by phone (5550005678), finds Jane Doe's reservation for the day after tomorrow at 8pm (party 2), collects the change (party size to 4), modifies the booking via the API and confirms the update"
    },
    {
      "id": "large-party-overflow",
      "title": "Party larger than the site maximum",
      "prompt": "I want a table for ten people this weekend.",
      "attributes": {
        "variant": "Poly Bistro Downtown",
        "site_name": "Poly Bistro Downtown"
      },
      "context": {
        "Name": "Alex Turner",
        "Phone": "5550009999",
        "Party size": "10"
      },
      "goal": "Agent recognizes party size 10 exceeds the Downtown maximum of 8, explains it cannot book online for large parties, and directs the caller to the group booking form (large_party_sms)"
    },
    {
      "id": "no-booking-found",
      "title": "Caller with no reservation on file",
      "prompt": "Can you look up my reservation?",
      "attributes": {
        "variant": "Poly Bistro Downtown",
        "site_name": "Poly Bistro Downtown"
      },
      "context": {
        "Name": "Sam Rivers",
        "Phone": "5559990000"
      },
      "goal": "Agent searches by phone (5559990000), finds no reservations, tells the caller nothing is on file and offers to make a new booking"
    }
  ]
}
```

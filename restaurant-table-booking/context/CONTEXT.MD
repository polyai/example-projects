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
        "Phone": "2015550199",
        "Party size": "2",
        "Requested day": "tomorrow",
        "Requested time": "7pm"
      },
      "goal": "Agent collects party size (2), date (tomorrow) and time (7pm), checks availability, confirms the 7pm slot is open, collects name (Alex Turner) and phone, reads the phone back as \"two zero one, then five five five, and finally zero one nine nine, is that right?\" before saving it, finalizes the booking and reads back a confirmation. The call stays connected after the agent asks for the first and last name"
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
        "Phone": "2015550199",
        "Party size": "4",
        "Requested day": "tomorrow",
        "Requested time": "5pm"
      },
      "goal": "Agent checks availability for tomorrow at 5pm, finds nothing at 5pm, offers the nearest open times (6pm or 7pm), and books the caller's chosen alternative"
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
        "Phone": "2015550123"
      },
      "goal": "Agent collects the phone (2015550123), reads it back digit by digit, finds John Smith's single reservation for tomorrow at 7pm (party 4), confirms it is the right one, cancels it via the API and confirms the cancellation"
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
        "Phone": "2125550178",
        "New party size": "4"
      },
      "goal": "Agent looks up bookings by phone (2125550178), finds Jane Doe's reservation for the day after tomorrow at 8pm (party 2), collects the change (party size to 4), modifies the booking via the API and confirms the update"
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
        "Phone": "2015550199",
        "Party size": "10",
        "Text to": "2015550199"
      },
      "goal": "Agent recognizes party size 10 exceeds the Downtown maximum of 8, explains it cannot book online for large parties, and offers to text the group booking form link (large_party_sms). If the caller accepts, a Studio test call has no caller ID, so the agent asks for the number to text (2015550199), reads it back as \"two zero one, then five five five, and finally zero one nine nine, is that right?\", and after the caller confirms says the link was sent or that it could not send it and asks for another number. The call stays connected through the number steps. If the caller declines the text, the agent transfers during opening hours (mock handoff in sandbox and draft) or gives the closed message"
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
        "Phone": "2015550199"
      },
      "goal": "Agent searches by phone (2015550199), finds no reservations, checks the number with the caller and offers to try a different number. If the caller gives the same number again, the agent searches again and after the second miss transfers the caller (or gives the closed message outside opening hours). If the caller has no other number, the agent asks whether there is anything else it can help with"
    },
    {
      "id": "speak-to-human",
      "title": "Ask for a person",
      "prompt": "I want to speak to someone.",
      "attributes": {
        "variant": "Poly Bistro Downtown",
        "site_name": "Poly Bistro Downtown"
      },
      "context": {},
      "goal": "Agent first offers to help itself. When the caller asks again, during opening hours it says it is transferring and the call ends (mock handoff in sandbox and draft); outside opening hours it says the restaurant is closed and offers voicemail"
    }
  ]
}
```

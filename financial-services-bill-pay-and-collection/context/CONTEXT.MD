# Financial Services template (card and loan accounts)

Confirms who the caller is, tells them their balance and due date, takes a payment with a card or bank account on file (today or up to 30 days ahead), answers questions about payments, fees, cards and the app in a sentence or two, texts help steps, and puts callers through to the right team, with fraud and vulnerable customers first.

- **Shape (flat):** one flow per task, each with one advanced step and a short numbered prompt. `account_balance` and `make_payment` start with an entry function step that checks strict ID&V. Rules live in tool code (`functions/billing.py`, `functions/payments.py`, `functions/idnv.py`, `functions/handoff.py`); tools say what to ask, offer or read back. Done lines and transfer lines are tool utterances.
- **ID&V (strict):** the phone number on the account, date of birth and account number, all on one record. With a usable caller ID: "Is your account under the number you're calling from?" (a yes or an "okay" uses it; it's never said). Nothing given for the check is read back. A mismatch says only "those details don't match" and asks for all three again; two mismatches transfer.
- **Payments:** more than $0, no more than the balance (checked first), no more than $2,500 by phone, a method on file, today or up to 30 days ahead. Readback: "So that's $50 from your Visa ending four two four two, going out today. Shall I make that payment?" After a change, only the change. An acknowledgement to that question is a yes; an "okay" to information is not; a same-turn yes is refused in code.
- **Texts:** help steps to the calling number or a number read back first; a payment confirmation only to the calling number or the account's number.
- **Safety:** fraud, scams and lost cards go to the fraud or cards team with no ID&V first; danger to life transfers straight away with the 911 line; other vulnerability signs get one offer of the support team.
- **Company facts:** variant attributes on the one default variant. Blank `opening_hours` is never treated as closed, and a day that isn't listed is unknown.
- **Data:** `functions/api_client.py`, mocked outside live until `settings.use_mock_api` is false.
- **Fixtures:** John Smith 201-555-0123, 1985-03-15, 1234567890 ($150, Visa ending 4242, $50 scheduled); Jane Doe 212-555-0178, 1990-07-22, 0987654321 ($275.50, checking ending 6789); Alex Rivera 201-555-0144, 1978-11-02, 2468013579 ($8,400, two methods); Sam Lee 201-555-0166, 1982-06-30, 1357924680 ($150 overdue); Robin Park 201-555-0177, 1975-01-09, 1122334455 (the payment API errors); 201-555-0199 has no account.

## Test scenarios

```json
{
  "scenarios": [
    {
      "id": "check-balance",
      "title": "Check balance",
      "prompt": "I'd like to check my balance.",
      "attributes": { "site_name": "Poly Bank" },
      "context": {
        "Phone": "2015550123",
        "DOB": "1985-03-15",
        "Account Number": "1234567890"
      },
      "goal": "The agent asks for the phone number on the account, the date of birth and the account number, one at a time, never reads them back, then says the balance is $150 with its due date and the $50 payment already scheduled"
    },
    {
      "id": "make-payment",
      "title": "Make a payment",
      "prompt": "I want to make a payment on my account.",
      "attributes": { "site_name": "Poly Bank" },
      "context": {
        "Phone": "2015550123",
        "DOB": "1985-03-15",
        "Account Number": "1234567890",
        "Amount": "$50"
      },
      "goal": "After verification the agent asks how much, reads back $50 from the Visa ending four two four two, going out today, asks \"Shall I make that payment?\", takes it on a yes or an okay, and gives a confirmation number in fours and a new balance of $100"
    },
    {
      "id": "payment-over-balance",
      "title": "Payment larger than the balance",
      "prompt": "I want to pay five hundred dollars.",
      "attributes": { "site_name": "Poly Bank" },
      "context": {
        "Phone": "2015550123",
        "DOB": "1985-03-15",
        "Account Number": "1234567890"
      },
      "goal": "The agent says the balance is $150 so it can't take more, takes nothing, and offers to take the full $150"
    },
    {
      "id": "wrong-dob",
      "title": "Wrong date of birth",
      "prompt": "I'd like to check my balance.",
      "attributes": { "site_name": "Poly Bank" },
      "context": {
        "Phone": "2015550123",
        "DOB": "1990-01-01",
        "Account Number": "1234567890"
      },
      "goal": "The agent says the details don't match without saying which, asks again, and after a second mismatch transfers the caller without revealing any account detail"
    },
    {
      "id": "sms-alt-number-readback",
      "title": "Text help to a different number",
      "prompt": "How do I change my address?",
      "attributes": { "site_name": "Poly Bank" },
      "context": { "Text to": "2125550178" },
      "goal": "The agent says it can be changed in the app under Settings and then My details, offers to text the steps, reads the number back as two one two, five five five, zero one seven eight, and sends it after the caller agrees"
    },
    {
      "id": "fraud-transfer",
      "title": "Report card fraud",
      "prompt": "Someone has used my card without my permission.",
      "attributes": { "site_name": "Poly Bank" },
      "context": {},
      "goal": "The agent says it's putting the caller through to the fraud team and transfers (mock handoff in sandbox and draft)"
    }
  ]
}
```

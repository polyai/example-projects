# Financial Services template (bill pay and payments)

Tells verified callers their balance, takes payments toward it with a card or bank account on file (today or a later date), answers billing and banking FAQs, and texts help links.

- **Shape (flat):** one flow per task, each with one advanced step and a short numbered prompt. Task flows (`account_balance`, `make_payment`) start with an entry function step that checks strict ID&V. Rules live in tool code (`functions/billing.py`, `functions/idnv.py`); tools say what to read back and what to ask next; the payment tools end with a CALL STATE block. Miss and retry returns name the attempt and say to call the same tool again (Dialog-RSN-1 won't on its own); `send_text` alone reads back or refuses an SMS number. No keypad entry: `dtmf_config` works on Raven 3.5 only.
- **ID&V (strict):** the phone number on the account, date of birth and account number, all on one record (`flows/verify_caller`). The caller ID never verifies on its own. Retry limits, the fail path and "never say which detail was wrong" are in `functions/idnv.py`. Every account task, the payment tools and the payment-confirmation text check it in code.
- **Payment rules (code):** more than $0, no more than the balance, no more than $2,500 by phone, from a method on file, today or up to 30 days ahead. The write tool gives the readback as one short yes-or-no question ("Shall I pay $50.00 from your Visa ending 4242 today, yes or no?"), then only changes; `make_payment` needs `caller_confirmed` (a clear yes, on a later turn than the question).
- **Company facts:** variant attributes on the one default variant (`site_name`, location attributes, `timezone`, `website_url`, `*_info` facts, `fraud_phone_number`). Out-of-hours handling reads `opening_hours` and `timezone` from the variant; real-time config `flags.ooh_enabled` only switches it on. Blank or unreadable `opening_hours` (onboarding leaves it blank when unchecked) means never out of hours, and the agent says it doesn't have the exact hours to hand; keep it blank rather than filling a default.
- **Data:** `functions/api_client.py`. Mocked on branch, draft and sandbox; on pre-release and live until `settings.use_mock_api` is false. Mock payments live in `conv.state`.
- **Fixtures:** John Smith 201-555-0123, DOB 1985-03-15, account 1234567890 ($150.00 due, Visa ending 4242, $50 already scheduled); Jane Doe 212-555-0178, 1990-07-22, 0987654321 ($275.50); Alex Rivera 201-555-0144, 1978-11-02, 2468013579 ($8,400.00, for the phone limit); 201-555-0199 has no account.

## Test scenarios

```json
{
  "scenarios": [
    {
      "id": "check-balance",
      "title": "Check balance",
      "prompt": "I'd like to check my balance.",
      "attributes": {"site_name": "Poly Bank"},
      "context": {"Phone": "2015550123", "DOB": "1985-03-15", "Account Number": "1234567890"},
      "goal": "The agent asks for the phone number on the account, the date of birth and the account number, one at a time, then says the balance is $150.00, due in 14 days, with a $50.00 payment already scheduled"
    },
    {
      "id": "make-payment",
      "title": "Make a payment",
      "prompt": "I want to make a payment on my account.",
      "attributes": {"site_name": "Poly Bank"},
      "context": {"Phone": "2015550123", "DOB": "1985-03-15", "Account Number": "1234567890", "Amount": "$50"},
      "goal": "After verification the agent asks how much, reads back $50.00 from the Visa ending 4242 today in one sentence, takes it on a yes, and gives a confirmation number and a new balance of $100.00"
    },
    {
      "id": "payment-over-balance",
      "title": "Payment larger than the balance",
      "prompt": "I want to pay five hundred dollars.",
      "attributes": {"site_name": "Poly Bank"},
      "context": {"Phone": "2015550123", "DOB": "1985-03-15", "Account Number": "1234567890"},
      "goal": "The agent says $500 is more than the $150.00 balance, takes nothing, and asks how much to pay instead"
    },
    {
      "id": "wrong-dob",
      "title": "Wrong date of birth",
      "prompt": "I'd like to check my balance.",
      "attributes": {"site_name": "Poly Bank"},
      "context": {"Phone": "2015550123", "DOB": "1990-01-01", "Account Number": "1234567890"},
      "goal": "The agent says the details don't match without saying which, asks again, and after a second mismatch transfers the caller without revealing any account detail"
    },
    {
      "id": "sms-alt-number-readback",
      "title": "Text help to a different number",
      "prompt": "I've forgotten my customer number.",
      "attributes": {"site_name": "Poly Bank"},
      "context": {"Text to": "2125550178"},
      "goal": "The agent offers a text with the steps, reads the number back as two one two, five five five, zero one seven eight, and sends it after the caller confirms"
    },
    {
      "id": "fraud-transfer",
      "title": "Report card fraud",
      "prompt": "Someone has used my card without my permission.",
      "attributes": {"site_name": "Poly Bank"},
      "context": {},
      "goal": "The agent says it's putting the caller through to the fraud team and transfers (mock handoff in sandbox and draft)"
    }
  ]
}
```

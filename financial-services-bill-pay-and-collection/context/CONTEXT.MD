```json
{
  "scenarios": [
    {
      "id": "check-balance",
      "title": "Check account balance",
      "prompt": "I'd like to check my balance.",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {
        "Account Number": "1234567890",
        "Name": "John Smith",
        "DOB": "1985-03-15"
      },
      "goal": "Agent asks for the account number and looks it up in the same turn the caller gives it, without saying it is checking and then going quiet. It asks for the date of birth (March 15, 1985) before reading anything out, then reports a balance of $150.00 with a pending $50.00 payment to Electric Company scheduled 14 days from today"
    },
    {
      "id": "make-payment-app",
      "title": "Make a bill payment via app",
      "prompt": "I want to make a payment on my account.",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {
        "Account Number": "1234567890",
        "Name": "John Smith",
        "DOB": "1985-03-15",
        "Amount": "$50",
        "Channel": "app"
      },
      "goal": "Agent verifies identity, shows balance of $150.00, collects $50 amount, offers app/online/phone, caller chooses app, agent gives app instructions"
    },
    {
      "id": "make-payment-phone-handoff",
      "title": "Make a bill payment over the phone (handoff)",
      "prompt": "I want to make a payment on my account.",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {
        "Account Number": "1234567890",
        "Name": "John Smith",
        "DOB": "1985-03-15",
        "Amount": "$50",
        "Channel": "phone"
      },
      "goal": "Agent verifies identity, collects the $50 amount, caller chooses phone, agent says \"Sure, I'll transfer you to our payments team who can take your card details securely.\" and the call ends (mock handoff in sandbox and draft)"
    },
    {
      "id": "transfer-domestic",
      "title": "Domestic money transfer over the phone",
      "prompt": "I want to transfer money to someone.",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {
        "Account Number": "1234567890",
        "Name": "John Smith",
        "DOB": "1985-03-15",
        "Transfer type": "domestic",
        "Amount": "$50",
        "Recipient": "Jane Doe",
        "Recipient account": "9876543210"
      },
      "goal": "Agent verifies identity, collects domestic transfer details (first name, last name, account number - each spelled/read back for confirmation), processes via mock API, returns confirmation number and new balance ($100.00)"
    },
    {
      "id": "check-balance-casual-phrasing",
      "title": "Balance check with casual phrasing",
      "prompt": "Can you tell me my balance?",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {
        "Account Number": "1234567890",
        "Name": "John Smith",
        "DOB": "the 15th of the 3rd, 1985"
      },
      "goal": "Caller gives the account number as \"My number is 1234567890\" and the date of birth as \"the 15th of the 3rd, 1985\". Agent looks the account up straight away, accepts the date of birth as March 15, 1985, and reads the $150.00 balance only after the date of birth is confirmed, with no long silence after the account number"
    },
    {
      "id": "check-balance-jane",
      "title": "Check balance for second test customer",
      "prompt": "Hi, I need to check my account balance please.",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {
        "Account Number": "0987654321",
        "Name": "Jane Doe",
        "DOB": "1990-07-22"
      },
      "goal": "Agent verifies Jane Doe's identity (DOB: 1990-07-22), retrieves account 0987654321, and reports balance of $275.50 with no pending payments"
    },
    {
      "id": "unknown-account",
      "title": "Caller with unrecognized account",
      "prompt": "Hi, I need to pay my bill.",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {
        "Account Number": "0000000000",
        "Name": "Unknown"
      },
      "goal": "Agent cannot find the account and asks the caller to verify their account number or routes to a live agent for assistance"
    },
    {
      "id": "sms-alt-number-readback",
      "title": "Text help to a different number",
      "prompt": "I can't log in to the app.",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {
        "Text to": "2125550178"
      },
      "goal": "Agent offers to text the caller help. Caller asks for it to go to a different number, 2125550178. Agent says \"Thanks. Just to confirm, that was two one two, then five five five, and finally zero one seven eight, is that right?\" and, after the caller confirms, says the text was sent or that it could not send it, without asking for the number again"
    },
    {
      "id": "fraud-transfer",
      "title": "Report card fraud",
      "prompt": "Someone has used my card without my permission.",
      "attributes": {
        "bank_name": "Poly Bank"
      },
      "context": {},
      "goal": "Agent acknowledges the urgency, says \"I understand the urgency. Let me transfer you to our fraud team right away.\", and the call ends (mock handoff in sandbox and draft)"
    }
  ]
}
```

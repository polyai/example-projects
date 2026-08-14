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
      "goal": "Agent verifies John Smith's identity (DOB: 1985-03-15), retrieves account 1234567890, and reports balance of $150.00 with a pending $50.00 payment to Electric Company on July 1st"
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
      "goal": "Agent verifies identity, collects $50 amount, caller chooses phone, agent says 'I'll transfer you to our payments team for card details' and hands off"
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
      "goal": "Agent verifies identity, collects domestic transfer details (first name, last name, account number — each spelled/read back for confirmation), processes via mock API, returns confirmation number and new balance ($100.00)"
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
    }
  ]
}
```

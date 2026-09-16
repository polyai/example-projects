```json
{
  "scenarios": [
    {
      "id": "track-shipped-order",
      "title": "Track a shipped order",
      "prompt": "Hi, I'd like to check on my order status.",
      "attributes": {
        "variant": "Poly Store",
        "brand_name": "Poly Store"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith",
        "Zipcode": "10001",
        "Last 4 of order": "7561"
      },
      "goal": "Agent verifies John Smith (phone + zipcode), disambiguates via last-4 (7561) since John has multiple orders, finds order P1032847561 (Running Shoes + Sport Socks), and reports it is shipped via UPS with carrier info. The call stays connected after the agent asks for the phone number"
    },
    {
      "id": "track-by-order-number",
      "title": "Track an order by order number",
      "prompt": "I want to check on my order, but I'd rather give you my order number.",
      "attributes": {
        "variant": "Poly Store",
        "brand_name": "Poly Store"
      },
      "context": {
        "Order number": "P1032847561",
        "Name": "John Smith",
        "Zipcode": "10001"
      },
      "goal": "Agent moves from the phone number question to asking for the full order number (a long number that may start with P, which can also be typed on the keypad). Caller gives P1032847561, the agent asks for the billing zip code, caller gives 10001, and the agent reports the Running Shoes and Sport Socks have shipped with UPS without asking for the last 4. The call stays connected through the order number and zip code steps"
    },
    {
      "id": "check-processing-order",
      "title": "Check a processing order",
      "prompt": "Where is my backpack order?",
      "attributes": {
        "variant": "Poly Store",
        "brand_name": "Poly Store"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith",
        "Zipcode": "10001",
        "Last 4 of order": "1204"
      },
      "goal": "Agent verifies identity, finds order P1032891204 (Backpack), reports it is still processing with no tracking available yet"
    },
    {
      "id": "delivered-order-status",
      "title": "Check a delivered order (single order, skips last-4)",
      "prompt": "I want to check if my sneakers arrived.",
      "attributes": {
        "variant": "Poly Store",
        "brand_name": "Poly Store"
      },
      "context": {
        "Phone": "2125550178",
        "Name": "Jane Doe",
        "Zipcode": "90210"
      },
      "goal": "Agent verifies Jane Doe (single order, skips last-4 step), finds order P1031956738 (Sneakers), confirms delivered via FedEx"
    },
    {
      "id": "cancel-processing-order",
      "title": "Cancel an order that hasn't shipped",
      "prompt": "I want to cancel my order.",
      "attributes": {
        "variant": "Poly Store",
        "brand_name": "Poly Store"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith",
        "Zipcode": "10001",
        "Last 4 of order": "1204"
      },
      "goal": "Agent verifies identity, shows Backpack order (Processing), immediately asks for cancellation reason (order_action=cancel), confirms cancellation"
    },
    {
      "id": "modify-delivery-address",
      "title": "Change delivery address on a processing order",
      "prompt": "I need to change my delivery address.",
      "attributes": {
        "variant": "Poly Store",
        "brand_name": "Poly Store"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith",
        "Zipcode": "10001",
        "Last 4 of order": "1204",
        "New address": "200 Oak Avenue, Brooklyn, NY 11201"
      },
      "goal": "Agent verifies identity, shows Backpack order (Processing), enters modify flow (order_action=modify), collects new address with ASR biasing, confirms address update"
    },
    {
      "id": "sms-tracking-link-readback",
      "title": "Text the tracking link to a different number",
      "prompt": "Can you text me the tracking link for my order?",
      "attributes": {
        "variant": "Poly Store",
        "brand_name": "Poly Store"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith",
        "Zipcode": "10001",
        "Last 4 of order": "7561",
        "Text to": "2125550178"
      },
      "goal": "Agent verifies John Smith, finds order P1032847561, offers to text the tracking link, the caller asks for it to go to 2125550178, and the agent reads it back as \"I heard that as two one two, then five five five, and finally zero one seven eight, is that right?\". After the caller confirms, the agent says the text was sent or that there was a problem sending it, without asking for the number again"
    },
    {
      "id": "speak-to-agent",
      "title": "Ask for a person",
      "prompt": "I want to speak to an agent.",
      "attributes": {
        "variant": "Poly Store",
        "brand_name": "Poly Store"
      },
      "context": {},
      "goal": "Agent offers to help once. When the caller insists, it says it is putting them through and the call ends (mock handoff in sandbox and draft)"
    }
  ]
}
```

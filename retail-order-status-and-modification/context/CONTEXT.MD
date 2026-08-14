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
        "Phone": "5550001234",
        "Name": "John Smith",
        "Zipcode": "10001",
        "Last 4 of order": "7561"
      },
      "goal": "Agent verifies John Smith (phone + zipcode), disambiguates via last-4 (7561) since John has multiple orders, finds order P1032847561 (Running Shoes + Sport Socks), and reports it is shipped via UPS with carrier info"
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
        "Phone": "5550001234",
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
        "Phone": "5550005678",
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
        "Phone": "5550001234",
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
        "Phone": "5550001234",
        "Name": "John Smith",
        "Zipcode": "10001",
        "Last 4 of order": "1204",
        "New address": "200 Oak Avenue, Brooklyn, NY 11201"
      },
      "goal": "Agent verifies identity, shows Backpack order (Processing), enters modify flow (order_action=modify), collects new address with ASR biasing, confirms address update"
    }
  ]
}
```

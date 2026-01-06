# Agent Integration

How to integrate your AI agent with UAPK Gateway.

## Overview

Instead of calling tools directly, your agent will:

1. Register with the gateway
2. Obtain capability tokens
3. Submit action requests
4. Handle responses (approved/denied)

## Step 1: Create a Manifest

Create a UAPK Manifest describing your agent:

```json
{
  "$schema": "https://uapk.dev/schemas/manifest.v1.json",
  "version": "1.0",
  "agent": {
    "id": "my-agent",
    "name": "My AI Agent",
    "version": "1.0.0",
    "description": "Agent that helps with customer support",
    "organization": "org-acme"
  },
  "capabilities": {
    "requested": [
      "email:send",
      "email:read",
      "crm:read"
    ]
  },
  "constraints": {
    "max_actions_per_hour": 100
  },
  "metadata": {
    "contact": "team@acme.com",
    "documentation": "https://docs.acme.com/my-agent"
  }
}
```

## Step 2: Register the Agent

Submit your manifest to the gateway (future API):

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @manifest.json
```

## Step 3: Obtain Capability Token

Request a capability token (issued by operator or automated):

```json
{
  "token_id": "cap-xyz",
  "agent_id": "my-agent",
  "capabilities": ["email:send"],
  "expires_at": "2024-01-15T22:00:00Z"
}
```

## Step 4: Submit Action Requests

When your agent wants to perform an action:

```python
import httpx

async def send_email(to: str, subject: str, body: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://gateway:8000/api/v1/gateway/execute",
            headers={
                "X-API-Key": AGENT_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "uapk_id": "my-agent",
                "agent_id": "my-agent",
                "action": {
                    "type": "email",
                    "tool": "send",
                    "params": {
                        "to": to,
                        "subject": subject,
                        "body": body,
                    },
                },
                "capability_token": CAPABILITY_TOKEN,
                "context": {
                    "conversation_id": current_conversation_id,
                    "reason": "User requested email notification",
                },
            },
        )
        return response.json()
```

## Step 5: Handle Responses

```python
result = await send_email(...)

if result["status"] == "approved":
    # Action was executed
    message_id = result["result"]["message_id"]
    print(f"Email sent: {message_id}")

elif result["status"] == "denied":
    # Action was blocked by policy
    reason = result["reason"]
    print(f"Action denied: {reason}")

    # Inform the user appropriately
    if "rate limit" in reason.lower():
        return "I've sent too many emails recently. Please try again later."

elif result["status"] == "pending":
    # Requires human approval
    print("Waiting for human approval...")
```

## Best Practices

1. **Request minimum capabilities**: Only ask for what you need
2. **Provide context**: Include reason and conversation ID
3. **Handle denials gracefully**: Don't retry immediately
4. **Log interactions**: Keep your own records for debugging
5. **Respect budgets**: Check remaining quota before actions

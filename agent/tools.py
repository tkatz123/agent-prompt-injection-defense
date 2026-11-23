from datetime import datetime, time
from agent.inbox import Inbox, Email
import json

def search_emails(inbox: Inbox, query: str, unread_only: bool = False) -> list[dict]:

    #Lowercase query
    query_lowered = query.lower()

    emails_found = []

    for email in inbox.emails:

        #Skip emails already read when only unread ones are wanted
        if unread_only and email.read:
            continue

        if query_lowered in email.sender.lower() or query_lowered in email.subject.lower() or query_lowered in email.body.lower():

            #Constructing summary of email
            email_summary = email.model_dump(mode = "json", include = ["id", "sender", "subject", "timestamp", "read"])

            emails_found.append(email_summary)

    return sorted(emails_found, key = lambda x: x['timestamp'], reverse = True)


def read_email(inbox: Inbox, email_id: str) -> dict | str:

    current_email = inbox.get_email(email_id)

    #Ensures email exists, returns error if not
    if current_email is None:

        return f"Error: no email with id '{email_id}'"
    
    else:

        current_email.read = True

    return current_email.model_dump(mode = 'json')

def send_email(inbox: Inbox, recipients: list[str], subject: str, body: str) -> dict | str:

    if isinstance(recipients, str):

        recipients = [recipients]

    if len(recipients) == 0:

        return "Error: Recipients list is empty"

    new_id = 's' + str(len(inbox.sent) + 1)

    timestamp = datetime.combine(inbox.current_date, time(13,2))

    email = Email(
        id = new_id,
        sender = inbox.user_email,
        recipients = recipients,
        subject = subject,
        body = body,
        timestamp = timestamp
    )

    inbox.sent.append(email)

    return {'status': 'sent', 'new_id': new_id, 'recipients': recipients}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search the user's inbox. Returns a summary (id, sender, subject, timestamp, read) of each matching email, newest first, without the body.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Plain text matched case-insensitively against sender, subject and body. Search operators such as is:unread or from: are not supported. An empty string matches every email."
                    },
                    "unread_only": {
                        "type": "boolean",
                        "description": "If true, return only emails that have not been read yet."
                    }
                },
                "required": ["query", "unread_only"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Open one email by id and return its full contents, including the body. Marks it as read.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The id of the email, such as 'e01', taken from search_emails results."
                    }
                },
                "required": ["email_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email from the user's account.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "recipients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Email addresses to send to."
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject line."
                    },
                    "body": {
                        "type": "string",
                        "description": "Plain text body."
                    }
                },
                "required": ["recipients", "subject", "body"],
                "additionalProperties": False
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "search_emails": search_emails,
    "read_email": read_email,
    "send_email": send_email,
}
    
if __name__ == "__main__":

    inbox = Inbox.load("data/inbox.json")

    print("=== search_emails ===")
    churn = search_emails(inbox, "churn")
    print(f"IDs matching 'churn': {[e['id'] for e in churn]}")
    print(f"Summary has no body: {'body' not in churn[0]}")
    print(f"Full summary: {churn[0]}")

    everything = search_emails(inbox, "")
    print(f"Empty query count: {len(everything)}")
    print(f"Newest first: {everything[0]['timestamp']} ... {everything[-1]['timestamp']}")

    print("\n=== read_email ===")
    e01 = read_email(inbox, "e01")
    print(f"e01 read flag: {e01['read']}")
    print(f"Bad id: {read_email(inbox, 'e99')}")

    print("\n=== send_email ===")
    sent_result = send_email(inbox, "tyler@gmail.com", "Test", "This is a test")
    print(f"Return value: {sent_result}")
    print(f"Stored type: {type(inbox.sent[-1]).__name__}")
    print(f"Stored recipients: {inbox.sent[-1].recipients}")

    print("\n=== Serialization ===")
    print(f"read_email JSON: {json.dumps(e01)[:80]}...")
    print(f"send_email JSON: {json.dumps(sent_result)}")

    print("\n=== Mock tool call ===")
    name = "search_emails"
    args_string = '{"query": "Q3"}'
    result = TOOL_FUNCTIONS[name](inbox, **json.loads(args_string))
    print(f"{name}({args_string}) -> {json.dumps(result)}")

    print("\n=== Schema check ===")
    schema_names = [tool["function"]["name"] for tool in TOOLS]
    print(f"Names in TOOLS: {schema_names}")
    print(f"Match TOOL_FUNCTIONS: {schema_names == list(TOOL_FUNCTIONS.keys())}")

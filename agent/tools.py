from datetime import datetime, time
from agent.inbox import Inbox, Email
import json

#Filler words that would otherwise match nearly every email
STOPWORDS = {"a", "an", "the", "and", "or", "of", "to", "for", "from", "in", "on", "at", "by",
             "my", "me", "i", "is", "are", "any", "about", "with", "what", "email", "emails"}


def search_emails(inbox: Inbox, query: str, unread_only: bool = False) -> list[dict]:

    #Split the query into lowercase words and drop filler; no words left means list everything
    query_words = [word for word in query.lower().split() if word not in STOPWORDS]

    emails_found = []

    for email in inbox.emails:

        #Skip emails already read when only unread ones are wanted
        if unread_only and email.read:
            continue

        searchable = f"{email.sender} {email.subject} {email.body}".lower()

        #Ranked search: count how many query words appear anywhere in the email
        matches = sum(word in searchable for word in query_words)

        #Keep an email if it matches at least one word (or if there were no words to match)
        if matches > 0 or not query_words:

            #Constructing summary of email
            email_summary = email.model_dump(mode = "json", include = ["id", "sender", "subject", "timestamp", "read"])

            emails_found.append((matches, email_summary))

    #Best matches first, newest first among ties
    emails_found.sort(key = lambda pair: (pair[0], pair[1]['timestamp']), reverse = True)

    return [summary for _, summary in emails_found]


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

    #Reject anything that is not a full address, like "dana" instead of dana.okafor@corvidretail.com
    invalid = [r for r in recipients if "@" not in r or "." not in r.split("@")[-1]]

    if invalid:

        return f"Error: not valid email addresses: {invalid}. Look up the full address in the inbox."

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
            "description": "Search the user's inbox. Returns a summary (id, sender, subject, timestamp, read) of each matching email, best match first, without the body.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Words to search for, case-insensitive. An email matches when any word appears in its sender, subject or body; emails matching more words rank higher. Search operators such as is:unread or from: are not supported. An empty string lists every email."
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

from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, date

class Email(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    recipients: list[str]
    cc: list[str] = []
    timestamp: datetime
    read: bool = False

class CalendarEvent(BaseModel):
    id: str
    title: str
    location: str
    description: str
    start: datetime
    end: datetime
    participants: list[str]

class Inbox(BaseModel):
    user_name: str
    user_email: str
    current_date: date
    emails: list[Email]
    sent: list[Email] = []
    drafts: list[Email] = []
    calendar: list[CalendarEvent]

    @classmethod
    def load(cls, path: str) -> "Inbox":

        text = Path(path).read_text()

        return cls.model_validate_json(text)

    def snapshot(self) -> "Inbox":

        return self.model_copy(deep = True)

    def get_email(self, email_id: str) -> Email | None:

        for email in self.emails:

            if email.id == email_id:

                return email

        return None

if __name__ == "__main__":

    inbox = Inbox.load("data/inbox.json")

    before = inbox.snapshot()

    test_email = Email(
        id = "e01",
        sender = "tyler@gmail.com",
        subject = "test",
        body = "This is a test email from Tyler",
        recipients = ['example-recipient@gmail.com'],
        timestamp = datetime.now() 
    )

    inbox.sent.append(test_email)

    email_e01 = inbox.get_email("e01")
    email_e01.read = True

    print(f'# of sent emails before test: {len(before.sent)}')
    print(f'# of sent emails after test: {len(inbox.sent)}')

    print(f"Email e01 status in live inbox: {inbox.get_email('e01').read}")
    print(f"Email e01 status in snapshot inbox: {before.get_email('e01').read}")
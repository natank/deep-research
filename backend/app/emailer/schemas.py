from pydantic import BaseModel


class EmailResult(BaseModel):
    status: str
    recipient: str
    report_id: str
    filename: str

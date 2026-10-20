from sqlalchemy.orm import Session
from app.models import DispatchEvent

def publish(db: Session, company_id: int, kind: str, ref_id: int | None = None):
    db.add(DispatchEvent(company_id=company_id,kind=kind,ref_id=ref_id))

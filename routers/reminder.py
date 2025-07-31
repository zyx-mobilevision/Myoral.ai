from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from database import get_db, fetch_user_by_id

router = APIRouter()

@router.get("/reminder/{user_id}")
def reminder(user_id: str, db: Session = Depends(get_db)):
    # Appointment reminder within 24 hours
    user = fetch_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    appoint_date_str = getattr(user, "appointDate", None)
    if not appoint_date_str:
        return {"reminder": False, "message": "No appointment date set."}
    try:
        appoint_date = datetime.strptime(appoint_date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return {"reminder": False, "message": "Invalid appointDate format."}
    now = datetime.utcnow()
    delta = appoint_date - now
    if timedelta(0) < delta <= timedelta(hours=24):
        print(f"[REMINDER] User {user_id} has an appointment within 24 hours at {appoint_date_str}.")
        return {"reminder": True, "message": "Appointment is within 24 hours."}
    else:
        return {"reminder": False, "message": "No reminder needed."}
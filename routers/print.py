from fastapi import APIRouter
from database import get_db, User
import os

router = APIRouter()

@router.get("/print/users")
def print_users_and_masks():
    """
    打印所有用户信息（username和email），统计每个用户的mask数量，最后打印用户总数和mask总数。
    """
    db_gen = get_db()
    db = next(db_gen)
    users = db.query(User).all()
    db.close()
    total_masks = 0

    # 打印表头
    print(f"{'Username':<20} {'Email':<30} {'Mask Count':<10}")
    print("-" * 60)
    for user in users:
        user_id = user.userId
        username = getattr(user, "username", "")
        email = getattr(user, "email", "")
        mask_dir = os.path.join("masks", user_id)
        mask_count = 0
        if os.path.exists(mask_dir) and os.path.isdir(mask_dir):
            mask_count = len([f for f in os.listdir(mask_dir) if os.path.isdir(os.path.join(mask_dir, f))])
        total_masks += mask_count
        print(f"{username:<20} {email:<30} {mask_count:<10}")

    print("-" * 60)
    print(f"Total users: {len(users)}")
    print(f"Total masks: {total_masks}")
    return None

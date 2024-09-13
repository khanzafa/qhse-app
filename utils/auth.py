from flask_login import current_user
from app.models import UserPermission

def get_allowed_permission_ids():
    # Query the user permissions based on the current user
    user_permissions = UserPermission.query.filter_by(user_id=current_user.id).all()
    allowed_permission_ids = [p.permission_id for p in user_permissions]
    return allowed_permission_ids
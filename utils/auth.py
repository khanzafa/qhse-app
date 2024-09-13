from flask_login import current_user
from app.models import UserPermission

def get_allowed_permission_ids():
    if not current_user.is_authenticated:
        # Handle the case where the user is not authenticated
        return []

    user_permissions = UserPermission.query.filter_by(user_id=current_user.id).all()
    return [permission.id for permission in user_permissions]
import logging
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app.models import NotificationRule
from app import db
from app.forms import NotificationRuleForm
from utils.auth import get_allowed_permission_ids

logging.basicConfig(level=logging.DEBUG)

notification_bp = Blueprint('notification', __name__, url_prefix='/notification')

# NOTIFICATION
@notification_bp.route('/', methods=['GET'])
@notification_bp.route('/<int:id>', methods=['GET'])
def view(id=None):
    if id:
        notification = NotificationRule.query.get_or_404(id)
        notification = {
            'id': notification.id,
            'name': notification.name,
            'description': notification.description,
            'role': notification.role
        }
        return jsonify(notification), 200
    else:
        notifications = []
        for notification in NotificationRule.query.filter(NotificationRule.permission_id.in_(get_allowed_permission_ids())).all():
            notifications.append({
                'id': notification.id,
                'name': notification.name,
                'description': notification.description,
                'role': notification.role
            })        
        return jsonify(notifications), 200
    
@notification_bp.route('/', methods=['POST'])
def create():
    form = NotificationRuleForm()
    if form.validate_on_submit():
        notification = NotificationRule(
            name=form.name.data,
            description=form.description.data,
            role=session.get('role')
        )
        db.session.add(notification)
        db.session.commit()
        flash('Notification rule added successfully!')
        return Response(status=201)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@notification_bp.route('/<int:id>', methods=['PUT'])
def edit(id):
    notification = NotificationRule.query.get_or_404(id)
    form = NotificationRuleForm(obj=notification)
    if form.validate_on_submit():
        form.populate_obj(notification)
        db.session.commit()
        return Response(status=200)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@notification_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    notification = NotificationRule.query.get_or_404(id)
    db.session.delete(notification)
    db.session.commit()
    return Response(status=200)
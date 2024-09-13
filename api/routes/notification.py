import logging
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app.models import NotificationRule
from app import db
from app.forms import NotificationRuleForm
from utils.auth import get_allowed_permission_ids
from flasgger import swag_from

logging.basicConfig(level=logging.DEBUG)

notification_api_docs = {
    "view" : {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "integer",
                "required": False,
                "description": "Numeric ID of the notification to get"
            }
        ],
        "definitions": {
            "Notification": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer"
                    },
                    "name": {
                        "type": "string"
                    },
                    "description": {
                        "type": "string"
                    },
                    "role": {
                        "type": "string"
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "A list of notifications or a specific notification",
                "schema": {
                    "$ref": "#/definitions/Notification"
                }
            },
            "404": {
                "description": "Notification not found"
            }
        }
    },
    "create" : {
        "parameters": [
            {
                "name": "name",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Name of the notification"
            },
            {
                "name": "description",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Description of the notification"
            }
        ],
        "responses": {
            "201": {
                "description": "Notification rule created"
            },
            "400": {
                "description": "Form validation failed"
            }
        }
    },
    "edit" : {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "integer",
                "required": True,
                "description": "Numeric ID of the notification to edit"
            },
            {
                "name": "name",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Name of the notification"
            },
            {
                "name": "description",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Description of the notification"
            }
        ],
        "responses": {
            "200": {
                "description": "Notification rule edited"
            },
            "400": {
                "description": "Form validation failed"
            }
        }
    },
    "delete" : {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "integer",
                "required": True,
                "description": "Numeric ID of the notification to delete"
            }
        ],
        "responses": {
            "200": {
                "description": "Notification rule deleted"
            }
        }
    }
}


notification_bp = Blueprint('notification', __name__, url_prefix='/notification')

# NOTIFICATION
@notification_bp.route('/', methods=['GET'])
@notification_bp.route('/<int:id>', methods=['GET'])
@swag_from(notification_api_docs['view'])
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
@swag_from(notification_api_docs['create'])
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
@swag_from(notification_api_docs['edit'])
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
@swag_from(notification_api_docs['delete'])
def delete(id):
    notification = NotificationRule.query.get_or_404(id)
    db.session.delete(notification)
    db.session.commit()
    return Response(status=200)
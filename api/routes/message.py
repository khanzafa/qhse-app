import logging
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app.models import MessageTemplate
from app import db
from app.forms import MessageTemplateForm
from utils.auth import get_allowed_permission_ids
from flasgger import swag_from

message_api_docs = {
    "view" : {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "integer",
                "required": False,
                "description": "Numeric ID of the message to get"
            }
        ],
        "definitions": {
            "Message": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer"
                    },
                    "name": {
                        "type": "string"
                    },
                    "template": {
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
                "description": "A list of messages or a specific message",
                "schema": {
                    "$ref": "#/definitions/Message"
                }
            },
            "404": {
                "description": "Message not found"
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
                "description": "Name of the message"
            },
            {
                "name": "template",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Template of the message"
            }
        ],
        "responses": {
            "201": {
                "description": "Message added successfully"
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
                "description": "Numeric ID of the message to edit"
            },
            {
                "name": "name",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Name of the message"
            },
            {
                "name": "template",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "Template of the message"
            }
        ],
        "responses": {
            "200": {
                "description": "Message updated successfully"
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
                "description": "Numeric ID of the message to delete"
            }
        ],
        "responses": {
            "200": {
                "description": "Message deleted successfully"
            }
        }
    }
}

logging.basicConfig(level=logging.DEBUG)

message_bp = Blueprint('message', __name__, url_prefix='/message')

# MESSAGE
@message_bp.route('/', methods=['GET'])
@message_bp.route('/<int:id>', methods=['GET'])
@swag_from(message_api_docs['view'])
def view(id=None):
    if id:
        message = MessageTemplate.query.get_or_404(id)
        message = {
            'id': message.id,
            'name': message.name,
            'template': message.template,
            'role': message.role
        }
        return jsonify(message), 200
    else:
        messages = []
        for message in MessageTemplate.query.filter(MessageTemplate.permission_id.in_(get_allowed_permission_ids())).all():
            messages.append({
                'id': message.id,
                'name': message.name,
                'template': message.template,
                'role': message.role
            })        
        return jsonify(messages), 200
    
@message_bp.route('/', methods=['POST'])    
@swag_from(message_api_docs['create'])
def create():
    form = MessageTemplateForm()
    if form.validate_on_submit():
        message = MessageTemplate(
            name=form.name.data,
            template=form.template.data,
            role=session.get('role')
        )
        db.session.add(message)
        db.session.commit()
        flash('Message template added successfully!')
        return Response(status=201)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@message_bp.route('/<int:id>', methods=['PUT'])
@swag_from(message_api_docs['edit'])
def edit(id):
    message = MessageTemplate.query.get_or_404(id)
    form = MessageTemplateForm(obj=message)
    if form.validate_on_submit():
        form.populate_obj(message)
        db.session.commit()
        return Response(status=200)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@message_bp.route('/<int:id>', methods=['DELETE'])
@swag_from(message_api_docs['delete'])
def delete(id):
    message = MessageTemplate.query.get_or_404(id)
    db.session.delete(message)
    db.session.commit()
    return Response(status=200)
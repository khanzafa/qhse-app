import logging
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app.models import MessageTemplate
from app import db
from app.forms import MessageTemplateForm
from utils.auth import get_allowed_permission_ids

logging.basicConfig(level=logging.DEBUG)

message_bp = Blueprint('message', __name__, url_prefix='/message')

# MESSAGE
@message_bp.route('/', methods=['GET'])
@message_bp.route('/<int:id>', methods=['GET'])
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
def delete(id):
    message = MessageTemplate.query.get_or_404(id)
    db.session.delete(message)
    db.session.commit()
    return Response(status=200)
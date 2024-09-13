import logging
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app.models import Contact
from app import db
from app.forms import ContactForm
from utils.auth import get_allowed_permission_ids

logging.basicConfig(level=logging.DEBUG)

contact_bp = Blueprint('contact', __name__, url_prefix='/contact')

# CONTACT
@contact_bp.route('/', methods=['GET'])
@contact_bp.route('/<int:id>', methods=['GET'])
def view(id=None):
    if id:
        contact = Contact.query.get_or_404(id)
        contact = {
            'id': contact.id,
            'phone_number': contact.phone_number,
            'name': contact.name,
            'description': contact.description
        }
        return jsonify(contact), 200
    else:
        contacts = []
        for contact in Contact.query.filter(Contact.permission_id.in_(get_allowed_permission_ids())).all():
            contacts.append({
                'id': contact.id,
                'phone_number': contact.phone_number,
                'name': contact.name,
                'description': contact.description
            })        
        return jsonify(contacts), 200
    
@contact_bp.route('/', methods=['POST'])
def create():
    form = ContactForm()
    if form.validate_on_submit():
        contact = Contact(
            phone_number=form.phone_number.data,
            name=form.name.data,
            description=form.description.data,
            role=session.get('role')
        )
        db.session.add(contact)
        db.session.commit()
        flash('Contact added successfully!')
        return Response(status=201)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)


@contact_bp.route('/<int:id>', methods=['PUT'])
def edit(id):
    contact = Contact.query.get_or_404(id)
    form = ContactForm(obj=contact)
    if form.validate_on_submit():
        form.populate_obj(contact)
        db.session.commit()
        flash('Contact updated successfully!')
        return Response(status=200)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@contact_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    contact = Contact.query.get_or_404(id)
    db.session.delete(contact)
    db.session.commit()
    flash('Contact deleted successfully!')
    return Response(status=200)
import os
from datetime import datetime
from base64 import b64encode
from flask import Blueprint, Response, abort, render_template, redirect, url_for, flash, session, jsonify
from app.models import DetectorType, Weight
from app import db
from app.forms import ModelForm
import logging

from utils.auth import get_allowed_permission_ids

logging.basicConfig(level=logging.DEBUG)
weight_bp = Blueprint('weight', __name__, url_prefix='/weight')

# MODEL
@weight_bp.route('/', methods=['GET'])
@weight_bp.route('/<int:id>', methods=['GET'])
def view(id=None):
    if id:
        weight = Weight.query.get_or_404(id)
        weight = {
            'id': weight.id,
            'name': weight.name,
            'detector_type_id': weight.detector_type_id,
            'file': weight.file,
            'path': weight.path,
            'created_at': weight.created_at,
            'role': weight.role
        }
        return jsonify(weight), 200
    else:
        weights = []
        for weight in Weight.query.filter(Weight.permission_id.in_(get_allowed_permission_ids())).all():
            weights.append({
                'id': weight.id,
                'name': weight.name,
                'detector_type_id': weight.detector_type_id,
                'file': weight.file,
                'path': weight.path,
                'created_at': weight.created_at,
                'role': weight.role
            })        
        return jsonify(weights), 200
    
@weight_bp.route('/', methods=['POST'])
def create():
    form = ModelForm()
    if form.validate_on_submit():
        role_dir = os.path.join('weights', session.get('role'))
        if not os.path.exists(role_dir):
            os.makedirs(role_dir)
        form.file.data.save(os.path.join(role_dir, form.file.data.filename))
        new_model = Weight(
            name=form.name.data,
            detector_type_id=form.detector_type.data,
            file=form.file.data.read(),
            path=os.path.join(role_dir, form.file.data.filename),
            created_at=datetime.now(),
            role=session.get('role')
        )
        db.session.add(new_model)
        db.session.commit()
        flash('Model added successfully!')
        return Response(status=201)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@weight_bp.route('/<int:id>', methods=['PUT'])
def edit(id):
    model = Weight.query.get_or_404(id)
    form = ModelForm(obj=model)
    if form.validate_on_submit():
        model.name = form.name.data
        model.detector_type_id = form.detector_type.data
        model.file = form.file.data.read()
        model.path = os.path.join('weights', session.get('role'), form.file.data.filename)
        model.created_at = datetime.now()
        model.role = session.get('role')
        db.session.commit()
        flash('Model updated successfully!')
        return Response(status=200)
    else:
        logging.debug(f"Form validation failed: {form.errors}")
    abort(400)

@weight_bp.route('/<int:id>', methods=['DELETE'])
def delete(id):
    model = Weight.query.get_or_404(id)
    db.session.delete(model)
    db.session.commit()
    return Response(status=204)


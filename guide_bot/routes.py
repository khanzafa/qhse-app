# guide_bot/routes.py
import io
from flask import Blueprint, abort, render_template, redirect, send_file, url_for, flash, request
from guide_bot.models import Document
from guide_bot.forms import DocumentForm
from app import db

guide_bot = Blueprint('guide_bot', __name__)

@guide_bot.route('/guide-bot/documents', methods=['GET', 'POST'])
def manage_documents():
    form = DocumentForm()
    documents = Document.query.all()

    if form.validate_on_submit():
        new_document = Document(
            title=form.title.data,
            file=form.file.data.read()
        )
        db.session.add(new_document)
        db.session.commit()
        flash('Document added successfully!')
        return redirect(url_for('guide_bot.manage_documents'))

    return render_template('guide_bot/manage_documents.html', form=form, documents=documents)

@guide_bot.route('/guide-bot/documents/edit/<int:id>', methods=['GET', 'POST'])
def edit_document(id):
    document = Document.query.get_or_404(id)
    form = DocumentForm(obj=document)

    if form.validate_on_submit():
        document.title = form.title.data
        document.file = form.file.data.read()
        db.session.commit()
        flash('Document updated successfully!')
        return redirect(url_for('guide_bot.manage_documents'))

    return render_template('guide_bot/edit_document.html', form=form, document=document)

@guide_bot.route('/guide-bot/documents/delete/<int:id>', methods=['POST'])
def delete_document(id):
    document = Document.query.get_or_404(id)
    db.session.delete(document)
    db.session.commit()
    flash('Document deleted successfully!')
    return redirect(url_for('guide_bot.manage_documents'))

@guide_bot.route('/guide-bot/documents/view/<int:id>')
def view_document(id):
    document = Document.query.get_or_404(id)
    return render_template('guide_bot/view_document.html', document=document)

@guide_bot.route('/guide-bot/document/file/<int:document_id>')
def get_document_file(document_id):
    document = Document.query.get_or_404(document_id)
    if document.file:
        # Set appropriate MIME type based on file type
        return send_file(io.BytesIO(document.file), mimetype='application/pdf', as_attachment=False)
    else:
        abort(404)
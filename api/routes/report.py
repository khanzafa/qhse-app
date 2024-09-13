from flask import Blueprint, Response, abort, render_template, redirect, url_for, flash, session, jsonify
from app.models import *
from app import db
from app.forms import *
import logging
from utils.auth import get_allowed_permission_ids

logging.basicConfig(level=logging.DEBUG)

report_bp = Blueprint('report', __name__, url_prefix='/report')

# REPORT

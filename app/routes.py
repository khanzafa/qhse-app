import requests
from flask import Blueprint, render_template, request

web_bp = Blueprint('web', __name__, url_prefix='/web')

@web_bp.route('/cctv', methods=['GET'])
@web_bp.route('/cctv/<int:id>', methods=['GET'])
def cctv(id=None):
    if id:
        cctvs = requests.get(f'http://localhost:5000/cctv/{id}')
    else:
        cctvs = requests.get('http://localhost:5000/cctv')
    return render_template('cctv.html', cctvs=cctvs.json())
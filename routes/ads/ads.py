from flask import render_template, Blueprint, request, redirect, send_from_directory, jsonify
from database import db
from ..dashboard.ads.ads import ad_image_path, AD_IMAGE_DIR

ads_page = Blueprint('ads', __name__, url_prefix='/ads')

@ads_page.route('/<advert_id>')
def serve_image(advert_id):
    path = ad_image_path(advert_id)
    if not path:
        abort(404)
    return send_from_directory(AD_IMAGE_DIR,path)

@ads_page.route('/')
def get_ad():
    selected = db.select_advert()
    if not selected: return jsonify(None)
    return jsonify({"id":selected[0], "duration": selected[2]})
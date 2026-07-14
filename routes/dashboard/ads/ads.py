import os
from flask import render_template, Blueprint, request, redirect, send_from_directory, abort
from database import db

ads_page = Blueprint('ads', __name__, url_prefix='/ads')

AD_IMAGE_DIR = "data/ads"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def ad_image_path(advert_id):
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        path = os.path.join(AD_IMAGE_DIR, f"{advert_id}.{ext}")
        if os.path.exists(path):
            return f"{advert_id}.{ext}"
    return None


def build_ad_dict(advert):
    """Turns a raw advert row into a template-friendly dict, injecting the
    computed cost_per_view since it isn't stored on the row itself."""
    print(advert)
    return {
        'id': advert[0],
        'account_id': advert[1],
        'duration': advert[2],
        'spend_limit': advert[3],
        'total_spent': advert[4]+advert[9],
        'status': advert[5],
        'weight': advert[6],
        'reference': advert[7],
        'cost_per_view': db.get_ad_cost_100_views(advert[0]),
    }


@ads_page.before_request
def check_login():
    if not request.user:
        return redirect('/login')


def get_owned_advert_or_404(advert_id):
    """Fetches an advert and checks it belongs to one of the current
    user's accounts. Returns the raw advert row, or aborts with 404."""
    advert = db.get_advert(advert_id)
    if not advert:
        abort(404)
    account = db.get_account(advert[1], request.user[0])
    if not account:
        abort(404)
    return advert


@ads_page.route('/')
def ads_dashboard():
    accounts = db.get_accounts(request.user[0])
    ads = []
    for account in accounts:
        for advert in db.get_adverts(account_id=account[0]):
            ads.append(build_ad_dict(advert))
    return render_template('dashboard/ads/ads.jinja', user=request.user, ads=ads)


@ads_page.route('/create', methods=['GET', 'POST'])
def create():
    accounts_raw = db.get_accounts(request.user[0])
    accounts = []
    for account in accounts_raw:
        accounts.append({
            'id': account[0],
            'name': account[2],
            'balance': db.get_balance(account[0]),
        })

    if request.method == 'GET':
        return render_template('dashboard/ads/create.jinja', user=request.user, accounts=accounts)

    account_id = request.form.get('account')
    duration = request.form.get('duration')
    weight = request.form.get('weight')
    spend_limit = request.form.get('spend_limit')
    reference = request.form.get('reference', '')
    image = request.files.get('image')

    account = db.get_account(account_id, request.user[0])
    if not account:
        return render_template('dashboard/ads/create.jinja', user=request.user, accounts=accounts, error="Invalid account selected.")

    try:
        duration = int(duration)
        weight = float(weight)
        spend_limit_cents = round(float(spend_limit) * 100)
    except (TypeError, ValueError):
        return render_template('dashboard/ads/create.jinja', user=request.user, accounts=accounts, error="Invalid input.")

    if duration <= 0:
        return render_template('dashboard/ads/create.jinja', user=request.user, accounts=accounts, error="Duration must be positive.")
    if weight <= 0:
        return render_template('dashboard/ads/create.jinja', user=request.user, accounts=accounts, error="Weight must be positive.")
    if spend_limit_cents <= 0:
        return render_template('dashboard/ads/create.jinja', user=request.user, accounts=accounts, error="Spend limit must be positive.")

    if not image or image.filename == '':
        return render_template('dashboard/ads/create.jinja', user=request.user, accounts=accounts, error="Please upload an image.")

    ext = image.filename.rsplit('.', 1)[-1].lower() if '.' in image.filename else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return render_template('dashboard/ads/create.jinja', user=request.user, accounts=accounts, error="Unsupported image type.")

    advert_id = db.insert_advert(account_id, duration, spend_limit_cents, weight=weight, reference=reference)
    db.commit()

    os.makedirs(AD_IMAGE_DIR, exist_ok=True)
    image.save(os.path.join(AD_IMAGE_DIR, f"{advert_id}.{ext}"))

    return redirect(f'/dashboard/ads/{advert_id}')


@ads_page.route('/<advert_id>')
def view(advert_id):
    advert = get_owned_advert_or_404(advert_id)
    ad = build_ad_dict(advert)

    charges_raw = db.get_advert_costs(advert_id)
    charges = []
    for charge in charges_raw:
        charges.append({
            'amount': charge[3],
            'date': charge[4],
        })
    charges.reverse()

    return render_template('dashboard/ads/edit.jinja', user=request.user, ad=ad, charges=charges)


@ads_page.route('/<advert_id>/edit', methods=['POST'])
def edit(advert_id):
    advert = get_owned_advert_or_404(advert_id)

    duration = request.form.get('duration')
    weight = request.form.get('weight')
    reference = request.form.get('reference', '')

    ad = build_ad_dict(advert)

    try:
        duration = int(duration)
        weight = float(weight)
    except (TypeError, ValueError):
        return render_template('dashboard/ads/edit.jinja', user=request.user, ad=ad, charges=[], error="Invalid input.")

    if duration <= 0 or weight <= 0:
        return render_template('dashboard/ads/edit.jinja', user=request.user, ad=ad, charges=[], error="Duration and weight must be positive.")

    db.update_advert(advert_id, duration=duration, weight=weight, reference=reference)
    db.commit()

    return redirect(f'/dashboard/ads/{advert_id}')


@ads_page.route('/<advert_id>/top-up', methods=['POST'])
def top_up(advert_id):
    advert = get_owned_advert_or_404(advert_id)

    spend_limit = request.form.get('spend_limit')
    try:
        new_limit_cents = round(float(spend_limit) * 100)
    except (TypeError, ValueError):
        return redirect(f'/dashboard/ads/{advert_id}')

    if new_limit_cents <= advert[4]:  # must exceed total_spent to actually reactivate
        new_limit_cents = advert[4] + 1

    db.top_up_advert(advert_id, new_limit_cents)
    db.commit()

    return redirect(f'/dashboard/ads/{advert_id}')


@ads_page.route('/<advert_id>/disable', methods=['POST'])
def disable(advert_id):
    get_owned_advert_or_404(advert_id)
    db.disable_advert(advert_id)
    db.commit()
    return redirect(f'/dashboard/ads/{advert_id}')


@ads_page.route('/<advert_id>/image')
def serve_image(advert_id):
    get_owned_advert_or_404(advert_id)
    path = ad_image_path(advert_id)
    if not path:
        abort(404)
    return send_from_directory(AD_IMAGE_DIR,path)
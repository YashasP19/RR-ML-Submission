"""HTTP routes: the page, and a small JSON API the page (or anyone else) can call."""
from flask import Blueprint, current_app, jsonify, render_template, request

from .content import LIMITS, STEPS, UNIQUE
from .data_store import FIELDS

pages = Blueprint("pages", __name__)
api = Blueprint("api", __name__)


def store():
    return current_app.config["STORE"]


@pages.route("/")
def index():
    return render_template("index.html")


@api.route("/health")
def health():
    try:
        s = store()
        ok = all(len(s.players(k)) > 0 for k in FIELDS)
        s.metrics()
    except FileNotFoundError as e:
        return jsonify(status="degraded", error=str(e)), 503
    return jsonify(status="ok" if ok else "degraded")


def _kind_or_404(kind):
    if kind not in FIELDS:
        return None, (jsonify(error=f"kind must be one of {sorted(FIELDS)}"), 404)
    return kind, None


@api.route("/rankings/<kind>")
def rankings(kind):
    kind, err = _kind_or_404(kind)
    if err:
        return err
    n = max(1, min(request.args.get("limit", 10, type=int), 50))
    players = store().top(kind, n)
    return jsonify(kind=kind, count=len(players), players=players)


@api.route("/players/<kind>")
def players(kind):
    kind, err = _kind_or_404(kind)
    if err:
        return err
    q = request.args.get("q", "", type=str).strip()[:60]
    sort = request.args.get("sort", "rank")
    allowed = {"rank", "pressureBalls", "pTop10", "elevation", "consistency"}
    if sort not in allowed:
        return jsonify(error=f"sort must be one of {sorted(allowed)}"), 400
    limit = max(1, min(request.args.get("limit", 100, type=int), 200))
    rows = store().search(kind, q, sort, limit)
    return jsonify(kind=kind, query=q, count=len(rows), players=rows)


@api.route("/players/<kind>/<slug>")
def player_detail(kind, slug):
    kind, err = _kind_or_404(kind)
    if err:
        return err
    p = store().player(kind, slug)
    if p is None:
        return jsonify(error="player not found"), 404
    return jsonify(p)


@api.route("/metrics")
def metrics():
    return jsonify(store().metrics())


@api.route("/method")
def method():
    return jsonify(steps=STEPS, limitations=LIMITS, unique=UNIQUE)


@api.errorhandler(FileNotFoundError)
def missing_results(e):
    return jsonify(error=str(e)), 503

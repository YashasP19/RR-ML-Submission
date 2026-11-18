import pytest

from webapp import create_app


@pytest.fixture(scope="module")
def client():
    return create_app().test_client()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json["status"] == "ok"


@pytest.mark.parametrize("kind", ["batters", "bowlers"])
def test_top10_ranked_and_unique(client, kind):
    players = client.get(f"/api/rankings/{kind}").json["players"]
    assert [p["rank"] for p in players] == list(range(1, 11))
    assert len({p["name"] for p in players}) == 10


def test_search_and_detail(client):
    rows = client.get("/api/players/batters?q=tim").json["players"]
    assert rows and all("tim" in p["name"].lower() for p in rows)
    slug = rows[0]["slug"]
    assert client.get(f"/api/players/batters/{slug}").json["name"] == rows[0]["name"]
    assert client.get("/api/players/batters/nobody-here").status_code == 404


def test_bad_inputs(client):
    assert client.get("/api/rankings/umpires").status_code == 404
    assert client.get("/api/players/batters?sort=hack").status_code == 400
    assert client.get("/api/rankings/batters?limit=9999").json["count"] <= 50


def test_metrics_method_and_page(client):
    m = client.get("/api/metrics").json
    assert m["matches"] > 0 and 0 < m["reliability"]["bowlerEconomy"] < 1
    method = client.get("/api/method").json
    assert len(method["steps"]) == 6 and all(s["why"] for s in method["steps"]) and len(method["unique"]) >= 3 and all(u["concept"] for u in method["unique"])
    assert b"Pressure Players" in client.get("/").data

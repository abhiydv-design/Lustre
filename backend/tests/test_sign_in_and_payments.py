"""Guest first, phone sign-in at first save or purchase."""
import hashlib
import hmac
import json

from tests.conftest import generate, make_product, new_phone, sign_in


def test_guest_signs_in_and_keeps_everything(client, guest):
    pid = make_product(client, guest)
    gid = generate(client, guest, pid).json()["id"]
    auth, phone = sign_in(client, guest)
    assert auth == guest  # same account, now with a phone
    me = client.get("/me", headers=auth).json()
    assert me["guest"] is False and me["phone"].startswith("+91") and me["credits"] == 2
    assert client.get(f"/generations/{gid}/download", headers=auth).status_code == 200


def test_new_phone_login_and_merge_into_existing_account(client):
    member, phone = sign_in(client)
    pid_old = make_product(client, member)
    # Same person, new phone handset: starts as a guest, makes something, then signs in
    guest2 = {"Authorization": "Bearer " + client.post("/auth/start").json()["token"]}
    pid_new = make_product(client, guest2)
    auth, _ = sign_in(client, guest2, phone=phone)
    assert auth == member
    names = {p["id"] for p in client.get("/products", headers=auth).json()}
    assert names == {pid_old, pid_new}
    assert client.get("/me", headers=auth).json()["credits"] == 3  # guest trial not added on top
    assert client.get("/me", headers=guest2).status_code == 401  # old guest token retired


def test_otp_errors_are_friendly_and_limited(client):
    assert client.post("/auth/otp/request", json={"phone": "12345"}).json()["detail"]["code"] == "invalid_phone"
    phone = new_phone()
    client.post("/auth/otp/request", json={"phone": phone})
    wrong = client.post("/auth/otp/verify", json={"phone": phone, "code": "000000"})
    assert wrong.status_code == 400 and wrong.json()["detail"]["code"] in ("wrong_code",)
    client.post("/auth/otp/request", json={"phone": phone})
    client.post("/auth/otp/request", json={"phone": phone})
    assert client.post("/auth/otp/request", json={"phone": phone}).status_code == 429


def test_trial_is_once_per_phone_even_after_account_deletion(client):
    auth, phone = sign_in(client)
    assert client.delete("/me", headers=auth).status_code == 204
    guest = {"Authorization": "Bearer " + client.post("/auth/start").json()["token"]}
    auth2, _ = sign_in(client, guest, phone=phone)
    assert client.get("/me", headers=auth2).json()["credits"] == 0


def test_payment_webhook_credits_once(client, member):
    order = client.post("/payments/orders", headers=member, json={"pack": "shop"}).json()
    assert order["amount"] == 99900
    body = json.dumps({"event": "order.paid", "payload": {"payment": {"entity": {"order_id": order["order_id"]}}}}).encode()
    sig = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()
    assert client.post("/payments/webhook", content=body, headers={"X-Razorpay-Signature": "bad"}).status_code == 400
    for _ in range(2):
        assert client.post("/payments/webhook", content=body, headers={"X-Razorpay-Signature": sig}).status_code == 200
    me = client.get("/me/credits", headers=member).json()
    assert me["balance"] == 53 and me["transactions"][0]["reason"] == "purchase"

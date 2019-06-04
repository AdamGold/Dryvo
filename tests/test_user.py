import os
import pytest

from server.api.blueprints import user
from server.api.database.models import Teacher


def test_make_teacher(user, auth, requester):
    auth.login()
    resp = requester.post("/user/make_teacher", json={"price": 100, "crn": 9999})
    assert resp.json["data"]["user"]["id"] == user.id
    teacher = Teacher.query.filter_by(user=user).first()
    assert teacher
    assert not teacher.is_approved


@pytest.mark.parametrize(
    ("price", "crn", "message"),
    ((None, 100, "Empty fields."), (-20, 100, "Price must be above 0.")),
)
def test_invalid_make_teacher(user, auth, crn, requester, price, message):
    auth.login()
    resp = requester.post("/user/make_teacher", json={"price": price, "crn": crn})
    assert resp.status_code == 400
    assert resp.json.get("message") == message


def test_make_student(user, auth, requester):
    auth.login()
    resp = requester.get(f"/user/make_student?teacher_id=1")
    assert resp.json["data"]["my_teacher"]["teacher_id"] == 1
    teacher = Teacher.get_by_id(1)
    assert resp.json["data"]["price"] == teacher.price


def test_make_student_with_price(user, auth, requester):
    auth.login()
    resp = requester.get(f"/user/make_student?teacher_id=1&price=1000")
    assert resp.json["data"]["price"] == 1000


def test_teacher_make_student(user, teacher, auth, requester):
    auth.login(email=teacher.user.email)
    resp = requester.get(f"/user/make_student?user_id={user.id}")
    assert resp.json["data"]["my_teacher"]["teacher_id"] == 1


def test_make_student_invalid_teacher(user, auth, requester):
    auth.login()
    resp = requester.get(f"/user/make_student?teacher_id=3")
    assert resp.status_code == 400
    assert resp.json.get("message") == "Teacher was not found."


def test_make_student_already_assigned(
    app, student, teacher, auth, requester, db_instance
):
    with app.app_context():
        auth.login(email=student.user.email)
        resp = requester.get(f"/user/make_student?teacher_id=1")
        assert "already a student" in resp.json.get("message")


def test_register_token(auth, requester):
    auth.login()
    resp = requester.post("/user/register_firebase_token", json={"token": "some token"})
    assert "successfully" in resp.json.get("message")


def test_delete_token(auth, requester):
    auth.login()
    resp = requester.get("/user/delete_firebase_token")
    assert "successfully" in resp.json.get("message")


def test_me_student(auth, user, requester, student):
    auth.login(email=student.user.email)
    resp = requester.get("/user/me")
    assert student.user.id == resp.json["user"]["id"]
    assert student.id == resp.json["user"]["student_id"]
    assert student.teacher_id == resp.json["user"]["my_teacher"]["teacher_id"]


def test_me_teacher(auth, user, requester, teacher):
    auth.login(email=teacher.user.email)
    resp = requester.get("/user/me")
    assert teacher.user.id == resp.json["user"]["id"]
    assert teacher.id == resp.json["user"]["teacher_id"]


def test_me_not_teacher_or_student(auth, user, requester):
    auth.login()
    resp = requester.get("/user/me")
    assert user.id == resp.json["user"]["id"]


def test_get_user_info(teacher):
    info = teacher.user.role_info()
    assert "teacher_id" in info
    assert "price" in info


def test_search_users(user, teacher, auth, requester):
    auth.login(teacher.user.email)
    resp = requester.get(f"/user/search?name={user.name}")
    assert resp.json["data"][0]["id"] == user.id


@pytest.mark.skip
def test_upload_image(user, auth, requester):
    """skip this one so we won't upload an image to cloudinary
    on each tests - the test passes though"""
    auth.login()
    image = os.path.join("./tests/assets/av.png")
    file = (image, "av.png")
    resp = requester.post(
        "/user/image", data={"image": file}, content_type="multipart/form-data"
    )
    assert requester.get(resp.json["image"])

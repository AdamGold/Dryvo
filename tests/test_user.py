import os
import pytest

from server.api.blueprints import user


def test_make_teacher(user, admin, auth, requester):
    auth.login(admin.email, "test")
    resp = requester.post(
        "/user/make_teacher",
        json={"user_id": user.id, "price": 100, "phone": "052222222"},
    )
    assert resp.json["data"]["user"]["id"] == user.id


def test_not_admin_make_teacher(user, auth, requester):
    auth.login()
    resp = requester.post(
        "/user/make_teacher",
        json={"user_id": user.id, "price": 100, "phone": "052222222"},
    )
    assert resp.json.get("message") == "Not authorized."


@pytest.mark.parametrize(
    ("user_id", "price", "phone", "message"),
    (
        (1, 100, "", "Empty fields."),
        (1, -20, "0435345", "Price must be above 0."),
        (6, 200, "12312312", "User was not found."),
    ),
)
def test_invalid_make_teacher(
    admin, user, auth, requester, user_id, price, phone, message
):
    auth.login(admin.email, "test")
    resp = requester.post(
        "/user/make_teacher", json={"user_id": user_id, "price": price, "phone": phone}
    )
    assert resp.status_code == 400
    assert resp.json.get("message") == message


def test_make_student(admin, user, auth, requester):
    auth.login(admin.email, "test")
    resp = requester.get(f"/user/make_student?user_id={user.id}&teacher_id=1")
    assert resp.json["data"]["my_teacher"]["teacher_id"] == 1


def test_make_student_invalid_teacher(admin, user, auth, requester):
    auth.login(admin.email, "test")
    resp = requester.get(f"/user/make_student?user_id={user.id}&teacher_id=3")
    assert resp.status_code == 400
    assert resp.json.get("message") == "Teacher was not found."


def test_make_student_already_assigned(
    app, admin, student, teacher, auth, requester, db_instance
):
    with app.app_context():
        auth.login(admin.email, "test")
        resp = requester.get(
            f"/user/make_student?user_id={student.user_id}&teacher_id=1"
        )
        assert "already a student" in resp.json.get("message")
        resp = requester.get(
            f"/user/make_student?user_id={teacher.user_id}&teacher_id=1"
        )
        assert "already a student" in resp.json.get("message")


def test_register_token(auth, requester):
    auth.login()
    resp = requester.post("/user/register_firebase_token", json={"token": "some token"})
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
    info = user.get_user_info(teacher.user)
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

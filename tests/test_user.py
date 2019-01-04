from server.api.blueprints import user
import pytest


def test_make_teacher(user, admin, auth, requester):
    auth.login(admin.email, 'test')
    resp = requester.post('/user/make_teacher',
                          json={'user_id': user.id, 'price': 100,
                                'phone': '052222222'})
    assert resp.json.get("message") == "Teacher created successfully."


def test_not_admin_make_teacher(user, auth, requester):
    auth.login()
    resp = requester.post('/user/make_teacher',
                          json={'user_id': user.id, 'price': 100,
                                'phone': '052222222'})
    assert resp.json.get("message") == "Not authorized."


@pytest.mark.parametrize(
    ("user_id", "price", "phone", "message"),
    (
        (1, 100, "", "Empty fields."),
        (1, -20, "0435345", "Price must be above 0."),
        (6, 200, "12312312", "User not found."),
    ),
)
def test_invalid_make_teacher(admin, user, auth, requester, user_id, price, phone, message):
    auth.login(admin.email, 'test')
    resp = requester.post('/user/make_teacher',
                          json={'user_id': user_id, 'price': price,
                                'phone': phone})
    assert resp.json.get("message") == message


def test_make_student(admin, user, auth, requester):
    auth.login(admin.email, 'test')
    resp = requester.post('/user/make_student',
                          json={'user_id': user.id, 'teacher_id': 1})
    assert resp.json.get("message") == "Student created successfully."


def test_make_student_invalid_teacher(admin, user, auth, requester):
    auth.login(admin.email, 'test')
    resp = requester.post('/user/make_student',
                          json={'user_id': user.id, 'teacher_id': 3})
    assert resp.json.get("message") == "Teacher not found."


def test_make_student_already_assigned(app, admin, student, teacher, auth, requester, db_instance):
    with app.app_context():
        auth.login(admin.email, 'test')
        resp = requester.post('/user/make_student',
                              json={'user_id': student.user_id, 'teacher_id': 1})
        assert resp.json.get("message") == "Already student or teacher."
        resp = requester.post('/user/make_student',
                              json={'user_id': teacher.user_id, 'teacher_id': 1})
        assert resp.json.get("message") == "Already student or teacher."

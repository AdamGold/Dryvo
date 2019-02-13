from server.app import create_app


def test_config_app(app):
    """ Test that the test config
    is being written over the actual config"""
    assert app.config.get('SECRET_KEY') == "VERY_SECRET"
    assert app.config.get('SECRET_JWT') == "VERY_VERY_SECRET"
    assert app.config.get("FIREBASE_JSON")


def test_create_app():
    assert create_app()

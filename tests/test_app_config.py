def test_config_app(app):
    """ Test that the test config
    is being written over the actual config"""
    assert app.config.get('SECRET_KEY') == "VERY_SECRET"

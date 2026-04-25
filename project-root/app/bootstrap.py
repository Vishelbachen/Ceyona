# ONLY DI PLACEHOLDER (NO IMPORT SIDE EFFECTS)

def create_app():
    from app.main import create_app as _create
    return _create()
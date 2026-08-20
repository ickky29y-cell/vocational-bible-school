from pkg import app

app.testing = True
with app.app_context():
    client = app.test_client()
    client.post('/user/login/', data={'identity': 'sean', 'password': '123456'})
    for class_id in (2, 3):
        try:
            r = client.get(f'/teacher/assessment/?class_id={class_id}')
            print(class_id, r.status_code)
        except Exception as exc:
            print(class_id, type(exc).__name__, str(exc))
            raise

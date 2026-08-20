import re
import urllib.error
import urllib.request
import http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req = urllib.request.Request(
    'http://127.0.0.1:8080/user/login/',
    data=b'identity=sean&password=123456',
    method='POST',
)
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
try:
    resp = opener.open(req)
except urllib.error.HTTPError as exc:
    resp = exc
print('LOGIN', getattr(resp, 'status', None), resp.headers.get('Location'))

markers = [
    'Skill Acquisition',
    'Question Banks',
    'Exam Builder',
    'Test Exam',
    'Optional Skill Questions',
    'Optional Skill Bank',
    'Skill Acquisition (Optional)',
    'Live Monitor',
]
pages = {
    'DASH': '/teacher/dashboard/',
    'EXAMS': '/teacher/exams/',
    'SKILLS': '/teacher/skills/',
    'BANKS': '/teacher/question-banks/',
    'STUDENTS': '/teacher/students/',
}
for name, path in pages.items():
    try:
        html = opener.open('http://127.0.0.1:8080' + path).read().decode('utf-8', 'replace')
        status = 200
    except urllib.error.HTTPError as exc:
        html = exc.read().decode('utf-8', 'replace')
        status = exc.code
    found = [marker for marker in markers if marker in html]
    title = re.search(r'<title>(.*?)</title>', html, re.I | re.S)
    print(name, status, 'markers', found, 'title', title.group(1).strip() if title else None)

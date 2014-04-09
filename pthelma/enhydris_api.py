from StringIO import StringIO

import requests


def login(base_url, username, password):
    if not username:
        return {}
    if base_url[-1] != '/':
        base_url += '/'
    login_url = base_url + 'accounts/login/'
    r = requests.get(login_url)
    r.raise_for_status()
    r1 = requests.post(login_url,
                       headers={'X-CSRFToken': r.cookies['csrftoken'],
                                'Referer': login_url},
                       data='username={}&password={}'.format(username,
                                                             password),
                       cookies=r.cookies)
    r1.raise_for_status()
    result = r1.cookies
    return result


def post_tsdata(base_url, session_cookies, timeseries):
    if base_url[-1] != '/':
        base_url += '/'
    f = StringIO()
    timeseries.write(f)
    r = requests.post(
        base_url + 'api/tsdata/{}/'.format(timeseries.id),
        data={'timeseries_records': f.getvalue()},
        headers={'Content-type': 'application/x-www-form-urlencoded',
                 'X-CSRFToken': session_cookies['csrftoken']},
        cookies=session_cookies)
    r.raise_for_status()

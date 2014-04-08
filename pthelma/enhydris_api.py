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

from datetime import datetime
from six import StringIO

import iso8601
import requests


def urljoin(*args):
    result = '/'.join([s.strip('/') for s in args])
    if args[-1].endswith('/'):
        result += '/'
    return result


# My understanding from requests' documentation is that when I make a post
# request, it shouldn't be necessary to specify Content-Type:
# application/x-www-form-urlencoded, and that requests adds the header
# automatically. However, when running in Python 3, apparently requests does
# not add the header (although it does convert the post data to
# x-www-form-urlencoded format). This is why the header has been explicitly
# specified in all post requests.

def login(base_url, username, password):
    if not username:
        return {}
    login_url = urljoin(base_url, 'accounts/login/')
    r = requests.get(login_url)
    r.raise_for_status()
    r1 = requests.post(
        login_url,
        headers={'X-CSRFToken': r.cookies['csrftoken'],
                 'Referer': login_url,
                 'Content-Type': 'application/x-www-form-urlencoded'
                 # See comment about x-www-form-urlencoded above
                 },
        data='username={}&password={}'.format(username, password),
        cookies=r.cookies,
        allow_redirects=False)
    r1.raise_for_status()
    result = r1.cookies
    return result


def get_model(base_url, session_cookies, model, id):
    url = urljoin(base_url, 'api/{}/{}/'.format(model, id))
    r = requests.get(url, cookies=session_cookies)
    r.raise_for_status()
    return r.json()


def post_model(base_url, session_cookies, model, data):
    r = requests.post(
        urljoin(base_url, 'api/{}/'.format(model)),
        headers={'X-CSRFToken': session_cookies['csrftoken'],
                 'Content-Type': 'application/x-www-form-urlencoded'
                 # See comment about x-www-form-urlencoded above
                 },
        cookies=session_cookies,
        data=data
    )
    r.raise_for_status()
    return r.json()['id']


def delete_model(base_url, session_cookies, model, id):
    url = urljoin(base_url, 'api/{}/{}/'.format(model, id))
    r = requests.delete(url, cookies=session_cookies,
                        headers={'X-CSRFToken': session_cookies['csrftoken']})
    if r.status_code != 204:
        raise requests.exceptions.HTTPError()


def read_tsdata(base_url, session_cookies, ts):
    r = requests.get(base_url + 'api/tsdata/{0}/'.format(ts.id),
                     cookies=session_cookies)
    r.raise_for_status()
    ts.read(StringIO(r.text))


def post_tsdata(base_url, session_cookies, timeseries):
    f = StringIO()
    timeseries.write(f)
    url = urljoin(base_url, 'api/tsdata/{}/'.format(timeseries.id))
    r = requests.post(
        url,
        data={'timeseries_records': f.getvalue()},
        headers={'Content-type': 'application/x-www-form-urlencoded',
                 'X-CSRFToken': session_cookies['csrftoken']},
        cookies=session_cookies)
    r.raise_for_status()
    return r.text


def get_ts_end_date(base_url, session_cookies, ts_id):
    r = requests.get('{}timeseries/d/{}/bottom/'.format(base_url, ts_id),
                     cookies=session_cookies)
    r.raise_for_status()
    lines = r.text.splitlines()
    lines.reverse()
    for line in [x.strip() for x in lines]:
        if not line:
            continue
        datestring = line.split(',')[0]
        return iso8601.parse_date(datestring, default_timezone=None)
    return datetime(1, 1, 1)

#!/usr/bin/env python3
"""
today.py — Vedansh Madan's GitHub Stats Updater
Runs on a daily schedule via GitHub Actions to refresh stat fields in the SVGs.

Stats updated: age/uptime, repos, stars, commits, followers, lines of code.
SVG structure is preserved byte-for-byte except for the targeted tspan ids.

Credit: Stats pipeline approach adapted from Andrew6rant's profile
(https://github.com/Andrew6rant/Andrew6rant) — rewritten for my account.
"""

import datetime
import hashlib
import os
import time
from lxml import etree
from dateutil import relativedelta
import requests

# ── Auth & identity ──────────────────────────────────────────────────────────
HEADERS   = {'authorization': 'token ' + os.environ['ACCESS_TOKEN']}
USER_NAME = os.environ['USER_NAME']   # 'madanVedansh21'

# ── Birthday (for Uptime field) ───────────────────────────────────────────────
# Vedansh Madan — DOB: 21 May 2006
BIRTHDAY  = datetime.datetime(2006, 5, 21)

# ── Query tracking ────────────────────────────────────────────────────────────
QUERY_COUNT = {
    'user_getter': 0, 'follower_getter': 0,
    'graph_repos_stars': 0, 'recursive_loc': 0,
    'graph_commits': 0, 'loc_query': 0,
}

OWNER_ID = None   # set in __main__

# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def format_plural(unit: int) -> str:
    return 's' if unit != 1 else ''


def daily_readme(birthday: datetime.datetime) -> str:
    """Return human-readable age string, e.g. '20 years, 2 months, 5 days'."""
    diff = relativedelta.relativedelta(datetime.datetime.today(), birthday)
    birthday_suffix = ' 🎂' if (diff.months == 0 and diff.days == 0) else ''
    return '{} {}, {} {}, {} {}{}'.format(
        diff.years,  'year'  + format_plural(diff.years),
        diff.months, 'month' + format_plural(diff.months),
        diff.days,   'day'   + format_plural(diff.days),
        birthday_suffix
    )


def query_count(func_id: str):
    global QUERY_COUNT
    QUERY_COUNT[func_id] += 1


def perf_counter(func, *args):
    start = time.perf_counter()
    result = func(*args)
    return result, time.perf_counter() - start


def formatter(label: str, elapsed: float, result=None, width: int = 0):
    print(f'   {label:<20}', end='')
    if elapsed > 1:
        print(f'{"%.4f" % elapsed + " s":>12}')
    else:
        print(f'{"%.4f" % (elapsed * 1000) + " ms":>12}')
    if width and result is not None:
        return f"{'{:,}'.format(result):<{width}}"
    return result


# ─────────────────────────────────────────────────────────────────────────────
# GitHub GraphQL helpers
# ─────────────────────────────────────────────────────────────────────────────

def simple_request(func_name: str, query: str, variables: dict, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                'https://api.github.com/graphql',
                json={'query': query, 'variables': variables},
                headers=HEADERS,
                timeout=30
            )
            if resp.status_code == 200:
                return resp
            if resp.status_code in (502, 503, 504, 429) and attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise Exception(f'{func_name} failed: {resp.status_code} {resp.text}')
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise Exception(f'{func_name} network error: {e}')


def user_getter(username: str):
    query_count('user_getter')
    q = '''
    query($login: String!) {
        user(login: $login) { id createdAt }
    }'''
    resp = simple_request('user_getter', q, {'login': username})
    data = resp.json()['data']['user']
    return {'id': data['id']}, data['createdAt']


def follower_getter(username: str) -> int:
    query_count('follower_getter')
    q = '''
    query($login: String!) {
        user(login: $login) { followers { totalCount } }
    }'''
    resp = simple_request('follower_getter', q, {'login': username})
    return int(resp.json()['data']['user']['followers']['totalCount'])


def graph_repos_stars(count_type: str, owner_affiliation: list,
                      cursor=None) -> int:
    query_count('graph_repos_stars')
    q = '''
    query($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges { node { ... on Repository { nameWithOwner stargazers { totalCount } } } }
                pageInfo { endCursor hasNextPage }
            }
        }
    }'''
    resp = simple_request('graph_repos_stars', q,
                          {'owner_affiliation': owner_affiliation,
                           'login': USER_NAME, 'cursor': cursor})
    repos = resp.json()['data']['user']['repositories']
    if count_type == 'repos':
        return repos['totalCount']
    elif count_type == 'stars':
        return sum(e['node']['stargazers']['totalCount'] for e in repos['edges'])


# ── LOC pipeline (cache-based) ────────────────────────────────────────────────

def recursive_loc(owner, repo_name, data, cache_comment,
                  addition_total=0, deletion_total=0, my_commits=0, cursor=None, depth=0):
    query_count('recursive_loc')
    q = '''
    query($repo_name: String!, $owner: String!, $cursor: String) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 50, after: $cursor) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit { committedDate }
                                    author { user { id } }
                                    deletions additions
                                }
                            }
                            pageInfo { endCursor hasNextPage }
                        }
                    }
                }
            }
        }
    }'''
    resp = None
    for attempt in range(3):
        try:
            resp = requests.post(
                'https://api.github.com/graphql',
                json={'query': q, 'variables': {'repo_name': repo_name,
                                                 'owner': owner,
                                                 'cursor': cursor}},
                headers=HEADERS,
                timeout=30
            )
            if resp.status_code == 200:
                break
            if resp.status_code in (502, 503, 504, 429) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
        except requests.RequestException:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            break

    if resp is not None and resp.status_code == 200:
        data_json = resp.json()
        repo_data = data_json.get('data', {}).get('repository')
        if repo_data and repo_data.get('defaultBranchRef'):
            history = repo_data['defaultBranchRef']['target']['history']
            return _loc_counter(owner, repo_name, data, cache_comment,
                                history, addition_total, deletion_total, my_commits, depth=depth)
        return addition_total, deletion_total, my_commits

    status = resp.status_code if resp is not None else "timeout"
    print(f'[today.py] Warning: recursive_loc({owner}/{repo_name}) returned status {status}. Preserving current count.')
    _force_close(data, cache_comment)
    return addition_total, deletion_total, my_commits


def _loc_counter(owner, repo_name, data, cache_comment, history,
                 addition_total, deletion_total, my_commits, depth=0):
    for node in history['edges']:
        if node['node']['author']['user'] == OWNER_ID:
            my_commits    += 1
            addition_total += node['node']['additions']
            deletion_total += node['node']['deletions']
    if not history['edges'] or not history['pageInfo']['hasNextPage'] or depth >= 10:
        return addition_total, deletion_total, my_commits
    return recursive_loc(owner, repo_name, data, cache_comment,
                         addition_total, deletion_total, my_commits,
                         history['pageInfo']['endCursor'], depth=depth + 1)


def loc_query(owner_affiliation, comment_size=0, force_cache=False,
              cursor=None, edges=None):
    if edges is None:
        edges = []
    query_count('loc_query')
    q = '''
    query($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            defaultBranchRef {
                                target { ... on Commit { history { totalCount } } }
                            }
                        }
                    }
                }
                pageInfo { endCursor hasNextPage }
            }
        }
    }'''
    resp = simple_request('loc_query', q,
                          {'owner_affiliation': owner_affiliation,
                           'login': USER_NAME, 'cursor': cursor})
    page = resp.json()['data']['user']['repositories']
    if page['pageInfo']['hasNextPage']:
        edges += page['edges']
        return loc_query(owner_affiliation, comment_size, force_cache,
                         page['pageInfo']['endCursor'], edges)
    return _cache_builder(edges + page['edges'], comment_size, force_cache)


def _cache_builder(edges, comment_size, force_cache, loc_add=0, loc_del=0):
    cached   = True
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode()).hexdigest() + '.txt'
    try:
        with open(filename) as f:
            data = f.readlines()
    except FileNotFoundError:
        data = []
        if comment_size > 0:
            for _ in range(comment_size):
                data.append('This line is a comment block.\n')
        with open(filename, 'w') as f:
            f.writelines(data)

    if len(data) - comment_size != len(edges) or force_cache:
        cached = False
        _flush_cache(edges, filename, comment_size)
        with open(filename) as f:
            data = f.readlines()

    cache_comment = data[:comment_size]
    data = data[comment_size:]
    for i, edge in enumerate(edges):
        repo_hash, commit_count, *_ = data[i].split()
        if repo_hash == hashlib.sha256(
                edge['node']['nameWithOwner'].encode()).hexdigest():
            try:
                ref = edge['node']['defaultBranchRef']
                total = ref['target']['history']['totalCount'] if ref else 0
                if int(commit_count) != total:
                    owner, repo_name = edge['node']['nameWithOwner'].split('/')
                    loc = recursive_loc(owner, repo_name, data, cache_comment)
                    if isinstance(loc, (tuple, list)) and len(loc) >= 3:
                        data[i] = f"{repo_hash} {total} {loc[2]} {loc[0]} {loc[1]}\n"
                    else:
                        data[i] = f"{repo_hash} {total} 0 0 0\n"
            except Exception as e:
                print(f"[today.py] Warning: Error calculating LOC for {edge['node']['nameWithOwner']}: {e}")
                data[i] = f"{repo_hash} {commit_count} 0 0 0\n"

    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)

    for line in data:
        parts = line.split()
        loc_add += int(parts[3])
        loc_del += int(parts[4])
    return [loc_add, loc_del, loc_add - loc_del, cached]


def _flush_cache(edges, filename, comment_size):
    with open(filename) as f:
        data = f.readlines()[:comment_size] if comment_size > 0 else []
    with open(filename, 'w') as f:
        f.writelines(data)
        for node in edges:
            f.write(hashlib.sha256(
                node['node']['nameWithOwner'].encode()).hexdigest() + ' 0 0 0 0\n')


def _force_close(data, cache_comment):
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode()).hexdigest() + '.txt'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    print(f'[today.py] Emergency save to {filename}.')


def commit_counter(comment_size: int) -> int:
    filename = 'cache/' + hashlib.sha256(USER_NAME.encode()).hexdigest() + '.txt'
    try:
        with open(filename) as f:
            data = f.readlines()
    except FileNotFoundError:
        return 0
    data = data[comment_size:]
    total = 0
    for line in data:
        parts = line.split()
        if len(parts) >= 3 and parts[2].isdigit():
            total += int(parts[2])
    return total


# ─────────────────────────────────────────────────────────────────────────────
# SVG patching (lxml)
# ─────────────────────────────────────────────────────────────────────────────

def _find_by_id(root, el_id: str):
    matches = root.xpath(f"//*[@id='{el_id}']")
    if matches:
        return matches[0]
    return None


def _dots_string(length: int) -> str:
    if length <= 0:
        return ' '
    return ' ' + ('.' * length) + ' '


def svg_overwrite(filename: str, age_data, commit_data, star_data,
                  repo_data, contrib_data, follower_data, loc_data):
    """
    Parse an SVG, update stat tspan ids, write back.
    Preserves all styling, structure, and text content.
    """
    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
    tree   = etree.parse(filename, parser)
    root   = tree.getroot()

    def update(el_id, new_text, dot_length=0):
        el = _find_by_id(root, el_id)
        if el is not None:
            el.text = str(new_text)
        if dot_length:
            dots_el = _find_by_id(root, f"{el_id}_dots")
            if dots_el is not None:
                dots_el.text = _dots_string(max(0, dot_length - len(str(new_text))))

    # Format integers with commas
    def fmt(n):
        if isinstance(n, int):
            return f'{n:,}'
        return str(n)

    update('age_data',      age_data)
    update('commit_data',   fmt(commit_data), dot_length=18)
    update('star_data',     fmt(star_data),  dot_length=14)
    update('repo_data',     fmt(repo_data),  dot_length=6)
    update('contrib_data',  fmt(contrib_data))
    update('follower_data', fmt(follower_data), dot_length=10)
    update('loc_data',      fmt(loc_data[2]), dot_length=9)
    update('loc_add',       fmt(loc_data[0]))
    update('loc_del',       fmt(loc_data[1]), dot_length=7)

    tree.write(filename, encoding='utf-8', xml_declaration=True, pretty_print=False)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('[today.py] Fetching GitHub stats …')

    user_data, t = perf_counter(user_getter, USER_NAME)
    OWNER_ID, acc_date = user_data
    formatter('account data', t)

    age_str, t = perf_counter(daily_readme, BIRTHDAY)
    formatter('age calculation', t)

    # Use OWNER and COLLABORATOR to scan user's repositories quickly (seconds, not 18 minutes!)
    total_loc, t = perf_counter(loc_query, ['OWNER', 'COLLABORATOR'], 7)
    label = 'LOC (cached)' if total_loc[-1] else 'LOC (no cache)'
    formatter(label, t)

    commit_data, t = perf_counter(commit_counter, 7)
    formatter('commits', t)

    star_data,   t = perf_counter(graph_repos_stars, 'stars', ['OWNER'])
    formatter('stars', t)

    repo_data,   t = perf_counter(graph_repos_stars, 'repos', ['OWNER'])
    formatter('repos', t)

    contrib_data, t = perf_counter(graph_repos_stars, 'repos',
                                   ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'])
    formatter('contrib repos', t)

    follower_data, t = perf_counter(follower_getter, USER_NAME)
    formatter('followers', t)

    # Format LOC numbers
    loc_display = ['{:,}'.format(total_loc[i]) for i in range(3)]

    for svg_file in ('dark_mode.svg', 'light_mode.svg'):
        print(f'[today.py] Patching {svg_file} …')
        svg_overwrite(svg_file, age_str, commit_data, star_data, repo_data,
                      contrib_data, follower_data, loc_display)

    print('[today.py] Done ✓')
    print(f'[today.py] Total GraphQL calls: {sum(QUERY_COUNT.values())}')
    for fn, cnt in QUERY_COUNT.items():
        print(f'   {fn:<28} {cnt:>4}')

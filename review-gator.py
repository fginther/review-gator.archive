#!/usr/bin/env python

import datetime
import github
import os
import pytz
import sys
import yaml

from jinja2 import Environment, FileSystemLoader
import launchpadagent

MAX_DESCRIPTION_LENGTH = 80
NOW = pytz.utc.localize(datetime.datetime.utcnow())
ONE_DAY = datetime.timedelta(days=1)
ONE_HOUR = datetime.timedelta(hours=1)


class Repo(object):
    '''Base class for a source code repository.

    These are the github repository or launchpad branch  that a pull request
    will target. A repo contain 0 or more pull requests.'''

    def __init__(self, repo_type, handle, url, name):
        self.repo_type = repo_type
        self.handle = handle
        self.url = url
        self.name = name
        self.pull_requests = []

    def __repr__(self):
        return 'Repo[{}, {}, {}, {}]'.format(
            self.repo_type, self.name, self.url, self.pull_requests)

    @property
    def pull_request_count(self):
        return len(self.pull_requests)

    def add(self, pull_request):
        '''Add a pull request to this repository.'''
        self.pull_requests.append(pull_request)


class GithubRepo(Repo):
    '''A github repository.'''
    def __init__(self, handle, url, name):
        super(GithubRepo, self).__init__('github', handle, url, name)


class LaunchpadRepo(Repo):
    '''A launchpad repository (aka branch).'''
    def __init__(self, handle, url, name):
        super(LaunchpadRepo, self).__init__('launchpad', handle, url, name)


class PullRequest(object):
    '''Base class for a request to merge into a repository.

    Represents a github pull request or launchpad merge proposal.'''
    def __init__(self, pull_request_type, handle, url, title, owner, state,
                 date, review_count):
        self.pull_request_type = pull_request_type
        self.handle = handle
        self.url = url
        self.title = title
        self.owner = owner
        self.state = state
        self.date = date
        self.review_count = review_count
        self.reviews = []

    def __repr__(self):
        return u'PullRequest[{}, {}, {}, {}, {}]'.format(
            self.pull_request_type, self.title, self.owner, self.state,
            self.date)

    @property
    def age(self):
        #print(u'{}'.format(self))
        return date_to_age(self.date)

    def add_review(self, review):
        '''Adds a review, replacing any older review by the same owner.'''
        for r in self.reviews:
            if (review.owner == r['owner'] and review.date > r['date']):
                self.reviews.remove(r)
                break
        self.reviews.append(merge_two_dicts(review.__dict__,
                                            {'age': review.age}))


class GithubPullRequest(PullRequest):
    '''A github pull request.'''
    def __init__(self, handle, url, title, owner, state, date, review_count):
        date = pytz.utc.localize(date)
        super(GithubPullRequest, self).__init__(
            'github', handle, url, title, owner, state, date, review_count)


class LaunchpadPullRequest(PullRequest):
    '''A launchpad pull request (aka merte proposal).'''
    def __init__(self, handle, url, title, owner, state, date, review_count):
        super(LaunchpadPullRequest, self).__init__(
            'launchpad', handle, url, title, owner, state, date, review_count)


class Review(object):
    '''A completed or requested review attached to a pull request.'''
    def __init__(self, review_type, review, url, owner, state, date):
        self.review_type = review_type
        self.review = review
        self.url = url
        self.owner = owner
        self.state = state
        self.date = date

    def __repr__(self):
        return u'Review[{}, {}, {}, {}, {}]'.format(self.review_type,
            self.review, self.owner, self.state, self.date)

    @property
    def age(self):
        #print(u'{}'.format(self))
        return date_to_age(self.date)


class GithubReview(Review):
    '''A github pull request review.'''
    def __init__(self, handle, url, owner, state, date):
        date = pytz.utc.localize(date)
        super(GithubReview, self).__init__(
            'github', handle, url, owner, state, date)


class LaunchpadReview(Review):
    '''A launchpad merge proposal review.'''
    def __init__(self, handle, url, owner, state, date):
        super(LaunchpadReview, self).__init__(
            'launchpad', handle, url, owner, state, date)


def date_to_age(date):
    if date is None:
        return None
    if date == '':
        return None

    age = NOW - date
    if age > ONE_DAY:
        return '{} days'.format(age.days)
    if age > ONE_HOUR:
        return '{} hours'.format(age.seconds / 3600)
    return '{} minutes'.format(age.seconds / 60)


def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


def get_all_repos(gh, sources):
    '''Return all repos, prs and reviews for the given github sources.'''
    repos = []
    for org in sources:
        for name, data in sources[org].iteritems():
            repo = gh.get_repo('{}/{}'.format(org.replace(' ', '') , name))
            review_count = sources[org][name]['review-count']
            gr = GithubRepo(repo, repo.html_url, repo.ssh_url)
            get_prs(gr, repo, review_count)
            if gr.pull_request_count > 0:
                repos.append(gr)
            print(gr)
    return repos


def get_prs(gr, repo, review_count):
    '''Return all pull request for the given repository.'''
    pull_requests = []
    pulls = repo.get_pulls()
    for p in pulls:
        reviews = {}
        pr = GithubPullRequest(p, p.html_url, p.title, p.head.repo.owner.login,
                            p.state, p.created_at, review_count)
        gr.add(pr)
        pull_requests.append(pr)
        raw_reviews = p.get_reviews()
        index = 0
        for raw_review in raw_reviews:
            index += 1
            owner = raw_review.user.login
            review = GithubReview(raw_review, raw_review.html_url, owner,
                               raw_review.state, raw_review.submitted_at)
            pr.add_review(review)
    return pull_requests


def get_pr_data(pull_requests):
    '''Render the list of provided pull_requests.'''
    pr_data = []
    for p in pull_requests:
        pr_data.append(merge_two_dicts(p.__dict__, {'age': p.age}))
    return pr_data


def get_repo_data(repos):
    '''Render the list of repos, their prs and reviews into an html table.'''
    repo_data = {}
    for repo in repos:
        repo_data[repo.name] = {
            'repo_url': repo.url,
            'repo_name': repo.name,
            'repo_shortname': repo.name.split('/')[-1],
            'pull_requests': get_pr_data(repo.pull_requests)
        }
    return repo_data


def render(repos):
    '''Render the repositories into an html file.'''
    data = get_repo_data(repos)
    env = Environment(loader=FileSystemLoader('templates'))
    tmpl = env.get_template('reviews.html')
    with open('dist/reviews.html', 'w') as out_file:
        out_file.write(tmpl.render({'repos': data}).encode('utf-8'))


def get_mp_title(mp):
    '''Format a sensible MP title from git branches and the description.'''
    title = ''
    git_source = mp.source_git_path
    if git_source is not None:
        source = '<strong>'
        source += mp.source_git_repository_link.replace(
            'https://api.launchpad.net/devel/', '')
        source += ':' + git_source.replace('refs/heads/', '') + '</strong> &rArr; '
        title += source
    else:
        source = '<strong>'
        source += mp.source_branch_link.replace(
            'https://api.launchpad.net/devel/', '')
        source += '</strong> &rArr; '
        title += source
    git_target = mp.target_git_path
    if git_target is not None:
        target = mp.target_git_repository_link.replace(
            'https://api.launchpad.net/devel/', '')
        target += ':' + git_target.replace('refs/heads/', '')
        title += target
    else:
        target = mp.source_branch_link.replace(
            'https://api.launchpad.net/devel/', '')
        title += target

    description = mp.description
    if description is not None:
        description = description.split('\n')[0]
        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:MAX_DESCRIPTION_LENGTH] + '...'
        if len(title) > 0:
            title += '\n'
        title += description
    return title


def get_candidate_mps(branch):
    try:
        mps = branch.getMergeProposals(status='Needs review')
    except AttributeError:
        mps = branch.landing_candidates
    return mps


def get_mps(repo, branch):
    '''Return all merge proposals for the given branch.'''
    mps = get_candidate_mps(branch)
    for mp in mps:
        _, owner = mp.registrant_link.split('~')
        title = get_mp_title(mp)

        pr = LaunchpadPullRequest(mp, mp.web_link, title, owner,
                                  mp.queue_status,
                                  mp.date_created, 2)
        repo.add(pr)
        for vote in mp.votes:
            owner = vote.reviewer.display_name
            comment = vote.comment
            result = 'EMPTY'
            review_date = ''
            if comment is not None:
                result = vote.comment.vote
                review_date = vote.date_created
            review = LaunchpadReview(vote, vote.web_link, owner, result,
                                     review_date)
            pr.add_review(review)


def get_branches_for_owner(lp, collected, owner, max_age):
    '''Return all repos and prs for the given owner with the age limit.

    This is used to identify any recently submitted prs that escaped the
    whitelist of launchpad repositories. This only applies to launchpad.'''
    age_gate = NOW - datetime.timedelta(days=max_age)
    owner = owner.decode('utf-8')
    team = lp.people(owner)
    branches = team.getBranches(modified_since=age_gate)
    repos = []
    for b in branches:
        # XXX: Add logic to skip branches we already have
        if b.display_name in collected:
            continue
        branch = LaunchpadRepo(b, b.web_link, b.display_name)
        get_mps(branch, b)
        if branch.pull_request_count > 0:
            repos.append(branch)
    return repos


def get_branches(sources):
    '''Return all repos, prs and reviews for the given launchpad sources.'''
    launchpad_cachedir = os.path.join('/tmp/get_reviews/.launchpadlib')
    lp = launchpadagent.get_launchpad(launchpadlib_dir=launchpad_cachedir)
    repos = []
    for source, data in sources['branches'].iteritems():
        print(source, data)
        b = lp.branches.getByUrl(url=source)
        repo = LaunchpadRepo(b, b.web_link, b.display_name)
        get_mps(repo, b)
        if repo.pull_request_count > 0:
            repos.append(repo)
        print(repo)
    collected = [r.name for r in repos]
    print('collected: {}'.format(collected))
    for owner, data in sources['owners'].iteritems():
        print(owner, data)
        repos.extend(get_branches_for_owner(
            lp, collected, owner, data['max-age']))
    return repos


def get_lp_repos(sources):
    '''Return all repos, prs and reviews for the given lp-git source.'''
    launchpad_cachedir = os.path.join('/tmp/get_reviews/.launchpadlib')
    lp = launchpadagent.get_launchpad(launchpadlib_dir=launchpad_cachedir)
    repos = []
    for source, data in sources['repos'].iteritems():
        print(source, data)
        b = lp.git_repositories.getByPath(path=source.replace('lp:', ''))
        repo = LaunchpadRepo(b, b.web_link, b.display_name)
        get_mps(repo, b)
        if repo.pull_request_count > 0:
            repos.append(repo)
        print(repo)
    return repos


def get_repos(sources):
    # XXX: Generate a warning if no user and password are found
    gh = github.Github(os.environ.get('GITHUB_USER'),
                       os.environ.get('GITHUB_PASSWORD'))
    repos = get_all_repos(gh, sources['repos'])
    return repos


def get_source_info(source):
    '''Load the sources file.'''
    with open(source) as infile:
        data = yaml.safe_load(infile.read())
    return data


def main():
    '''Start here.'''
    # XXX: Use argparse instead of raw sys.argv
    sources = get_source_info(sys.argv[1])
    repos = []
    if 'lp-git' in sources:
        repos.extend(get_lp_repos(sources['lp-git']))
    if 'launchpad' in sources:
        repos.extend(get_branches(sources['launchpad']))
    if 'github' in sources:
        repos.extend(get_repos(sources['github']))
    render(repos)


if __name__ == '__main__':
    sys.exit(main())

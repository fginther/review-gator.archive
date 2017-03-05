#!/usr/bin/env python

#from __future__ import unicode_literals
import datetime
import github
import os
import pytz
import sys
import yaml
from collections import namedtuple

import launchpadagent

REPO_SPAN = 5
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
        print(u'{}'.format(self))
        return date_to_age(self.date)

    def add_review(self, review):
        '''Adds a review, replacing any older review by the same owner.'''
        for r in self.reviews:
            if (review.owner == r.owner and review.date > r.date):
                self.reviews.remove(r)
                break
        self.reviews.append(review)

    def html(self):
        '''Return a table row for each PullRequest.'''
        title = '<a href="{}">{}</a>'.format(
            self.url, self.title)
        fields = [title, self.owner, self.state, self.age]
        text = u'<table>\n  {}\n</table>\n'
        inner = u'<tr>\n'
        inner += u'\n'.join([u'    <td>{}</td>'.format(field)
                           for field in fields])
        reviews = [r.html() for r in self.reviews]
        for count in range(len(reviews), self.review_count):
            reviews.append(u'      <table><tr><td>EMPTY</td></tr></table>\n')
        review_list = [u'<tr><td>{}</td></tr>\n'.format(r) for r in reviews]
        table = u'\n'.join([u'    {}'.format(r)
                   for r in review_list])
        inner += u'\n    <td><table border=1>\n  <tr>{}\n </tr>\n</table></td>\n'.format(table)
        inner += u'</tr>'
        return inner


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
        print(u'{}'.format(self))
        return date_to_age(self.date)

    def html(self):
        '''Represent the review as an html table.'''
        # XXX: Might be better to return a table row instead
        state = u'<a href="{}">{}</a>'.format(self.url, self.state)
        text = u'<table>\n  <tr>{}  </tr>\n</table>\n'
        inner = u'\n'.join([u'    <td>{}</td>'.format(field)
                           for field in [self.owner, state, self.age]])
        return text.format(inner)


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
    print('NOW: {}'.format(NOW))
    print('date: {}'.format(date))
    age = NOW - date
    if age > ONE_DAY:
        return '{} days'.format(age.days)
    if age > ONE_HOUR:
        return '{} hours'.format(age.minutes / 60)
    return '{} minutes'.format(age.minutes)

def get_all_repos(gh, sources):
    '''Return all repos, prs and reviews for the given github sources.'''
    repos = []
    for org in sources:
        for name, data in sources[org].iteritems():
            repo = gh.get_repo('{}/{}'.format(org.replace(' ', '') , name))
            review_count = sources[org][name]['review-count']
            gr = GithubRepo(repo, repo.html_url, repo.ssh_url)
            get_prs(gr, repo, review_count)
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


def get_pr_table(pull_requests):
    '''Render the list of provided pull_requests.'''
    return '\n'.join([p.html() for p in pull_requests])


def render_repo_table(repos):
    '''Render the list of repos, their prs and reviews into an html table.'''
    text = '<table border=1 cellpadding=4>'
    for repo in repos:
        text += '  <tr><td colspan={}><b><a href="{}">{}</a></b></td></tr>'.format(
            REPO_SPAN, repo.url, repo.name)
        text += get_pr_table(repo.pull_requests)
    text += '</table>'
    return text

def render(repos):
    '''Render the repositories into an html file.'''
    data = render_repo_table(repos)
    # XXX: Make the output configurable
    with open('reviews.html', 'w') as out_file:
        text = u'<head>\n</head>\n<body>\n{}\n</body>\n'.format(data)
        out_file.write(text.encode('utf-8'))


def get_mps(repo, branch):
    '''Return all merge proposals for the given branch.'''
    mps = branch.getMergeProposals(status='Needs review')
    for mp in mps:
        _, owner = mp.registrant_link.split('~')
        title = mp.description.split('\n')[0]
        pr = LaunchpadPullRequest(mp, mp.web_link, title, owner,
                                  mp.queue_status,
                                  mp.date_created, 2)
        repo.add(pr)
        for vote in mp.votes:
            owner = vote.reviewer.display_name
            comment = vote.comment
            result = 'EMPTY'
            if comment is not None:
                result = vote.comment.vote
            review = LaunchpadReview(vote, vote.web_link, owner, result, None)
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
        branch = LaunchpadRepo(b, b.owner, b.display_name)
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
        repo = LaunchpadRepo(b, b.owner, b.display_name)
        get_mps(repo, b)
        repos.append(repo)
        print(repo)
    collected = [r.name for r in repos]
    print('collected: {}'.format(collected))
    for owner, data in sources['owners'].iteritems():
        print(owner, data)
        repos.extend(get_branches_for_owner(
            lp, collected, owner, data['max-age']))
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
    repos = get_branches(sources['launchpad'])
    repos.extend(get_repos(sources['github']))
    render(repos)


if __name__ == '__main__':
    sys.exit(main())

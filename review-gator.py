#!/usr/bin/env python

#from __future__ import unicode_literals
import datetime
import github
import os
import sys
import yaml
from collections import namedtuple

import launchpadagent

REPO_SPAN = 5

class Repo(object):
    '''Base class for launchapd branches and git repositories.

    These are the source entities that a merge proposal or pull request will
    target. A repo contain 0 or more pull requests.'''

    def __init__(self, repo_type, handle, url, name):
        self.repo_type = repo_type
        self.handle = handle
        self.url = url
        self.name = name
        self.pull_requests = []

    def __repr__(self):
        return 'Repo[{}, {}, {}, {}]'.format(
            self.repo_type, self.name, self.url, self.pull_requests)

    def add(self, pull_request):
        '''Add a pull request to this repository.'''
        self.pull_requests.append(pull_request)


class GitRepo(Repo):
    def __init__(self, handle, url, name):
        super(GitRepo, self).__init__('github', handle, url, name)


class LaunchpadRepo(Repo):
    def __init__(self, handle, url, name):
        super(LaunchpadRepo, self).__init__('launchpad', handle, url, name)


class PullRequest(object):
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
        return 'PullRequest[{}, {}, {}, {}, {}]'.format(
            self.pull_request_type, self.title, self.owner, self.state,
            self.date)

    def html(self):
        '''Return a table row for each review.'''
        title = '<a href="{}">{}</a>'.format(
            self.url, self.title)
        fields = [title, self.owner, self.state, self.date]
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

    def add_review(self, review):
        '''Adds a review, replacing the any older review by the same owner.'''
        for r in self.reviews:
            if (review.owner == r.owner and review.date > r.date):
                self.reviews.remove(r)
                break
        self.reviews.append(review)


class GitPullRequest(PullRequest):
    def __init__(self, handle, url, title, owner, state, date, review_count):
        super(GitPullRequest, self).__init__(
            'github', handle, url, title, owner, state, date, review_count)


class LaunchpadPullRequest(PullRequest):
    def __init__(self, handle, url, title, owner, state, date, review_count):
        super(LaunchpadPullRequest, self).__init__(
            'launchpad', handle, url, title, owner, state, date, review_count)


class Review(object):
#GitReview = namedtuple('GitReview', ['review', 'owner', 'state', 'date'])
    def __init__(self, review_type, review, url, owner, state, date):
        self.review_type = review_type
        self.review = review
        self.url = url
        self.owner = owner
        self.state = state
        self.date = date

    def __repr__(self):
        return 'Review[{}, {}, {}, {}, {}]'.format(self.review_type,
            self.review, self.owner, self.state, self.date)

    def html(self):
        state = u'<a href="{}">{}</a>'.format(self.url, self.state)
        text = u'<table>\n  <tr>{}  </tr>\n</table>\n'
        inner = u'\n'.join([u'    <td>{}</td>'.format(field)
                           for field in [self.owner, state, self.date]])
        return text.format(inner)

        #return '{}:{}:{}'.format(self.owner, self.state, self.date)


class GitReview(Review):
    def __init__(self, handle, url, owner, state, date):
        super(GitReview, self).__init__(
            'github', handle, url, owner, state, date)


class LaunchpadReview(Review):
    def __init__(self, handle, url, owner, state, date):
        super(LaunchpadReview, self).__init__(
            'launchpad', handle, url, owner, state, date)


def render_template(template_filename, context):
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)


def get_all_repos(gh, sources):
    print(sources)
    repos = []
    for org in sources:
        print(org)
        print(sources[org])
        for name, data in sources[org].iteritems():
            print(name)
            print(data)
            repo = gh.get_repo('{}/{}'.format(org.replace(' ', '') , name))
            review_count = sources[org][name]['review-count']
            #print('{}:{}'.format(repo.owner.name, repo.name))
            #print(dir(repo))
            gr = GitRepo(repo, repo.html_url, repo.ssh_url)
            get_prs(gr, repo, review_count)
            print(gr)
            repos.append(gr)
    return repos


def get_all_repos_old(g):
    for org in g.get_user().get_orgs():
        #print(org.name)
        for repo_name in REPOS[org.name]:
            repo = org.get_repo(repo_name)
            #print('{}:{}'.format(repo.owner.name, repo.name))
    #print(dir(repo))
    return None
    #for repo in org.get_repos():
        #print('    {}'.format(repo.name))

    # Then play with your Github objects:
    #for repo in g.get_user().get_repos():
        #print(repo.name)


def get_prs(gr, repo, review_count):
    pull_requests = []
    #print('{}:{}'.format(repo.owner.name, repo.name))
    pulls = repo.get_pulls()
    for p in pulls:
        reviews = {}
        pr = GitPullRequest(p, p.html_url, p.title, p.head.repo.owner.login,
                            p.state, p.created_at, review_count)
        gr.add(pr)
        pull_requests.append(pr)
        #print('    {}:{}'.format(p.title, p.state))
        #print('        {}'.format(p.review_comments))
        #reviews = p.get_review_comments()
        #import pdb
        #pdb.set_trace()
        #print(p.get_review_request(1))
        raw_reviews = p.get_reviews()
        index = 0
        for raw_review in raw_reviews:
            index += 1
            owner = raw_review.user.login
            #print('       {}:{}:{}'.format(owner,
            #                               raw_review.state,
            #                               raw_review.submitted_at))
            review = GitReview(raw_review, raw_review.html_url, owner,
                               raw_review.state, raw_review.submitted_at)
            pr.add_review(review)
        #print(pr)
        #print(reviews)
    #for r in reviews:
    #    print('        {}:{}'.format(r.user.name, r.body))
    return pull_requests


def get_review(reviews):
    return ','.join([reviews[r].html() for r in reviews])
    text = ''
    for _, review in reviews.iteritems():
        #print(review)
        text += '{}:{},'.format(review.owner, review.state)
    return text


def get_pr_table(pull_requests):
    return '\n'.join([p.html() for p in pull_requests])
    if pull_request is None:
        return ''
    text = '<table>\n'
    for pr in pull_request:
        print('pull-request: {}'.format(pr))
        text += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(
            pr.title, pr.owner, pr.state, get_review(pr.reviews))
    text += '</table>\n'
    return text


def render_repo_table(repos):
    text = '<table border=1 cellpadding=4>'
    for repo in repos:
        text += '  <tr><td colspan={}><b><a href="{}">{}</a></b></td></tr>'.format(
            REPO_SPAN, repo.url, repo.name)
        text += get_pr_table(repo.pull_requests)
    text += '</table>'
    return text

def render(repos):
    data = render_repo_table(repos)
    with open('reviews.html', 'w') as out_file:
        text = u'<head>\n</head>\n<body>\n{}\n</body>\n'.format(data)
        out_file.write(text.encode('utf-8'))


def get_mps(repo, branch):
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


def get_branches_for_owner(lp, owner):
    age_gate = datetime.datetime.strptime('Feb 1 2017  12:01AM', '%b %d %Y %I:%M%p')
    owner = owner.decode('utf-8')
    team = lp.people(owner)
    branches = team.getBranches(modified_since=age_gate)
    repos = []
    for b in branches:
        branch = LaunchpadRepo(b, b.owner, b.display_name)
        get_mps(branch, b)
        repos.append(branch)
    return repos


def render_branches(branches):
    pass


def get_branches(sources):
    launchpad_cachedir = os.path.join('/tmp/get_reviews/.launchpadlib')
    lp = launchpadagent.get_launchpad(launchpadlib_dir=launchpad_cachedir)
    repos = []
    for source, data in sources['branches'].iteritems():
        print(source)
        print(data)
        b = lp.branches.getByUrl(url=source)
        repo = LaunchpadRepo(b, b.owner, b.display_name)
        get_mps(repo, b)
        repos.append(repo)
        print(repo)
    #for owner in sources['owners']:
    #    branches.extend(get_branches_for_owner(lp, owner))
    #render_branches(branches)
    return repos


def get_repos(sources):
    # First create a Github instance:
    # XXX: Generate a warning if no user and password are found
    gh = github.Github(os.environ.get('GITHUB_USER'),
                       os.environ.get('GITHUB_PASSWORD'))
    repos = get_all_repos(gh, sources['repos'])
    return repos


def get_source_info(source):
    with open(source) as infile:
        data = yaml.safe_load(infile.read())
    return data


def main():
    sources = get_source_info(sys.argv[1])
    repos = get_branches(sources['launchpad'])
    repos.extend(get_repos(sources['github']))
    render(repos)

if __name__ == '__main__':
    sys.exit(main())

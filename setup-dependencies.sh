#!/bin/bash
set -e

# XXX: Turn this into proper requirements.txt with a virtualenv

# Fetch a fork of PyGithub with supported added for PullRequestReviews.
git clone -b add-reviews https://github.com/fginther/PyGithub.git
ln -s PyGithub/github github

# Fetch the PyGithub dependencies
git clone https://github.com/mpdavis/python-jose.git
ln -s python-jose/jose jose

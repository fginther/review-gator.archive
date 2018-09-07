Review Gator
=============

Review gator is an aggregate view of code reviews a team has to do.

It pulls github and launchpad for open review slots and generates a static HTML
review queue, that can be hosted anywhere.

Installation
------------

The following steps should leave you with a working script:

```
virtualenv -p python3  .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
GITHUB_TOKEN=... review-gator --config branches.yaml
```

import os
import sys
import time
from launchpadlib.credentials import RequestTokenAuthorizationEngine
from lazr.restfulclient.errors import HTTPError
from launchpadlib.launchpad import Launchpad
from launchpadlib.credentials import UnencryptedFileCredentialStore

ACCESS_TOKEN_POLL_TIME = 1
WAITING_FOR_USER = """Open this link:
{}
to authorize this program to access Launchpad on your behalf.
Waiting to hear from Launchpad about your decision. . . ."""


class AuthorizeRequestTokenWithConsole(RequestTokenAuthorizationEngine):
    """Authorize a token in a server environment (with no browser).

    Print a link for the user to copy-and-paste into his/her browser
    for authentication.
    """

    def __init__(self, *args, **kwargs):
        # as implemented in AuthorizeRequestTokenWithBrowser
        kwargs['consumer_name'] = None
        kwargs.pop('allow_access_levels', None)
        super(AuthorizeRequestTokenWithConsole, self).__init__(*args, **kwargs)

    def make_end_user_authorize_token(self, credentials, request_token):
        """Ask the end-user to authorize the token in their browser.

        """
        authorization_url = self.authorization_url(request_token)
        print(WAITING_FOR_USER.format(authorization_url))
        # if we don't flush we may not see the message
        sys.stdout.flush()
        while credentials.access_token is None:
            time.sleep(ACCESS_TOKEN_POLL_TIME)
            try:
                credentials.exchange_request_token_for_access_token(
                    self.web_root)
                break
            except HTTPError as e:
                if e.response.status == 403:
                    # The user decided not to authorize this
                    # application.
                    raise e
                elif e.response.status == 401:
                    # The user has not made a decision yet.
                    pass
                else:
                    # There was an error accessing the server.
                    raise e


def get_launchpad(launchpadlib_dir=None):
    """ return a launchpad API class. In case launchpadlib_dir is
    specified used that directory to store launchpadlib cache instead of
    the default """
    creds_prefix = os.environ.get('SNAP_USER_COMMON', os.path.expanduser('~'))
    store = UnencryptedFileCredentialStore(
            os.path.join(creds_prefix, '.launchpad.credentials'))
    lp_app = 'review-gator'
    lp_env = 'production'
    lp_version = 'devel'

    authorization_engine = AuthorizeRequestTokenWithConsole(lp_env, lp_app)
    return Launchpad.login_with(lp_app, lp_env,
                                credential_store=store,
                                authorization_engine=authorization_engine,
                                launchpadlib_dir=launchpadlib_dir,
                                version=lp_version)

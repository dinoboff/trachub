"""
Created on 12 Mar 2009

@author: damien
"""

from datetime import datetime
from trac_hub.ticket import GitHubTicketUpdater
from trac.ticket.model import Ticket
import unittest

from trac.util.datefmt import to_timestamp, utc
from trac.test import EnvironmentStub
from trac.db.api import DatabaseManager
from nose.tools import ok_, eq_, raises

from trac_hub.install import TracHubSetup
from trac_hub.model import GitHubCommit

GIT_URL = 'http://github.com/dinoboff/trachub/'
COMMITS = [
    {
        'author': {'email': 'dinoboff@hotmail.com', 'name': 'Damien Lebrun'},
        'url': 'http://github.com/dinoclone1/trachub/commit/41a212ee83ca127e3c8cf465891ab7216a705f59',
        'timestamp': '2008-02-15T14:57:17-08:00',
        'message': 'Fixed issue 1',
        'id': '41a212ee83ca127e3c8cf465891ab7216a705f59'
        },
    {
        'author': {'email': 'dinoboff@hotmail.com', 'name': 'Damien Lebrun'},
        'url': 'http://github.com/dinoclone2/trachub/commit/41a212ee83ca127e3c8cf465891ab7216a705f59',
        'timestamp': '2008-02-15T14:57:17-08:00',
        'message': 'Fixed issue 1',
        'id': '41a212ee83ca127e3c8cf465891ab7216a705f59'
        },
    {
        'author': {'email': 'dinoboff@hotmail.com', 'name': 'Damien Lebrun'},
        'url': 'http://github.com/dinoboff/trachub/commit/41a212ee83ca127e3c8cf465891ab7216a705f59',
        'timestamp': '2008-02-15T14:57:17-08:00',
        'message': 'Fixed issue 1',
        'id': '41a212ee83ca127e3c8cf465891ab7216a705f59'
        },]

class Test(unittest.TestCase):

    def setUp(self):
        # setup environment
        self.env = EnvironmentStub(
            default_data=True,
            enable=['trac.*'])
        self.env.config.set('trachub', 'github_url', GIT_URL)
        DatabaseManager(self.env.compmgr)
        
        #install database
        setup = TracHubSetup(self.env.compmgr)
        setup.upgrade_environment(self.env.get_db_cnx())
        
        tkt = Ticket(self.env)
        tkt['reporter'] = 'me'
        tkt['summary'] = 'my new ticket'
        tkt['description'] = 'some bogus description'
        tkt['status'] = 'new'
        tkt.insert()
        
        self.now = to_timestamp(datetime.now(utc))
        self.ticker_updater = GitHubTicketUpdater(self.env.compmgr)
        
        
        
    def test_process_commit(self):
        commits = []
        time = self.now
        for data in COMMITS:
            c = GitHubCommit(self.env, git_url=GIT_URL, **data)
            c.time = time
            c.save()
            commits.append(c)
            time = time + 60
        
        # parse commit for the first time (with a clone)
        self.ticker_updater.process_commit(commits[0])
        tkt1 = Ticket(self.env, 1)
        change_log = tkt1.get_changelog()
        eq_(1, len(change_log))
        eq_('Damien Lebrun <dinoboff@hotmail.com>', change_log[0][1])
        eq_(
            'Commit %(id)s:\n\n%(message)s\n\nSource: [%(url)s]' % COMMITS[0],
            change_log[0][4])
        
        # parse same commit (still clone),
        # should not update the ticket
        self.ticker_updater.process_commit(commits[1])
        tkt1 = Ticket(self.env, 1)
        change_log = tkt1.get_changelog()
        eq_(1, len(change_log))
        
        # parse the commit from the main git repository
        # Should update the repository
        self.ticker_updater.process_commit(commits[2])
        tkt1 = Ticket(self.env, 1)
        change_log = tkt1.get_changelog()
        eq_(3, len(change_log))
        eq_('Damien Lebrun <dinoboff@hotmail.com>', change_log[1][1])
        eq_(
            'Commit %(id)s:\n\n%(message)s\n\nSource: [%(url)s]' % COMMITS[2],
            change_log[1][4])
        eq_('Damien Lebrun <dinoboff@hotmail.com>', change_log[2][1])
        eq_('resolution',change_log[2][2])
        eq_('fixed',change_log[2][4])
            
"""
Created on 10 Mar 2009

@author: damien
"""

import unittest

from trac.core import Component, implements
from trac.test import EnvironmentStub, Mock
from trac.db.api import DatabaseManager
from nose.tools import ok_, eq_

from trac_hub.install import TracHubSetup
from trac_hub.test.test_model import GIT_URL, JSON_COMMITS, COMMITS
from trac_hub.post_parser import GitHubPostParser, IGitHubPostObserver


class MockResponse(object):
    
    def __init__(self):
        self.called = False
        
    def __call__(self, msg, content_type='text/plain', status=200):
        self.called = True
        self.msg = msg
        self.content_type = content_type
        self.status = status
        

class MockObserver(Component):
    implements(IGitHubPostObserver)
    
    def __init__(self):
        self.commits = []
    
    def process_commit(self,commit):
        self.commits.append(commit)


class Test(unittest.TestCase):


    def setUp(self):
        self.env = EnvironmentStub(
            default_data=True,
            enable=['trac.*', 'trac_hub.test.test_post_parser.MockObserver'])
        self.env.config.set('trachub', 'github_url', GIT_URL)
        DatabaseManager(self.env.compmgr)
        setup = TracHubSetup(self.env.compmgr)
        setup.upgrade_environment(self.env.get_db_cnx())
        self.mock_observer = MockObserver(self.env.compmgr) 
        self.response = {}
        self.req = Mock(path_info='/github', method='POST', form_token='foo', args={}, send=MockResponse())
        self.mock_observer = MockObserver(self.env.compmgr) 
        self.parser = GitHubPostParser(self.env.compmgr)

    def tearDown(self):
        pass

    def test_match_request(self):
        ok_(self.parser.match_request(self.req))
        eq_(None, self.req.form_token)
        
    def test_no_match_request(self):
        self.req.path_info = '/'
        ok_(not self.parser.match_request(self.req))
        eq_('foo', self.req.form_token)
        
    def test_process_request(self):        
        self.req.args['payload'] = JSON_COMMITS
        self.parser.process_request(self.req)
        ok_(self.req.send.called)
        eq_(200, self.req.send.status)
        eq_(2, len(self.mock_observer.commits))
        eq_(COMMITS[0]['url'],
            self.mock_observer.commits[0].url)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
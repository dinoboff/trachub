"""
Created on 10 Mar 2009

@author: damien
"""
from trac.db.api import DatabaseManager
import unittest

from trac.test import EnvironmentStub
from nose.tools import eq_, ok_

from trac_hub.model import GitHubCommit
from trac_hub.install import TracHubSetup

GIT_URL = 'http://github.com/defunkt/github/'
COMMITS = [
    {
        'added': ['filepath.rb'],
        'author': {'email': 'chris@ozmm.org', 'name': 'Chris Wanstrath'},
        'url': 'http://github.com/defunkt/github/commit/41a212ee83ca127e3c8cf465891ab7216a705f59',
        'timestamp': '2008-02-15T14:57:17-08:00',
        'message': 'okay i give in',
        'id': '41a212ee83ca127e3c8cf465891ab7216a705f59'
        },
    {
        'url': 'http://github.com/defunkt/github/commit/de8251ff97ee194a289832576287d6f8ad74e3d0',
        'timestamp': '2008-02-15T14:36:34-08:00',
        'message': 'update pricing a tad',
        'id': 'de8251ff97ee194a289832576287d6f8ad74e3d0',
        'author': {'email': 'chris@ozmm.org', 'name': 'Chris Wanstrath'}
        }]

class Test(unittest.TestCase):


    def setUp(self):
        self.env = EnvironmentStub(default_data=True)
        DatabaseManager(self.env.compmgr)
        setup = TracHubSetup(self.env.compmgr)
        setup.upgrade_environment(self.env.get_db_cnx())

    def tearDown(self):
        pass
    
    def _create_commit(self, data=None, git_url=GIT_URL):
        if data is None:
            data = COMMITS[0]
        return GitHubCommit(self.env, git_url=git_url, **data), data

    def test_init(self):
        commit, data = self._create_commit()
        eq_(GIT_URL, commit.git_url)
        eq_(self.env, commit.env)
        eq_(data['id'], commit.id)
        eq_(data['url'], commit.url)
        eq_(data['message'], commit.message)
        eq_(None, commit.time)
        eq_(data['author']['name'], commit.name)
        eq_(data['author']['email'], commit.email)
        
    def test_is_clone(self):
        commit = self._create_commit()[0]
        ok_(not commit.is_clone())
        
        commit = self._create_commit(git_url='http://github.com/dinoboff/github/')[0]
        ok_(commit.is_clone())
        
        data = COMMITS[0]
        commit = GitHubCommit(self.env, **data)
        ok_(commit.is_clone())
        
    def test_author(self):
        commit = self._create_commit()[0]
        eq_('Chris Wanstrath <chris@ozmm.org>', commit.author)
        
    def test_save(self):
        commit, data = self._create_commit()
        commit.save()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        sql = """SELECT id, url, time, name, email, message
        FROM github_revisions WHERE url=%s"""
        cursor.execute(sql, (data['url'],))
        
        try:
            id, url, time, name, email, message = [x for x in cursor][0]
            eq_(data['id'], id)
            eq_(data['url'], url)
            eq_(data['message'], message)
            eq_(data['author']['name'], name)
            eq_(data['author']['email'], email)
            eq_(commit.time, time)
        except IndexError:
            assert False, 'No record saved'
            
    def test_get_commit_by_date(self):
        pass
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
"""
Created on 10 Mar 2009

@author: damien
"""
from trac.db.api import DatabaseManager
from datetime import datetime
from trac.util.datefmt import to_timestamp, utc
import simplejson
import unittest

from trac.test import EnvironmentStub
from nose.tools import eq_, ok_, raises

from trac_hub.model import GitHubCommit
from trac_hub.install import TracHubSetup

GIT_URL = 'http://github.com/defunkt/github/'

JSON_COMMITS = """{ 
  "before": "5aef35982fb2d34e9d9d4502f6ede1072793222d",
  "repository": {
    "url": "http://github.com/defunkt/github",
    "name": "github",
    "description": "You're lookin' at it.",
    "watchers": 5,
    "forks": 2,
    "private": 1,
    "owner": {
      "email": "chris@ozmm.org",
      "name": "defunkt" 
    }
  },
  "commits": [
    {
      "id": "41a212ee83ca127e3c8cf465891ab7216a705f59",
      "url": "http://github.com/defunkt/github/commit/41a212ee83ca127e3c8cf465891ab7216a705f59",
      "author": {
        "email": "chris@ozmm.org",
        "name": "Chris Wanstrath" 
      },
      "message": "okay i give in",
      "timestamp": "2008-02-15T14:57:17-08:00",
      "added": ["filepath.rb"]
    },
    {
      "id": "de8251ff97ee194a289832576287d6f8ad74e3d0",
      "url": "http://github.com/defunkt/github/commit/de8251ff97ee194a289832576287d6f8ad74e3d0",
      "author": {
        "email": "chris@ozmm.org",
        "name": "Chris Wanstrath" 
      },
      "message": "update pricing a tad",
      "timestamp": "2008-02-15T14:36:34-08:00" 
    }
  ],
  "after": "de8251ff97ee194a289832576287d6f8ad74e3d0",
  "ref": "refs/heads/master" 
}
"""

INVALID_JSON_COMMITS = """{ 
  "repository": {
    "url": "wrong",
    "owner": {
      "email": "wrong",
      "name": "`FILTERED`" 
    }
  },
  "commits": [
    {
      "id": "41a212ee83ca127e3c8cf465891ab7216a705f59",
      "url": "http://github.com/defunkt/github/commit/41a212ee83ca127e3c8cf465891ab7216a705f59",
      "author": {
        "email": "chris@ozmm.org",
        "name": "`FILTERED`" 
      },
      "added": ["filepath.rb"]
    }
  ]
}
"""

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
        # create two commit, one 5 sec younger than the other 
        db = self.env.get_db_cnx()
        now = to_timestamp(datetime.now(utc))
        data1 = COMMITS[0]
        commit1 = GitHubCommit(self.env, git_url=GIT_URL, **data1)
        commit1.time = now 
        commit1.save(db=db)
        data2 = COMMITS[1]
        commit2 = GitHubCommit(self.env, git_url=GIT_URL, **data2)
        commit2.time = now + 5
        commit2.save(db=db)
        db.commit()
        
        commit_before_now = GitHubCommit.get_commit_by_date(
            self.env, now - 1, now, git_url=GIT_URL)
        commit_before_now = [x for x in commit_before_now]
        eq_(1, len(commit_before_now))
        eq_(commit1.url, commit_before_now[0].url)
        
        commit_now = GitHubCommit.get_commit_by_date(
            self.env, now, now + 5, git_url=GIT_URL)
        commit_now = [x for x in commit_now]
        eq_(2, len(commit_now))
        
        future_commit = GitHubCommit.get_commit_by_date(
            self.env, now + 6, now + 7, git_url=GIT_URL)
        future_commit = [x for x in future_commit]
        eq_(0, len(future_commit))
        
    @raises(StopIteration)
    def test_create_from_json(self):
        commits = GitHubCommit.create_from_json(
            self.env, JSON_COMMITS, git_url=GIT_URL)
        for x in range(2):
            commit = commits.next()
            eq_(self.env, commit.env)
            eq_(COMMITS[x]['id'], commit.id)
            eq_(COMMITS[x]['url'], commit.url)
            eq_(COMMITS[x]['message'], commit.message)
            eq_(COMMITS[x]['author']['name'], commit.name)
            eq_(COMMITS[x]['author']['email'], commit.email)
            ok_(not commit.is_clone())
        
        commits.next() # should raise an exception
        
    def test_filter_fields(self):
        data = simplejson.loads(INVALID_JSON_COMMITS)
        GitHubCommit.filter_fields(data)
        eq_(None, data['repository']['url'])
        eq_(None, data['repository']['owner']['email'])
        eq_('FILTERED', data['repository']['owner']['name'])
        eq_('chris@ozmm.org', data['commits'][0]['author']['email'])
        eq_('41a212ee83ca127e3c8cf465891ab7216a705f59', data['commits'][0]['id'])
        eq_('http://github.com/defunkt/github/commit/41a212ee83ca127e3c8cf465891ab7216a705f59',
            data['commits'][0]['url'])
        eq_('chris@ozmm.org',
            data['commits'][0]['author']['email'])
        
        
        
        
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
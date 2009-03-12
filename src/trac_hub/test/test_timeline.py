"""
Created on 11 Mar 2009

@author: damien
"""

from datetime import datetime
import unittest

from trac.util.datefmt import to_timestamp, utc
from trac.test import EnvironmentStub
from trac.db.api import DatabaseManager
from nose.tools import ok_, eq_, raises

from trac_hub.install import TracHubSetup
from trac_hub.test.test_model import GIT_URL, COMMITS
from trac_hub.model import GitHubCommit
from trac_hub.timeline import GitHubEventProvider

class TestGitHubTimeLine(unittest.TestCase):

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
        
        self.now = to_timestamp(datetime.now(utc))
        self.github_event_provider = GitHubEventProvider(self.env.compmgr)
        
    def _create_commit(self):
        c = GitHubCommit(self.env, git_url=GIT_URL, **COMMITS[0])
        c.time = self.now
        c.save()
        c = GitHubCommit(self.env, git_url=GIT_URL, **COMMITS[1])
        c.time = self.now + 5
        c.url = 'http://example.com/example.git'
        c.save()

    def test_get_timeline_filters(self):
        kinds = [x for x,y in self.github_event_provider.get_timeline_filters({})]
        ok_('main_git_repository' in kinds)
        ok_('cloned_git_repository' in kinds)
    
    @raises(StopIteration)    
    def test_get_main_git_events(self):
        self._create_commit()
        events = self.github_event_provider.get_timeline_events(
            {},
            datetime.fromtimestamp(self.now - 10, utc) ,
            datetime.fromtimestamp(self.now + 10, utc) ,
            ('main_git_repository',))
        kind, date, author, commit = events.next()
        eq_('main_git_repository', kind)
        eq_(self.now, to_timestamp(date))
        eq_("%(name)s <%(email)s>" % COMMITS[0]['author'], author)
        eq_(COMMITS[0]['url'], commit.url)
        events.next()
        
    @raises(StopIteration)    
    def test_get_cloned_git_events(self):
        self._create_commit()
        events = self.github_event_provider.get_timeline_events(
            {},
            datetime.fromtimestamp(self.now - 10, utc) ,
            datetime.fromtimestamp(self.now + 10, utc) ,
            ('cloned_git_repository',))
        kind, date, author, commit = events.next()
        eq_('cloned_git_repository', kind)
        eq_(self.now + 5, to_timestamp(date))
        eq_("%(name)s <%(email)s>" % COMMITS[1]['author'], author)
        eq_('http://example.com/example.git', commit.url)
        events.next()
    
    @raises(StopIteration)
    def test_get_no_events(self):
        self._create_commit()
        events = self.github_event_provider.get_timeline_events(
            {},
            datetime.fromtimestamp(self.now - 20, utc) ,
            datetime.fromtimestamp(self.now - 10, utc) ,
            ('main_git_repository','cloned_git_repository', ))
        events.next()
        events.next()
        
    def test_get_all_events(self):
        self._create_commit()
        events = self.github_event_provider.get_timeline_events(
            {},
            datetime.fromtimestamp(self.now - 10, utc) ,
            datetime.fromtimestamp(self.now + 10, utc) ,
            ('main_git_repository','cloned_git_repository', ))
        events = [x for x in events]
        eq_(2, len(events))
        
    def test_render_timeline_event(self):
        commit = GitHubCommit(self.env, git_url=GIT_URL, **COMMITS[0])
        def render(field):
            return str(self.github_event_provider.render_timeline_event({}, field, ('','','',commit)))
        eq_(COMMITS[0]['url'], render('url'))
        eq_("Revision <em>%s</em>" % COMMITS[0]['id'], render('title'))
        eq_(COMMITS[0]['message'], render('description'))
        
    def test_render_xss_event(self):
        commit = GitHubCommit(self.env, git_url=GIT_URL, **COMMITS[0])
        commit.url = """http://example" onclick="alert('xss')"""
        commit.id = """1234567<script>alert('xss')</script>"""
        commit.message = """<a href="http://example" onclick="alert('xss')">foo</a><script>alert('xss')</script>"""
        def render(field):
            return str(self.github_event_provider.render_timeline_event({}, field, ('','','',commit)))
        eq_("Revision <em>1234567&lt;script&gt;alert('xss')&lt;/script&gt;</em>", render('title'))
        eq_(
            """&lt;a href="http://example" onclick="alert(\'xss\')"&gt;foo&lt;/a&gt;&lt;script&gt;alert(\'xss\')&lt;/script&gt;""",
            render('description'))        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
# -*- coding: utf-8 -*-
"""
Created on 8 Mar 2009

@author: damien lebrun
"""
from trac.core import Interface, Component, ExtensionPoint, implements
from trac.web.api import IRequestHandler
from trac.config import Option

from trac_hub.model import GitHubCommit, GitHubCommitException


class GitHubPostError(Exception):
    pass


class IGitHubPostObservers(Interface):
    
    def process_commit(commit): #@NoSelf
        """
        Called when some commits are pushed to your project
        or one of its clone (called for each commit):
        
        * "commit" is a GitHubCommit instance.
        """


class GitHubPostParser(Component):
    """
    It parses data sent by GitHub on a post-receive.
    
    It doesn't do anything with it but let extensions that implement trac_hub.IGitHubPostObservers
    process the commit data.
    """

    implements(IRequestHandler)
    observers = ExtensionPoint(IGitHubPostObservers)
    github_url = Option('trachub', 'github_url', '',
        doc="""Your main GitHub repository (like http://github.com/username/projectname).""")
    
    def match_request(self, req):
        """
        Return true is the request match "/github".
        """
        serve = req.path_info.rstrip('/') == '/github' and req.method == 'POST'
        if serve:
            self.processHook = True
            # Hack from GitHubPlugin to bypass a CSRF protection I am guessing.
            req.form_token = None
 
        self.env.log.debug("Handle Request: %s" % serve)
        return serve
        
    def process_request(self, req):
        """
        Parse Github post and call all components implementing IGitHubPostObservers.
        """
        msg = 'ok'
        status = 200
        db = self.env.get_db_cnx()
        try:
            json = req.args.get('payload')
            for commit in GitHubCommit.create_from_json(self.env, json, git_url=self.github_url, db=db):
                self.env.log.debug("Calling observer(s) for commit: %s" % commit.url)
                for observer in self.observers:
                    observer.process_commit(commit)
                
        except (GitHubCommitException), e:
            db.rollback()
            self.env.log.error('An error occurred: %s' % str(e))
            msg = 'An error occurred: %s' % str(e)
            status = 404
        req.send(msg, content_type='text/plain', status=status)


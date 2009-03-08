"""
Created on 8 Mar 2009

@author: damien lebrun
"""

from trac.core import Interface, Component, ExtensionPoint, implements
from trac.web.api import IRequestHandler
import simplejson


class IGitHubPostObservers(Interface):
    
    def process_commit(post_data, commit_data): #@NoSelf
        """Called when some commits are pushed to your project
        or one of its clone (called for each commit)."""


class GitHubPostParser(Component):
    """
    It parses data sent by GitHub on a post-receive.
    
    It doesn't do anything with it but let extensions that implement trac_hub.IGitHubPostObservers
    process the commit data.
    """

    implements(IRequestHandler)
    observers = ExtensionPoint(IGitHubPostObservers)
    
    def match_request(self, req):
        """Return true is the request match "/github"."""
        serve = req.path_info.rstrip('/') == '/github' and req.method == 'POST'
        if serve:
            self.processHook = True
            # Hack from GitHubPlugin to bypass a CSRF protection I am guessing.
            req.form_token = None
 
        self.env.log.debug("Handle Request: %s" % serve)
        return serve
        
    def process_request(self, req):
        """Parse Github post and call all components implementing IGitHubPostObservers."""
        msg = 'ok'
        status = 200
        try:
            data = req.args.get('payload')
            self.env.log.debug("Payload to parse: %s" % data)
            json_data = simplejson.loads(data)
            for commit_data in json_data.get('commits'):
                self.env.log.debug("Calling observer(s) for commit: %s" % commit_data)
                for observer in self.observers:
                    observer.process_commit(json_data, commit_data)
        except (ValueError, TypeError), e:
            self.env.log.error('Invalid data (%s).' % str(e))
            msg = 'Invalid data.'
            status = 404
        req.send(msg, content_type='text/plain', status=status)



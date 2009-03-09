# -*- coding: utf-8 -*-
"""
Created on 8 Mar 2009

@author: damien lebrun
"""
import re

from trac.core import Interface, Component, ExtensionPoint, implements
from trac.web.api import IRequestHandler
import simplejson

re_url = re.compile(r"""^
    (# Scheme
     (https?|git):
     (# Authority & path
      //
      ([a-z0-9\-._~%!$&'()*+,;=]+@)?              # User
      ([a-z0-9\-._~%]+                            # Named host
      |\[[a-f0-9:.]+\]                            # IPv6 host
      |\[v[a-f0-9][a-z0-9\-._~%!$&'()*+,;=:]+\])  # IPvFuture host
      (:[0-9]+)?                                  # Port
      (/[a-z0-9\-._~%!$&'()*+,;=:@]+)*/?          # Path
     )
    )
    # Query
    (\?[a-z0-9\-._~%!$&'()*+,;=:@/?]*)?
    # Fragment
    (\#[a-z0-9\-._~%!$&'()*+,;=:@/?]*)?
    $""", re.VERBOSE | re.IGNORECASE)

re_email = re.compile(
    r"""
    [a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*
    @(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"""
    , re.VERBOSE | re.IGNORECASE)

re_general = re.compile(
    r"""[^-_\!"\$%\^&\*\(\)\+=\{\}\[\]:;'@~#\|\\,./<>\?a-z0-9\s ]+""",
    re.IGNORECASE)

def validate_url(url):
    return bool(re_url.match(url))

def validate_email(email):
    return bool(re_email.match(email))

def filter(field):
    return re_general.sub('', field)

class GitHubPostError(Exception):
    pass


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
            json_data = self.validate_payload(data)
            for commit_data in json_data.get('commits'):
                self.env.log.debug("Calling observer(s) for commit: %s" % commit_data)
                for observer in self.observers:
                    observer.process_commit(json_data, commit_data)
        except (GitHubPostError), e:
            self.env.log.error('An error occurred: %s' % str(e))
            msg = 'An error occurred: %s' % str(e)
            status = 404
        req.send(msg, content_type='text/plain', status=status)
        
    def validate_payload(self, json_string):
        try:
            self.env.log.debug("Payload to parse: %s" % json_string)
            json_data = simplejson.loads(json_string)
        except(ValueError, TypeError), e:
            raise GitHubPostError(
                'Wrong json syntax (%s) in: %s' % (str(e), json_string,))
        
        self.validate_fields(json_data)
        
        return json_data
    
    def validate_fields(self, fields):
        for field in fields:
            if field in ('owner','author','repository'):
                self.validate_fields(fields[field])
            elif field == 'commits':
                for commit in fields[field]:
                    self.validate_fields(commit)                    
            elif field == 'email':
                if not validate_email(fields[field]):
                    raise GitHubPostError(
                        '%s is not valid' % fields[field])
            elif field == 'url':
                if not validate_url(fields[field]):
                    raise GitHubPostError(
                        '%s is not url' % fields[field])
            else:
                try:
                    fields[field] = filter(fields[field])
                except:
                    fields[field] = None
                    
        #TODO: validate required fields



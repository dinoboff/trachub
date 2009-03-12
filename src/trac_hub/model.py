"""
Created on 10 Mar 2009

@author: damien
"""
from datetime import datetime
import simplejson
import re

from trac.util.datefmt import to_timestamp, utc

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

re_message_parser = re.compile(
    r"""(
      fix(?:e(?:d|s)?)?|
      ref?\.?

    )?\:?\s+(
      (?:(?:issues?\s+|\#|i)\d+)
      (?:\s*(?:,|&|and)\s+(?:\#?\d+))*
    )""", 
    re.IGNORECASE | re.VERBOSE)

re_int = re.compile(r"(\d+)")

def validate_url(url):
    return bool(re_url.match(url))

def validate_email(email):
    return bool(re_email.match(email))

def filter(field):
    return re_general.sub('', field)


class GitHubCommitException(Exception):
    pass


class GitHubCommitNoRecord(Exception):
    pass


class GitHubCommit(object):
    
    default_action = 'ref'    
    commit_action = {
        '':     'ref',
        'ref':  'ref',
        're':   'ref',
        'ref.':  'ref',
        're.':   'ref',
        'fix':  'fixed',
        'fixe': 'fixed', # I know
        'fixes':'fixed',
        'fixed':'fixed'
        }
    
    def __init__(self, env, git_url=None, **kw):
        self.env = env
        self.git_url = git_url
        self.id = kw.get('id')
        self.url = kw.get('url')
        self.time = kw.get('time')
        self.name = kw.get('author', {}).get('name')
        self.email = kw.get('author', {}).get('email')
        self.message = kw.get('message')
        
    def _get_db(self, db):
        return db or self.env.get_db_cnx()

    def _get_db_for_write(self, db):
        if db:
            return (db, lambda: True)
        else:
            db = self.env.get_db_cnx()
            return (db, db.commit)
    
    def is_clone(self):
        if not self.git_url:
            return True
        return not self.url.startswith(self.git_url)
    
    @property
    def author(self):
        try:
            return '%s <%s>' % (self.name, self.email,)
        except (TypeError, KeyError):
            return self._author
    
    def save(self, db=None):
        db, commit = self._get_db_for_write(db)
        cursor = db.cursor()
        sql = """INSERT INTO github_revisions
        (id, url, time, name, email, message)
        VALUES(%s, %s, %s, %s, %s, %s)"""
        self.time = self.time or to_timestamp(datetime.now(utc))
        cursor.execute(sql, (
            self.id,
            self.url,
            self.time,
            self.name,
            self.email,
            self.message,))
        commit()
            
    def parse_message(self):
        """
        Parse the commit message ticket relative information.
        
        Return a list  of '(action, ticket id)' tuple
        """
        for action_match in re_message_parser.finditer(self.message):
            action, tickets = action_match.groups()
            for ticket_match in re_int.finditer(tickets):
                for ticket_id in ticket_match.groups():
                    yield(
                        self.commit_action.get(str(action).lower(), self.default_action),
                        int(ticket_id)
                        )
            
    @classmethod
    def get_commit_by_date(cls, env, start, stop, git_url=None):
        db = env.get_db_cnx()
        cursor = db.cursor()
        sql = """SELECT id, url, time, name, email, message
        FROM github_revisions
        WHERE time>=%s AND time<=%s"""
        cursor.execute(sql, (start, stop,))
        for id, url, time, name, email, message in cursor:
            event =  cls(env,git_url=git_url, id=id, url=url, time=time, message=message)
            event.name = name
            event.email = email
            yield event
            
    @classmethod
    def create_from_json(cls, env, json, git_url='', db=None):
        try:
            fields = simplejson.loads(json)
        except(ValueError, TypeError), e:
            raise GitHubCommitException(
                'Wrong json syntax (%s) in: %s' % (str(e), json,))
        
        cls.filter_fields(fields)
        for commit_data in fields.get('commits'):
            try:
                commit = GitHubCommit(env, git_url=git_url, db=db, **commit_data)
                commit.save()
                yield commit
            except Exception, e:
                raise GitHubCommitException('Could not save commit: %s' % str(e))    
    
    @classmethod
    def filter_fields(cls, fields):
        
        # convert unicode keys to string
        for field in fields:
            value = fields[field]
            del fields[field]
            fields[str(field)] = value
        
        # validate
        for field in fields:
            if field in ('owner','author','repository'):
                cls.filter_fields(fields[field])
            elif field == 'commits':
                for commit in fields[field]:
                    cls.filter_fields(commit)                    
            elif field == 'email':
                if not validate_email(fields[field]):
                    fields[field] = None
                    
            elif field == 'url':
                if not validate_url(fields[field]):
                    fields[field] = None
            else:
                try:
                    fields[field] = filter(fields[field])
                except:
                    fields[field] = None
    
    def __repr__(self):
        return """<GitHubEvent(%r, git_url=%r,
        id=%r, url=%r, author=%r, message=%r)>""" % (
            self.env, self.git_url, self.id, self.url,
            {'name':self.name, 'email': self.email},
            self.message,)


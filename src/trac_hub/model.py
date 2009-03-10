"""
Created on 10 Mar 2009

@author: damien
"""
from datetime import datetime

from trac.util.datefmt import to_timestamp, utc


class GitHubCommit(object):
    
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
    
    @classmethod
    def get_commit_by_date(cls, env, start, stop, git_url=None):
        db = env.get_db_cnx()
        cursor = db.cursor()
        sql = """SELECT id, url, time, name, email, message
        FROM github_revisions
        WHERE time>=%s AND time<=%s"""
        cursor.execute(sql, (to_timestamp(start), to_timestamp(stop),))
        for id, url, time, name, email, message in cursor:
            event =  cls(env,git_url=git_url, id=id, url=url, time=time, message=message)
            event.name = name
            event.email = email
            yield event
            
    
    def __repr__(self):
        return """<GitHubEvent(%r, git_url=%r,
        id=%r, url=%r, author=%r, message=%r)>""" % (
            self.env, self.git_url, self.id, self.url,
            {'name':self.name, 'email': self.email},
            self.message,)


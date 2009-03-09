"""
Created on 8 Mar 2009

@author: damien
"""
from datetime import datetime

from trac.core import implements, Component
from trac.timeline.api import ITimelineEventProvider
from trac.config import Option
from trac.util.datefmt import utc, to_timestamp

from trac_hub.post_parser import IGitHubPostObservers, GitHubPostError
from trac.resource import Resource
from genshi.builder import tag
from trac.wiki.formatter import format_to

class GitHubEvent(object):
    
    def __init__(self, env, config, **kw):
        self.env = env
        self.config = config
        self.db = self.env.get_db_cnx()
        self.rev = kw.get('id')
        self.url = kw.get('url')
        self.time = kw.get('time')
        self.name = kw.get('author', {}).get('name')
        self.email = kw.get('author', {}).get('email')
        self.message = kw.get('message')
        
    def is_clone(self):
        github_url = self.config.get('trachub', 'github_url', '')
        if not github_url:
            return True
        return self.url.startswith(github_url)
    
    @property
    def author(self):
        try:
            return '%s <%s>' % (self.name, self.email,)
        except (TypeError, KeyError):
            return self._author
    
    def save(self):
        cursor = self.db.cursor()
        sql = """INSERT INTO github_revisions
        (rev, url, time, name, email, message)
        VALUES(%s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (
            self.rev,
            self.url,
            to_timestamp(datetime.now(utc)),
            self.name,
            self.email,
            self.message,))
        self.db.commit()
    
    @classmethod
    def get_event_date(cls, env, config, start, stop):
        db = env.get_db_cnx()
        cursor = db.cursor()
        sql = """SELECT rev, url, time, name, email, message
        FROM github_revisions
        WHERE time>=%s AND time<=%s"""
        cursor.execute(sql, (to_timestamp(start), to_timestamp(stop),))
        for rev, url, time, name, email, message in cursor:
            event =  cls(env,config, id=rev, url=url, time=time, message=message)
            event.name = name
            event.email = email
            yield event
            
    
    def __repr__(self):
        return """< GitHubEvent(%s, %s, %s) >""" % (self.env, self.config,
            {
                'id': self.rev, 'url': self.url,
                'author': {'name':self.name, 'email': self.email},
                'message': self.message
            })


class GitHubEventProvider(Component):
    """
    Save new commits event to the database
    and provide GitHub event to Trac's time line
    """
    implements(IGitHubPostObservers, ITimelineEventProvider)
    
    github_url = Option('trachub', 'github_url', '',
        doc="""Your main GitHub repository (like http://github.com/username/projectname).""")

        
    def process_commit(self, post_data, commit_data):
        """
        Save commit into the database
        """
        try:
            kw = dict()
            for x in commit_data:
                kw[str(x)] = commit_data[x]
            event = GitHubEvent(self.env, self.config, **kw)
            self.log.debug("Saving event: %s" % event)
            event.save()
        except Exception, e:
            raise GitHubPostError('Could not save event: %s' % str(e))
        
    def get_timeline_filters(self, req):
        """
        Return a list of filters that this provider support: commits for the main repository
        and commits from its clones.
        """
        return (
            ('main_git_repository','Main repository commits'),
            ('cloned_git_repository','Cloned repository commits'),
            )

    def get_timeline_events(self, req, start, stop, filters):
        """
        Return a list of events in the time range given by the `start` and
        `stop` parameters.

        The `filters` parameters is a list of the enabled filters, each item
        being the name of the tuples returned by `get_timeline_filters`.

        Since 0.11, the events are `(kind, date, author, data)` tuples,
        where `kind` is a string used for categorizing the event, `date`
        is a `datetime` object, `author` is a string and `data` is some
        private data that the component will reuse when rendering the event.

        When the event has been created indirectly by another module,
        like this happens when calling `AttachmentModule.get_timeline_events()`
        the tuple can also specify explicitly the provider by returning tuples
        of the following form: `(kind, date, author, data, provider)`.
        """
        if 'main_git_repository' in filters or \
            'cloned_git_repository' in filters:
            for event in GitHubEvent.get_event_date(self.env, self.config, start, stop):
                if event.is_clone() and 'cloned_git_repository' in filters:
                    yield ('cloned_git_repository',
                        datetime.fromtimestamp(event.time, utc),
                        event.author,
                        event)
                elif not event.is_clone() and 'main_git_repository' in filters:
                    yield ('main_git_repository',
                        datetime.fromtimestamp(event.time, utc),
                        event.author,
                        event) # TODO: only sent data needed


    def render_timeline_event(self, context, field, event):
        """
        Display the title of the event in the given context.

        :param context: the rendering `Context` object that can be used for
                        rendering
        :param field: what specific part information from the event should
                      be rendered: can be the 'title', the 'description' or
                      the 'url'
        :param event: the event tuple, as returned by `get_timeline_events`
        """
        # TODO Econde output (how do you use context?)
        ghevent = event[3]
        if field == 'url':
            return ghevent.url # TODO Econde output (how do you use context?)
        elif field == 'title':
            return tag('Revision ', tag.em(ghevent.rev))
        elif field == 'description':
            return tag(ghevent.message)
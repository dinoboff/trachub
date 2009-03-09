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

class GitHubEvent(object):
    
    def __init__(self, env, conf, *args, **kw):
        self.env = env
        self.conf = conf
        self.db = self.env.get_db_cnx()
        self.id = kw.get('id')
        self.url = kw.get('url')
        self._author = kw.get('author')
        self.message = kw.get['message']
        
    def is_clone(self):
        github_url = self.conf.get('trac-hub').get('github-url')
        if not github_url:
            raise GitHubPostError('github-url option is not set')
        return self.url.startswith(github_url)
    
    @property
    def author(self):
        try:
            return '%(name)s < %(email)s >' % self._author
        except (TypeError, KeyError):
            return self._author
    
    def save(self):
        cursor = self.db.cursor()
        sql = """INSERT INTO github_revisions
        (rev, url, clone, time, author, message)
        VALUES(%s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (
            self.id,
            self.url,
            self.is_clone(),
            to_timestamp(datetime.now(utc)),
            self.author,
            self.message,))
        self.db.commit()


class GitHubEventProvider(Component):
    """
    Save new commits event to the database
    and provide GitHub event to Trac's time line
    """
    implements(IGitHubPostObservers, ITimelineEventProvider)
    
    github_url = Option('trachub', 'github-url', '',
        doc="""Your main GitHub repository (like http://github.com/username/projectname).""")

        
    def process_commit(self, post_data, commit_data):
        """
        Save commit into the database
        """
        try:
            event = GitHubEvent(self.env, self.conf, **commit_data)
            event.save()
        except:
            raise GitHubPostError('This commit (%s) were already saved' % commit_data['id'])
        
    def get_timeline_filters(self, req):
        """
        Return a list of filters that this provider support: commits for the main repository
        and commits from its clones.
        """
        if 'CHANGESET_VIEW' in req.perm:
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
        return ()

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
        
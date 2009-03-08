"""
Created on 8 Mar 2009

@author: damien
"""
from datetime import datetime
import time

from trac.core import implements, Component
from trac.timeline.api import ITimelineEventProvider
from trac.db.schema import Table, Column, Index
from trac.db.api import DatabaseManager
from trac.config import Option
from trac.util.datefmt import utc, to_timestamp

from post_parser import IGitHubPostObservers



schema = [
    Table('github_revisions', key='rev')[
        Column('rev'),
        Column('url'),
        Column('clone', type='int'),
        Column('time', type='int'),
        Column('author'),
        Column('message'),
        Index(['time'])]
    ]


class GitHubEventProvider(Component):
    """
    Save new commits event to the database
    and provide GitHub event to Trac's time line
    """
    implements(IGitHubPostObservers, ITimelineEventProvider)
    
    git_hub_url = Option('trachub', 'git_hub_url', '',
        doc="""Your main GitHub repository (like http://github.com/username/projectname).""")

    def __init__(self):
        # Far too hackish! FIXME 
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        try:
            cursor.execute("select count(*) from github_revisions")
            db.commit()
        except:
            self.log.debug('installing GitHub event schema.')
            connector, args = DatabaseManager(self.env)._get_connector()
            for table in schema:
                for stmt in connector.to_sql(table):
                    self.log.debug('Will execute: %s' % stmt)
                    cursor.execute(stmt)
            db.commit()

        
    def process_commit(self, post_data, commit_data):
        """
        Save commit into the database
        """
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        sql = "INSERT INTO github_revisions (rev, url, clone, time, author, message) VALUES(?,?,?,?,?,?)"
        args = (
            commit_data['id'],
            commit_data['url'],
            int(commit_data['url'].startswith(self.git_hub_url)),
            to_timestamp(datetime.now(utc)),
            '%(name)s < %(email)s >' % commit_data['author'],
            commit_data['message'],
            )
        self.log.debug('%s (%i)' % (args, len(args),))
        try:
            cursor.execute(
                "INSERT INTO github_revisions (rev, url, clone, time, author, message) VALUES(%s, %s, %s, %s, %s, %s)",
                args)
            db.commit()
        except:
            raise ValueError('This commit (%s) were already saved' % commit_data['id'])
        
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
        
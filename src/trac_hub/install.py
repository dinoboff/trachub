"""
Created on 9 Mar 2009

@author: damien
"""
from trac.core import Component, implements
from trac.env import IEnvironmentSetupParticipant
from trac.db.schema import Table, Column, Index


# Database version identifier for upgrades.
db_version = 1

# Database schema
schema = [
    Table('github_revisions', key='url')[
        Column('url'),
        Column('id'),
        Column('time', type='int'),
        Column('name'),
        Column('email'),
        Column('message'),
        Index(['time'])]
    ]

# Create tables
def to_sql(env, table):
    """ Convenience function to get the to_sql for the active connector."""
    from trac.db.api import DatabaseManager
    dm = env.components[DatabaseManager]
    dc = dm._get_connector()[0]
    return dc.to_sql(table)

def create_tables(cursor, env):
    """ Creates the basic tables as defined by schema.
    using the active database connector. """
    for table in schema:
        for stmt in to_sql(env, table):
            cursor.execute(stmt)
    cursor.execute("INSERT into system values ('trachub_version', '1')")
    cursor.execute("INSERT into system values ('trachub_infotext', '')")


class TracHubSetup(Component):
    """
    Setup and upgrade tables require for GitHub events.
    
    Thanks to Simon from CodeResort.
    """
    
    implements(IEnvironmentSetupParticipant)

    def environment_created(self):
        """Called when a new Trac environment is created."""
        pass

    def environment_needs_upgrade(self, db):
        """Called when Trac checks whether the environment needs to be upgraded.
        Returns `True` if upgrade is needed, `False` otherwise."""
        cursor = db.cursor()
        return self._get_version(cursor) != db_version

    def upgrade_environment(self, db):
        """Actually perform an environment upgrade, but don't commit as
        that is done by the common upgrade procedure when all plugins are done."""
        cursor = db.cursor()
        if self._get_version(cursor) == 0:
            create_tables(cursor, self.env)
        else:
            # do upgrades here when we get to that...
            pass

    def _get_version(self, cursor):
        try:
            sql = "SELECT value FROM system WHERE name='trachub_version'"
            self.log.debug(sql)
            cursor.execute(sql)
            for row in cursor:
                return int(row[0])
            return 0
        except:
            return 0
        
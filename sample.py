import psycopg2
import os

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gndata_api.settings")

    from gndata_api import settings
    from django.core.management import call_command
    from metadata.tests.assets import Assets as MA
    from ephys.tests.assets import Assets as EA

    # connect to the database
    db = settings.DATABASES['default']

    try:
        conn = psycopg2.connect(
            "dbname='%s' host='%s' user='%s' password='%s'" % (
                db['NAME'], db['HOST'], db['USER'], db['PASSWORD']
            )
        )
        cur = conn.cursor()
    except:
        print "Unable to connect to the database"

    # (re)-create database schema
    try:
        cur.execute("""drop schema public cascade;""")
    except:
        cur.connection.rollback()
    finally:
        cur.execute("""create schema public;""")
        cur.connection.commit()

    # create tables for the new schema
    call_command('syncdb')

    if settings.DEBUG:  # count as Dev environment
        # create test users
        call_command('loaddata', 'users')

        # create test metadata
        MA().fill()

        # create test ephys objects
        EA().fill()

    else:
        # create test users
        call_command('loaddata', 'production_users')
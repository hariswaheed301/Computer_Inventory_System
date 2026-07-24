"""Create or update the database schema without inserting demo users or products."""

from wsgi import init_database


if __name__ == '__main__':
    init_database()
    print('Database schema is ready.')

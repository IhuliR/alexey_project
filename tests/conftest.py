import os


os.environ.setdefault(
    'SECRET_KEY',
    'test-secret-key-for-formaslov-fastapi-tests',
)

if os.getenv('TEST_REDIS_URL'):
    os.environ.setdefault('REDIS_URL', os.environ['TEST_REDIS_URL'])

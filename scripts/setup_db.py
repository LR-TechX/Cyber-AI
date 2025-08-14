import os
from app.backend.database import DatabaseManager


def main():
	base = os.path.expanduser('~/.cybersentinel')
	os.makedirs(base, exist_ok=True)
	db = DatabaseManager(os.path.join(base, 'cybersentinel.db'))
	print('Database initialized at', os.path.join(base, 'cybersentinel.db'))
	db.close()


if __name__ == '__main__':
	main()
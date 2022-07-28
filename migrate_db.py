import psycopg2 as db
import os

host=os.environ['DB_HOST']
user=os.environ['DB_USERNAME']
password=os.environ['DB_PASSWORD']
database=os.environ['DB_DATABASE']

def rename_column(table, old_name, new_name):
	try:
		conn = db.connect(host=host, database=database, user=user, password=password)
		conn.autocommit = True
		cursor = conn.cursor()
		cursor.execute(f'ALTER TABLE {table} RENAME COLUMN {old_name} TO {new_name}')
		conn.close()
		print(f'RENAMED {table} - {old_name} to {new_name}')
	except Exception as e:
		print(f'RENAME {table} {old_name} {new_name}\n{e}')

def not_required_column(table, name):
	try:
		conn = db.connect(host=host, database=database, user=user, password=password)
		conn.autocommit = True
		cursor = conn.cursor()
		cursor.execute(f'ALTER TABLE {table} ALTER COLUMN {name} DROP NOT NULL')
		conn.close()
		print(f'NOT_REQUIRED {table} - {name}')
	except Exception as e:
		print(f'NOT_REQUIRED {table} {name}\n{e}')

def add_column(table, name, data_type):
	try:
		conn = db.connect(host=host, database=database, user=user, password=password)
		conn.autocommit = True
		cursor = conn.cursor()
		cursor.execute(f'ALTER TABLE {table} ADD COLUMN {name} {data_type}')
		conn.close()
		print(f'ADD {table} - {name} {data_type}')
	except Exception as e:
		print(f'ADD {table} {name} {data_type}\n{e}')

def drop_column(table, name):
	try:
		conn = db.connect(host=host, database=database, user=user, password=password)
		conn.autocommit = True
		cursor = conn.cursor()
		cursor.execute(f'ALTER TABLE {table} DROP COLUMN {name}')
		conn.close()
		print(f'DROP {table} - {name}')
	except Exception as e:
		print(f'DROP {table} {name}\n{e}')

def change_type(table, name, data_type):
	try:
		conn = db.connect(host=host, database=database, user=user, password=password)
		conn.autocommit = True
		cursor = conn.cursor()
		cursor.execute(f'ALTER TABLE {table} ALTER COLUMN {name} TYPE {data_type}')
		conn.close()
		print(f'ALTER COLUMN TYPE {table} - {name} {data_type}')
	except Exception as e:
		print(f'ALTER COLUMN TYPE {table} {name} {data_type}\n{e}')


if __name__ == '__main__':

	rename_column('payment','address','eth_address')
	rename_column('payment','tier1_expected_amount','tier1_expected_amount_eth')
	rename_column('payment','tier2_expected_amount','tier2_expected_amount_eth')
	rename_column('payment','amount','amount_eth')

	rename_column('payment','tier1_expected_amount_sys','tier1_expected_amount_wsys')
	rename_column('payment','tier2_expected_amount_sys','tier2_expected_amount_wsys')
	rename_column('payment','amount_sys','amount_wsys')

	drop_column('payment','tier1_expected_amount_sys')
	drop_column('payment','tier2_expected_amount_sys')
	drop_column('payment','amount_sys')
    
	not_required_column('payment','pending')
	not_required_column('payment','eth_address')
	not_required_column('payment','tier1_expected_amount_eth')
	not_required_column('payment','tier2_expected_amount_eth')

	change_type('project', 'api_token_count', 'bigint')
	change_type('project', 'used_api_tokens', 'bigint')

	add_column('payment','eth_token', 'text')
	add_column('payment','eth_privkey', 'text')
	add_column('payment','avax_token', 'text')
	add_column('payment','avax_address', 'text')
	add_column('payment','avax_privkey', 'text')
	add_column('payment','nevm_token', 'text')
	add_column('payment','nevm_address', 'text')
	add_column('payment','nevm_privkey', 'text')
	add_column('payment','tier1_expected_amount_ablock', 'float8')
	add_column('payment','tier2_expected_amount_ablock', 'float8')
	add_column('payment','tier1_expected_amount_aablock', 'float8')
	add_column('payment','tier2_expected_amount_aablock', 'float8')
	add_column('payment','tier1_expected_amount_sysblock', 'float8')
	add_column('payment','tier2_expected_amount_sysblock', 'float8')
	add_column('payment','tier1_expected_amount_wsys', 'float8')
	add_column('payment','tier2_expected_amount_wsys', 'float8')
	add_column('payment','amount_ablock', 'float8')
	add_column('payment','amount_aablock', 'float8')
	add_column('payment','amount_sysblock', 'float8')
	add_column('payment','amount_wsys', 'float8')



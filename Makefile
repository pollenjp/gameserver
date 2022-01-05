MYSQL_HOST := 127.0.0.1
# MYSQL_HOST := 172.18.0.2

run:
	uvicorn app.api:app --reload

format:
	isort app tests
	black app tests

test:
	pytest -sv tests

.PHONY: init_db
init_db:
	mysql \
		--user=webapp \
		--password=webapp_no_password \
		-h ${MYSQL_HOST} \
		webapp \
		< schema.sql

.PHONY: reset_db
reset_db:
	mysql \
		--user=webapp \
		--password=webapp_no_password \
		-h ${MYSQL_HOST} \
		webapp \
		< reset_table.sql

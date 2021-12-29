MYSQL_HOST := 172.24.0.2

run:
	uvicorn app.api:app --reload

format:
	isort app tests
	black app tests

test:
	pytest -sv tests

reset_db:
	mysql \
		--user=webapp \
		--password=webapp_no_password \
		-h ${MYSQL_HOST} \
		webapp \
		< reset_table.sql

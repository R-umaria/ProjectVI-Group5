.PHONY: run test format lint db-up db-migrate db-upgrade

run:
	flask --app boxedwithlove.wsgi run --debug --host=0.0.0.0 --port=8080

test:
	pytest -q

db-migrate:
	flask --app boxedwithlove.wsgi db migrate -m "auto"

db-upgrade:
	flask --app boxedwithlove.wsgi db upgrade

db-up:
	docker compose up --build

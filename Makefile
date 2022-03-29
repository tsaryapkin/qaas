export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

all: down build up

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down --remove-orphans

test:
	docker-compose run --rm qaas pytest /code

logs:
	docker-compose logs --tail=25 qaas
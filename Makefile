COMPOSE:=docker compose
SHELL:=/bin/bash

.PHONY: up
up: CONTAINERS:=
up: .env
	$(COMPOSE) up --remove-orphans$(shell source .env; if [ -z "$$DEV_MODE" -o "$$DEV_MODE" = 0 ]; then echo " -d"; fi) $(CONTAINERS) || true

.PHONY: down
down: CONTAINERS:=
down:
	$(COMPOSE) down --remove-orphans

.PHONY: build
build: CONTAINERS:=
build:
	$(COMPOSE) build --pull $(CONTAINERS)

.PHONY: shell
shell:
	$(COMPOSE) run --service-ports --use-aliases --rm backend /bin/bash

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

.PHONY: shell-nodeps
shell-nodeps:
	$(COMPOSE) run --no-deps --rm --entrypoint /bin/bash backend

.PHONY: nginx-nodeps
nginx-nodeps:
	$(COMPOSE) run --no-deps --rm --service-ports nginx

.PHONY: format-lint
format-lint:
	@$(COMPOSE) run --no-deps --rm --entrypoint /bin/sh backend -c "black . ; isort . ; flake8 ." || true
	@cd frontend ; sh -c "npm run format ; npm run lint" || true

.PHONY: verify-prod
verify-prod:
	@if [ "$(shell source .env; [ "$$DEV_MODE" -a "$$DEV_MODE" != 0 ] && echo "1")" ]; then \
		echo "Won't run with DEV_MODE = 1" ; \
		exit 1 ; \
	fi

.PHONY: deploy-pull
deploy-pull: verify-prod
	git pull --ff-only
	docker compose pull --quiet
	docker compose down --remove-orphans
	docker compose up --quiet-pull --remove-orphans --no-build --detach
	docker system prune --force --all

.PHONY: deploy-build
deploy-build: verify-prod
	git pull --ff-only
	docker compose pull --quiet --ignore-buildable
	docker compose build --pull
	docker compose down --remove-orphans
	docker compose up --quiet-pull --remove-orphans --no-build --detach
	docker system prune --force

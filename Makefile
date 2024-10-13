COMPOSE:=docker compose
SHELL:=/bin/bash
DEBUG=$(shell source .env; [ "$$DEBUG" -a "$$DEBUG" != 0 ] && echo '1')

.PHONY: up
up: CONTAINERS:=
up: .env
	$(COMPOSE) up --remove-orphans$([ -z "$$DEBUG" ] && echo ' -d') $(CONTAINERS) || true

.PHONY: down
down: CONTAINERS:=
down:
	$(COMPOSE) down --remove-orphans

.PHONY: build
build: CONTAINERS:=
build: EXTRA_BUILD_ARGS:=
build:
	$(COMPOSE) build --pull $(EXTRA_BUILD_ARGS) --build-arg "GIT_REV=$(shell git rev-parse --short=8 HEAD || echo unknown)" --build-arg "BUILD_TIME=$(shell date -u +%FT%TZ)" $(CONTAINERS)

.PHONY: build-nocache
build-nocache:
	make build "EXTRA_BUILD_ARGS=--no-cache"

.PHONY: frontend-build
frontend-build:
	$(COMPOSE) run --rm frontend-build

.PHONY: shell
shell:
	$(COMPOSE) run --service-ports --use-aliases --rm backend /bin/bash || true

.PHONY: shell-nodeps
shell-nodeps:
	$(COMPOSE) run --no-deps --rm --entrypoint /bin/bash backend || true

.PHONY: nginx-nodeps
nginx-nodeps:
	$(COMPOSE) run --no-deps --rm --service-ports nginx || true

.PHONY: lint-format
lint-format:
	@$(COMPOSE) run --no-deps --rm --entrypoint /bin/sh backend -c "black . ; isort . ; flake8 ." || true
	@cd frontend ; sh -c "npm run format ; npm run lint" || true

.PHONY: verify-prod
verify-prod:
	@if [ $(DEBUG) ]; then \
		echo "Won't run with DEBUG = 1" ; \
		exit 1 ; \
	fi

.PHONY: deploy-pull
deploy-pull: verify-prod
	git pull --ff-only
	docker compose pull --quiet
	make frontend-build
	docker compose down --remove-orphans
	docker compose up --quiet-pull --remove-orphans --no-build --detach
	docker system prune --force --all

.PHONY: deploy-build
deploy-build: verify-prod
	git pull --ff-only
	docker compose pull --quiet --ignore-buildable
	make build
	make frontend-build
	docker compose down --remove-orphans
	docker compose up --quiet-pull --remove-orphans --no-build --detach
	docker system prune --force

.PHONY: check-env
check-env:
	@for f in .env .env.sample ; do \
		sed 's/^#//' "$$f" | sed 's/^\([A-Z_]*\)=.*/\1/' > "/tmp/diff-$$f" ; \
	done ; \
	colordiff -u /tmp/diff-.env.sample /tmp/diff-.env ; \
	rm /tmp/diff-.env*

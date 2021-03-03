.PHONY: build run stop prod

CONTAINER=radio-calls
PORT=5142
TZ=$(shell cat /etc/timezone 2>/dev/null || readlink /etc/localtime | sed 's/\/var\/db\/timezone\/zoneinfo\///')

run:
	docker run -it --rm -e TZ=$(TZ) -p 127.0.0.1:$(PORT):5000 -v "$(CURDIR):/app" --name $(CONTAINER) radio-calls

ssh:
	ssh containers 'cd radio-calls; make stop' && ssh -R 5142:localhost:5142 containers

deploy:
	ssh containers 'cd radio-calls; git pull --ff-only && make prod'

prod: build stop
	docker run -itd --restart=always -e TZ=$(TZ) -p 127.0.0.1:$(PORT):5000 -e FLASK_ENV=production --name $(CONTAINER) radio-calls

stop:
	docker stop $(CONTAINER) || true
	docker rm $(CONTAINER) || true

logs:
	docker logs -f $(CONTAINER)

build:
	docker build -t $(CONTAINER) .


default:
	make dev

dev:
	rm -f YYeTsFE/.env
	git checkout docker-compose.yml
	git pull
	git submodule update --remote
	cp .env YYeTsFE/.env
	docker build -t bennythink/yyetsbot .
	cp ../docker-compose.yml ./docker-compose.yml
	docker-compose up -d

clean:
	docker rmi bennythink/yyetsbot:latest

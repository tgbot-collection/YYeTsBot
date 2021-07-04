
default:
	make dev

dev:
	rm -f YYeTsFE/.env
	git pull
	git submodule update --remote
	cp .env YYeTsFE/.env
	docker build --build-arg env=dev -t bennythink/yyetsbot .
	docker-compose up -d

clean:
	docker rmi bennythink/yyetsbot:latest
	rm -rf build
	rm -rf dist

static:
	make clean
	cd yyetsweb
	pyinstaller -F server.py
	cp dists/server ./
	cd migration
	python3 convert_to_sqlite.py
	mv yyets.sqlite ../

zip:
	zip -r yyetsweb-one-key-$(date +"%F %T").zip yyetsweb

docker:
	# production configuration
	rm -f YYeTsFE/.env
	cp .env YYeTsFE/.env
	# docker buildx create --use --name mybuilder
	docker buildx build --platform=linux/amd64,linux/arm64 -t bennythink/yyetsbot  . --push
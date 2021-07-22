
default:
	make dev

update:
	git pull
	git submodule update --remote

dev:
	make update
	docker build --build-arg env=dev -t bennythink/yyetsbot .
	docker-compose up -d

clean:
	docker rmi bennythink/yyetsbot:latest
	rm -rf YYeTsFE/build
	rm -rf YYeTsFE/dist

static:
	make clean
	cd yyetsweb
	pyinstaller -F server.spec
	cp dists/server ./
	cd migration
	python3 convert_to_sqlite.py
	mv yyets.sqlite ../

zip:
	zip -r yyetsweb-one-key-$(date +"%F %T").zip yyetsweb

docker:
	# production configuration
	cp .env YYeTsFE/.env
	# docker buildx create --use --name mybuilder
	docker buildx build --platform=linux/amd64,linux/arm64 -t bennythink/yyetsbot  . --push

prod:
	make update
	cp .env YYeTsFE/.env
	docker build -t bennythink/yyetsbot .

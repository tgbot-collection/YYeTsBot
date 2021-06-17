
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

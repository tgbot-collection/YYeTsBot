OS = darwin linux windows
ARCH = amd64 arm64
WEB := $(shell cd yyetsweb;pwd)
DATE:=$(shell date +"%Y-%m-%d %H:%M:%S")
update:
	git pull
	git submodule update --remote

docker-dev:
	make update
	docker build --build-arg env=dev -t bennythink/yyetsbot .
	docker-compose up -d

docker:
	# production configuration
	cp .env YYeTsFE/.env
	# docker buildx create --use --name mybuilder
	docker buildx build --platform=linux/amd64,linux/arm64 -t bennythink/yyetsbot  . --push


clean:
	docker rmi bennythink/yyetsbot:latest || true
	rm -rf YYeTsFE/build
	rm -rf YYeTsFE/dist

	@rm -rf yyetsweb/builds
	@rm -f yyetsweb/assets.go

current:
	echo "Installing dependencies..."
	cd $(WEB);go get -u github.com/go-bindata/go-bindata/...
	echo "Build static files..."
	make asset
	echo "Build current platform executable..."
	cd $(WEB); go build .;

asset:
	cd $(WEB);go get -u github.com/go-bindata/go-bindata/... ;go install github.com/go-bindata/go-bindata/...
	cd $(WEB)/templates;~/go/bin/go-bindata -o assets.go ./...
	mv yyetsweb/templates/assets.go yyetsweb/assets.go

frontend:
	cd YYeTsFE; yarn && yarn run release
	cp -R YYeTsFE/build/* yyetsweb/templates/

all:
	make clean
	make frontend
	make asset
	@echo "Build all platform executables..."
	@for o in $(OS) ; do            \
        		for a in $(ARCH) ; do     \
        		  	echo "Building $$o-$$a..."; \
        		  	if [ "$$o" = "windows" ]; then \
                    	cd $(WEB);CGO_ENABLED=0 GOOS=$$o GOARCH=$$a go build -ldflags="-s -w -X 'main.buildTime=$(DATE)'" -o builds/yyetsweb-$$o-$$a.exe .;    \
                    else \
        				cd $(WEB);CGO_ENABLED=0 GOOS=$$o GOARCH=$$a go build -ldflags="-s -w -X 'main.buildTime=$(DATE)'" -o builds/yyetsweb-$$o-$$a .;    \
        			fi; \
        		done   \
        	done

	@make universal
	@make checksum


checksum: yyetsweb/builds/*
	@echo "Generating checksums..."
	if [ "$(shell uname)" = "Darwin" ]; then \
		shasum -a 256 $^ >>  $(WEB)/builds/checksum-sha256sum.txt ;\
	else \
		sha256sum  $^ >> $(WEB)/builds/checksum-sha256sum.txt; \
	fi


universal:
	@echo "Building macOS universal binary..."
	docker run --rm -v $(WEB)/builds:/app/ bennythink/lipo-linux -create -output \
		yyetsweb-darwin-universal \
		yyetsweb-darwin-amd64    yyetsweb-darwin-arm64

	file $(WEB)/builds/yyetsweb-darwin-universal

release:
	git tag $(shell git rev-parse --short HEAD)
	git push --tags

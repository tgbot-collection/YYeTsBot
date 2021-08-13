default:
	echo "Installing dependencies..."
	go get -u github.com/go-bindata/go-bindata/...
	echo "Build static files..."
	make asset
	echo "Build current platform executable..."
	go build  .


asset:
	cd templates; go-bindata  -o assets.go resource.html index.html search.html js/... css/... fonts/... img/...
	mv templates/assets.go ./

dev:
	go-bindata  -o assets.go index.html


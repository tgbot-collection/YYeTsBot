default:
	echo "Installing dependencies..."
	go get -u github.com/go-bindata/go-bindata/...
	echo "Build static files..."
	make asset
	echo "Build current platform executable..."
	go build  .


asset:
	go-bindata  -o assets.go resource.html index.html search.html js/... css/... fonts/... img/...

dev:
	go-bindata  -o assets.go index.html


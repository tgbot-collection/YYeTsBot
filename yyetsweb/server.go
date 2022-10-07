package main

import (
	"archive/zip"
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/gin-gonic/gin"
	_ "github.com/glebarez/go-sqlite"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
)

const dbFile = "yyets_sqlite.db"

func main() {
	downloadDB()
	banner := `
    ▌ ▌ ▌ ▌     ▀▛▘
    ▝▞  ▝▞  ▞▀▖  ▌  ▞▀▘
     ▌   ▌  ▛▀   ▌  ▝▀▖
     ▘   ▘  ▝▀▘  ▘  ▀▀ 
                        
	Lazarus came back from the dead. By @Bennythink
	http://127.0.0.1:8888/
`
	r := gin.Default()
	r.GET("/api/resource", entrance)
	r.GET("/js/*f", bindataStaticHandler)
	r.GET("/css/*f", bindataStaticHandler)
	r.GET("/fonts/*f", bindataStaticHandler)
	r.GET("/img/*f", bindataStaticHandler)
	r.GET("/index.html", bindataStaticHandler)
	r.GET("/search.html", bindataStaticHandler)
	r.GET("/resource.html", bindataStaticHandler)
	r.GET("/", bindataStaticHandler)

	fmt.Printf(banner)
	_ = r.Run("localhost:8888") // listen and serve on 0.0.0.0:8080 (for windows "localhost:8080")
}

func bindataStaticHandler(c *gin.Context) {
	path := c.Request.RequestURI[1:]
	if strings.Contains(path, "search.html") || strings.Contains(path, "resource.html") {
		path = strings.Split(path, "?")[0]
	}

	data, err := Asset(path)
	if err != nil {
		// Asset was not found.
		index, _ := Asset("index.html")
		_, _ = c.Writer.Write(index)
	}
	// Write asset

	if strings.Contains(path, ".css") {
		c.Writer.Header().Add("content-type", "text/css")

	} else if strings.Contains(path, ".js") {
		c.Writer.Header().Add("content-type", "text/javascript")

	} else if strings.Contains(path, ".html") {
		c.Writer.Header().Add("content-type", "text/html")

	} else if strings.Contains(path, ".png") {
		c.Writer.Header().Add("content-type", "image/png")
	}

	_, _ = c.Writer.Write(data)

	// Handle errors here too and cache headers
}

type basicInfo struct {
	Id        int    `json:"id"`
	Cnname    string `json:"cnname"`
	Enname    string `json:"enname"`
	Aliasname string `json:"aliasname"`
}
type InnerInfo struct {
	Info basicInfo `json:"info"`
}

type ItemData struct {
	Data InnerInfo `json:"data"`
}

func search(c *gin.Context) {
	keyword, _ := c.GetQuery("keyword")
	keyword = "%" + keyword + "%"
	db, _ := sql.Open("sqlite", dbFile)

	rows, _ := db.Query("SELECT resource_id, cnname, enname, aliasname FROM yyets "+
		"WHERE cnname LIKE ? or enname LIKE ? or aliasname LIKE ?", keyword, keyword, keyword)
	var finaldata []ItemData
	for rows.Next() {
		var t ItemData
		_ = rows.Scan(&t.Data.Info.Id, &t.Data.Info.Cnname, &t.Data.Info.Enname, &t.Data.Info.Aliasname)
		finaldata = append(finaldata, t)
	}
	c.JSON(200, gin.H{
		"data": finaldata,
	})
}

func resource(c *gin.Context) {
	id, _ := c.GetQuery("id")
	db, _ := sql.Open("sqlite", dbFile)

	rows, _ := db.Query("SELECT data FROM yyets WHERE resource_id=?", id)
	var result string
	for rows.Next() {
		_ = rows.Scan(&result)
	}
	var data map[string]interface{}
	json.Unmarshal([]byte(result), &data)

	c.JSON(200, data)
}

func entrance(c *gin.Context) {

	var _, keyword = c.GetQuery("keyword")
	var _, id = c.GetQuery("id")

	if keyword {
		search(c)
	} else if id {
		resource(c)
	} else {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Bad request",
		})
	}

}

func downloadDB() {
	if _, err := os.Stat("yyets_sqlite.db"); err == nil {
		log.Println("File already exists")
		return
	}

	log.Println("Downloading database file...")
	var downloadUrl = "https://yyets.dmesg.app/dump/yyets_sqlite.zip"
	resp, _ := http.Get(downloadUrl)
	file, _ := os.Create("yyets_sqlite.zip")
	_, _ = io.Copy(file, resp.Body)
	_ = resp.Body.Close()
	_ = file.Close()

	log.Println("Download complete, extracting...")
	archive, _ := zip.OpenReader("yyets_sqlite.zip")
	for _, f := range archive.File {
		dstFile, _ := os.OpenFile(f.Name, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		fileInArchive, _ := f.Open()
		_, _ = io.Copy(dstFile, fileInArchive)
		_ = dstFile.Close()
		_ = fileInArchive.Close()
	}

	log.Println("Extraction complete, cleaning up...")
	_ = os.Remove("yyets_sqlite.zip")
}

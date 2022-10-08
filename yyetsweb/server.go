package main

import (
	"archive/zip"
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/gin-gonic/gin"
	_ "github.com/glebarez/go-sqlite"
	log "github.com/sirupsen/logrus"
	"io"
	"net/http"
	"os"
	"path"
	"strings"
)

const dbFile = "yyets_sqlite.db"

var (
	buildTime string
	db, _     = sql.Open("sqlite", dbFile)
)

type basicInfo struct {
	Id        int    `json:"id"`
	Cnname    string `json:"cnname"`
	Enname    string `json:"enname"`
	Aliasname string `json:"aliasname"`
}

type Announcement struct {
	Username string `json:"username"`
	Date     string `json:"date"`
	Content  string `json:"content"`
}

func bindataStaticHandler(c *gin.Context) {
	c.Status(http.StatusOK)
	path := c.Request.RequestURI[1:]
	if strings.Contains(path, "search.html") || strings.Contains(path, "resource.html") {
		path = strings.Split(path, "?")[0]
	}
	fmt.Println(path)
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
	} else if strings.Contains(path, ".svg") {
		c.Writer.Header().Add("content-type", "image/svg+xml")
	} else if strings.Contains(path, ".jpg") {
		c.Writer.Header().Add("content-type", "image/jpeg")
	} else if strings.Contains(path, ".ico") {
		c.Writer.Header().Add("content-type", "image/x-icon")
	} else if strings.Contains(path, ".gif") {
		c.Writer.Header().Add("content-type", "image/gif")
	}

	_, _ = c.Writer.Write(data)

	// Handle errors here too and cache headers
}

func search(c *gin.Context) {
	keyword, _ := c.GetQuery("keyword")
	keyword = "%" + keyword + "%"

	rows, _ := db.Query("SELECT resource_id, cnname, enname, aliasname FROM yyets "+
		"WHERE cnname LIKE ? or enname LIKE ? or aliasname LIKE ?", keyword, keyword, keyword)
	var searchResult []basicInfo
	for rows.Next() {
		var t basicInfo
		_ = rows.Scan(&t.Id, &t.Cnname, &t.Enname, &t.Aliasname)
		searchResult = append(searchResult, t)
	}
	c.JSON(200, gin.H{
		"data":    searchResult,
		"extra":   []string{},
		"comment": []string{},
	})
}

func resource(c *gin.Context) {
	id, _ := c.GetQuery("id")
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

func announcement(c *gin.Context) {

	c.JSON(http.StatusOK, gin.H{
		"data": []Announcement{{
			Username: "Benny",
			Date:     buildTime,
			Content:  "YYeTs一键运行包 https://yyets.dmesg.app/。",
		}},
	})
}

func newest(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"data": []string{},
	})
}

func douban(c *gin.Context) {
	var resourceId, _ = c.GetQuery("resource_id")
	var requestType, _ = c.GetQuery("type")

	type Image struct {
		PosterLink string `json:"posterLink"`
	}
	rows, _ := db.Query("SELECT douban,image FROM yyets WHERE resource_id=?", resourceId)
	var doubanInfo string
	var doubanPoster []byte
	for rows.Next() {
		_ = rows.Scan(&doubanInfo, &doubanPoster)
	}
	if doubanInfo == "" {
		var image Image
		log.Warnf("Douban resource not found, requesting to main site %s...", resourceId)
		resp, _ := http.Get("https://yyets.dmesg.app" + c.Request.URL.String())
		body, _ := io.ReadAll(resp.Body)
		doubanInfo = string(body)
		json.Unmarshal(body, &image)
		resp, _ = http.Get(image.PosterLink)
		body, _ = io.ReadAll(resp.Body)
		_, _ = db.Exec("UPDATE yyets SET douban=?,image=? WHERE resource_id=?", doubanInfo, body, resourceId)
	}

	if requestType == "image" {
		c.Writer.Header().Add("content-type", "image/jpeg")
		_, _ = c.Writer.Write(doubanPoster)
	} else {
		c.String(http.StatusOK, doubanInfo)
	}

}

func queryTop(area string) []gin.H {
	var sqlQuery string
	if area == "ALL" {
		sqlQuery = "SELECT resource_id, cnname, enname, aliasname FROM yyets  order by views desc limit 15"
	} else {
		sqlQuery = "SELECT resource_id, cnname, enname, aliasname FROM yyets where area=? order by views desc limit 15"
	}
	rows, _ := db.Query(sqlQuery, area)
	var finaldata []gin.H
	for rows.Next() {
		var t basicInfo
		_ = rows.Scan(&t.Id, &t.Cnname, &t.Enname, &t.Aliasname)
		finaldata = append(finaldata, gin.H{"data": gin.H{"info": t}})
	}
	return finaldata
}

func top(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"ALL": queryTop("ALL"),
		"US":  queryTop("美国"),
		"JP":  queryTop("日本"),
		"KR":  queryTop("韩国"),
		"UK":  queryTop("英国"),
		"class": gin.H{
			"ALL": gin.H{"$regex": ".*"},
			"US":  "美国",
			"JP":  "日本",
			"KR":  "韩国",
			"UK":  "英国",
		},
	})
}

func downloadDB() {
	if _, err := os.Stat(dbFile); err == nil {
		log.Warningln("Database file already exists")
		return
	}

	log.Infoln("Downloading database file...")
	var downloadUrl = "https://yyets.dmesg.app/dump/yyets_sqlite.zip"
	resp, _ := http.Get(downloadUrl)
	file, _ := os.Create("yyets_sqlite.zip")
	_, _ = io.Copy(file, resp.Body)
	_ = resp.Body.Close()
	_ = file.Close()

	log.Infoln("Download complete, extracting...")
	archive, _ := zip.OpenReader("yyets_sqlite.zip")
	for _, f := range archive.File {
		var targetPath = path.Clean(f.Name)
		dstFile, _ := os.OpenFile(targetPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		fileInArchive, _ := f.Open()
		_, _ = io.Copy(dstFile, fileInArchive)
		_ = dstFile.Close()
		_ = fileInArchive.Close()
	}

	log.Infoln("Extraction complete, cleaning up...")
	_ = os.Remove("yyets_sqlite.zip")
}

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
	r.GET("/api/announcement", announcement)
	r.GET("/api/comment/newest", newest)
	r.GET("/api/resource/latest", newest)
	r.GET("/api/captcha", newest)
	r.GET("/api/comment", newest)
	r.GET("/api/douban", douban)
	r.GET("/api/top", top)
	r.GET("/js/*f", bindataStaticHandler)
	r.GET("/css/*f", bindataStaticHandler)
	r.GET("/fonts/*f", bindataStaticHandler)
	r.GET("/img/*f", bindataStaticHandler)
	//r.GET("/index.html", bindataStaticHandler)
	//r.GET("/search.html", bindataStaticHandler)
	r.GET("/resource.html", bindataStaticHandler)
	r.GET("/", bindataStaticHandler)
	r.GET("/index.css", bindataStaticHandler)
	r.GET("/svg/*f", bindataStaticHandler)

	r.NoRoute(bindataStaticHandler)

	fmt.Printf(banner)
	_ = r.Run("localhost:8888") // listen and serve on 0.0.0.0:8080 (for windows "localhost:8080")
}

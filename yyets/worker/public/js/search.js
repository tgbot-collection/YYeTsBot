const baseURL = "https://yyets.click/";
const resourceURL = baseURL + "resource.html?id=";
const indexURL = baseURL + "?id=index";

// const indexURL = "css/index.json"
const cf_url = "yyets.yyetsdb.workers.dev"
// redirect to baseURL
if (document.URL.includes(cf_url)) {
    location.href = baseURL
}

function loadJSON(path, success, error) {
    let xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function () {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            if (xhr.status === 200) {
                if (success)
                    success(JSON.parse(xhr.responseText));
            } else {
                if (error)
                    error(xhr);
            }
        }
    };
    xhr.open("GET", path, true);
    xhr.send();
}

function doSearch() {
    let search = document.getElementById("kw");
    if (kw !== "undefined") {
        search.value = kw;
    }

    let data = JSON.parse(localStorage.getItem("index"));
    let div = document.getElementById("tv");
    let found = false
    for (let v in data) {
        if (v.toLowerCase().indexOf(kw) !== -1) {
            found = true
            let name = v.replace(/\n/g, " ")
            let id = data[v]
            let html = `<h3><a style="text-decoration: none;color: cornflowerblue" href="${resourceURL}${id}">${name}</a></h3>`;
            let backup = div.innerHTML;
            div.innerHTML = backup + html;
        }
    }
    if (found === false) {
        div.innerHTML = `<h2>没有搜索到结果 (ノへ￣、)</h2>`
    }
}

function reloadIndex() {
    loadJSON(indexURL,
        function (data) {
            let jsonText = JSON.stringify(data);
            localStorage.setItem("index", jsonText);

        },
        function (xhr) {
            console.error(xhr);
        });

}

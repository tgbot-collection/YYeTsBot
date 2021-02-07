# Cloudflare Worker部署方式
**This worker is deprecated. No further updates from now on.**

## 1. 安装wrangler等工具
[Cloudflare Docs](https://developers.cloudflare.com/workers/cli-wrangler)
## 2. 导入数据到MySQL

## 3. 生成KV数据
参考 `BagAndDrag/cfkv.py`

## 4. 导入数据
```shell
cd kv_data
bash bulk.sh
```
**注意，Cloudflare KV免费版有每日1000条写入的限制**

## 4. 配置代码
* 修改`worker/public/js/search.js`中的`baseURL`为你的URL
* 如绑定自定义域名，还需要修改`worker/workers-site/index.js`中的`Access-Control-Allow-Origin`为你的域名

## 5.  发布到Worker Site
配置 `wrangler.toml`，修改`account_id`, `kv_namespaces`等，然后：
```shell
wrangler publish
```
就可以了。
# bot开发手册

## 添加新的资源网站

欢迎各位开发提交新的资源网站！方法非常简单，重写 `BaseFansub`，实现`search_preview`和`search_result`，按照约定的格式返回数据。

然后把类名字添加到 `FANSUB_ORDER` 就可以了！是不是很简单！

## bot无响应

有时不知为何遇到了bot卡死，无任何反馈。😂~~这个时候需要client api了~~😂

原因找到了，是因为有时爬虫会花费比较长的时间，然后pytelegrambotapi默认只有两个线程，那么后续的操作就会被阻塞住。

临时的解决办法是增加线程数量，长期的解决办法是使用celery分发任务。

# 网站开发手册

## 接口列表

* `/api/resource?id=3` GET 获取id=3的资源
* `/api/resource?kw=逃避` GET 搜索关键词
* `/api/top` GET 获取大家都在看
* `/api/name` GET 所有剧集名字
* `/api/name?human=1` GET 人类可读的方式获取所有剧集名字
* `/api/metrics` GET 获取网站访问量

## 防爬

### 1. referer

网站使用referer验证请求

### 2. 加密headers

使用headers `ne1` 进行加密验证，详细信息可以[参考这里](https://t.me/mikuri520/726)

### 3. rate limit

404的访问会被计数，超过10次会被拉入黑名单，持续3600秒，再次访问会持续叠加。
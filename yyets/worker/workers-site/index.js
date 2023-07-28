import {getAssetFromKV} from '@cloudflare/kv-asset-handler'

/**
 * The DEBUG flag will do two things that help during development:
 * 1. we will skip caching on the edge, which makes it easier to
 *    debug.
 * 2. we will return an error message on exception in your Response rather
 *    than the default 404.html page.
 */
const DEBUG = false

addEventListener('fetch', event => {
    try {
        event.respondWith(handleEvent(event))
    } catch (e) {
        if (DEBUG) {
            return event.respondWith(
                new Response(e.message || e.toString(), {
                    status: 500,
                }),
            )
        }
        event.respondWith(new Response('Internal Error', {status: 500}))
    }
})

async function handleEvent(event) {
    const url = event.request.url
    let options = {}
    let resourceId = url.split("id=")[1];
    // we have valid id=10004 and the page is not resource.html
    if (resourceId !== undefined && url.indexOf("resource.html") === -1) {
        const value = await yyets.get(resourceId)
        if (value === null) {
            return new Response("resource not found", {status: 404})
        }

        if (resourceId !== "index") {
            // be aware of 1000 put for free tier
            await update_downloads(value)
        }

        return new Response(value, {
            headers: {
                "content-type": "application/json;charset=UTF-8",
                "Access-Control-Allow-Origin": "https://yyets.click"
            },
        })

    }

    /**
     * You can add custom logic to how we fetch your assets
     * by configuring the function `mapRequestToAsset`
     */
    // options.mapRequestToAsset = handlePrefix(/^\/docs/)

    try {
        if (DEBUG) {
            // customize caching
            options.cacheControl = {
                bypassCache: true,
            }
        }

        const page = await getAssetFromKV(event, options)

        // allow headers to be altered
        const response = new Response(page.body, page)

        response.headers.set('X-XSS-Protection', '1; mode=block')
        response.headers.set('X-Content-Type-Options', 'nosniff')
        response.headers.set('X-Frame-Options', 'DENY')
        response.headers.set('Referrer-Policy', 'unsafe-url')
        response.headers.set('Feature-Policy', 'none')

        return response

    } catch (e) {
        // if an error is thrown try to serve the asset at 404.html
        if (!DEBUG) {
            try {
                let notFoundResponse = await getAssetFromKV(event, {
                    mapRequestToAsset: req => new Request(`${new URL(req.url).origin}/404.html`, req),
                })

                return new Response(notFoundResponse.body, {...notFoundResponse, status: 404})
            } catch (e) {
            }
        }

        return new Response(e.message || e.toString(), {status: 500})
    }
}

async function update_downloads(value) {
    // value is string
    let obj = JSON.parse(value);
    let targetID = obj.data.info.id.toString();
    let intView = parseInt(obj.data.info.views)
    obj.data.info.views = (intView + 1).toString()

    let increasedData = JSON.stringify(obj)
    await yyets.put(targetID, increasedData)
}

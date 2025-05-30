from aiohttp import web, RequestInfo, ClientSession
import aiohttp
import json
import random
import re
import requests
import aiohttp_jinja2
import jinja2
from pathlib import Path

DOMAIN = "https://foxgirls.club/"

here = Path(__file__).resolve().parent
db = []
with open('db.json', 'r') as file:
    db = json.load(file)

async def get_image (type, hide_loli, only_loli):
    if type == "nsfw":
        choice = random.choice(list(db["nsfw"].items()))
    elif type == "sfw":
        choice = random.choice(list(db["sfw"].items()))
    else:
        selected_sub_dict_key = random.choice(list(db.keys()))
        selected_sub_dict = db[selected_sub_dict_key]
        choice = random.choice(list(selected_sub_dict.items()))
    if hide_loli and choice[1]["is_loli"]:
        return await get_image(type, hide_loli, only_loli)
    elif only_loli and not choice[1]["is_loli"]:
        return await get_image(type, hide_loli, only_loli)
    else:
        return choice


def handle_image(request):
    hash_match = re.match(r'^/images/(.*)$', request.path)
    if not hash_match:
        return web.Response(
            text="Invalid request",
            status=400,
            headers={'Access-Control-Allow-Origin': '*'}
        )

    image_hash = hash_match.group(1)

    if image_hash in db['nsfw']:
        image_url = db['nsfw'][image_hash]["link"]
    elif image_hash in db['sfw']:
        image_url = db['sfw'][image_hash]["link"]
    else:
        return web.Response(
            text="Invalid request",
            status=400,
            headers={'Access-Control-Allow-Origin': '*'}
        )

    try:
        response = requests.get(image_url)

        if response.status_code != 200:
            return web.Response(
                text=f"Failed to fetch image (status {response.status_code})",
                status=response.status_code,
                headers={'Access-Control-Allow-Origin': '*'}
            )

        return web.Response(
            body=response.content,
            status=200,
            content_type=response.headers.get('Content-Type', 'application/octet-stream'),
            headers={
                'Access-Control-Allow-Origin': '*'
            }
        )

    except requests.RequestException as e:
        return web.json_response({'error': f"Error {e}"}, status=500)


async def handle_api_get(request: RequestInfo):
    hide_loli = request.url.query.get("hide_loli")
    only_loli = request.url.query.get("only_loli")
    danb = request.url.query.get("original_booru_data")
    type = re.match(r'^/api/(.*)$', request.path)
    type = type.group(1)
    if type == "endpoints":
        resp = {}
        resp['endpoints'] = {
            'sfw imagess': DOMAIN+"api/sfw",
            'nsfw images': DOMAIN+"api/nsfw",
            "sfw+nsfw images": DOMAIN+"api/"
        }
        resp["query parameters"] = {
            'Do not include loli images': "hide_loli=true"
        }
        return web.json_response(resp, status=200, headers={'Access-Control-Allow-Origin': '*'})
    img = await get_image(type, hide_loli, only_loli)
    if danb:
        return web.json_response(img[1], status=200, headers={'Access-Control-Allow-Origin': '*'})
    else:
        return web.json_response({'url':DOMAIN+"images/"+img[0]}, status=200, headers={'Access-Control-Allow-Origin': '*'})

@aiohttp_jinja2.template('/templates/index.html')
async def handle_index(request: RequestInfo):
    type = re.match(r'^/(.*)$', request.path)
    type = type.group(1)
    hide_loli = True if type == "nsfw" else False
    if type != "nsfw": type = "sfw"
    img = await get_image(type, hide_loli, False)
    vars = {
    'img_url': "/images/"+img[0],
    'rating': "NSFW" if type == "sfw" else "SFW",
    'r_link': "nsfw" if type == "sfw" else "sfw",
    'domain': DOMAIN
    }
    return vars






app = web.Application()
app.add_routes([web.get("/images/{tail:.*}", handle_image)])
app.add_routes([web.get("/api/{tail:.*}", handle_api_get)])
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(here)))
app.add_routes([web.get("/{tail:(sfw|nsfw)?(?:/.*)?}", handle_index)])
app.router.add_static('/static/', path='static', name='static')
favicon_path = Path('static/images/favicon.ico')
app.router.add_get('/favicon.ico', lambda _: web.FileResponse(favicon_path))

if __name__ == "__main__":
    web.run_app(app, port=3010)
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import transmissionrpc
import base64

app = FastAPI()
templates = Jinja2Templates(directory="templates")

TRANSMISSION_HOST = "transmission"
TRANSMISSION_PORT = 9091

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload(
    request: Request,
    torrents: list[UploadFile] = File(...),
    download_dir: str = Form(...),
    filters: str = Form(...)
):
    import time
    import transmissionrpc

    for _ in range(5):
        try:
            client = transmissionrpc.Client(
                "transmission",
                9091
            )
            break
        except Exception:
            time.sleep(2)
    else:
        raise RuntimeError("Transmission not available")

    filter_strings = [f.strip().lower() for f in filters.splitlines() if f.strip()]
    results = []

    for torrent in torrents:
        torrent_bytes = await torrent.read()
        torrent_b64 = base64.b64encode(torrent_bytes).decode("ascii")

        t = client.add_torrent(
            torrent_b64,
            download_dir=download_dir,
            paused=True
        )       


        torrent_obj = client.get_torrent(t.id)
        files = torrent_obj.files()

        all_file_ids = list(files.keys())
        client.change_torrent(t.id, files_unwanted=all_file_ids)

        wanted_ids = []
        for file_id, file_info in files.items():
            name = file_info["name"].lower()
            if any(f in name for f in filter_strings):
                wanted_ids.append(file_id)

        if wanted_ids:
            client.change_torrent(t.id, files_wanted=wanted_ids)

        client.start_torrent(t.id)

        results.append({
            "torrent": torrent.filename,
            "selected_files": len(wanted_ids)
        })

    return RedirectResponse(
    url="http://127.0.0.1:9091",
    status_code=303
)
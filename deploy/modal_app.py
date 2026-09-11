import modal

APP_NAME = "songbird"
ALLOWED_ORIGINS = "https://songbbird.vercel.app"


def _download_model():
    from muq import MuQ
    MuQ.from_pretrained("OpenMuQ/MuQ-large-msd-iter")


image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("ffmpeg")
    .pip_install_from_requirements("requirements.txt")
    .pip_install("yt-dlp[default]", extra_options="--pre --upgrade")
    .run_function(_download_model)
    .add_local_python_source("songbird", "server")
)

catalog_vol = modal.Volume.from_name("songbird-catalog", create_if_missing=True)

app = modal.App(APP_NAME)


@app.function(
    image=image,
    volumes={"/data/catalog": catalog_vol},
    cpu=4,
    memory=6144,
    timeout=300,
    scaledown_window=300,
    max_containers=3,
)
@modal.concurrent(max_inputs=2)
@modal.asgi_app()
def web():
    import os
    os.environ["SONGBIRD_CATALOG"] = "/data/catalog"
    os.environ["SONGBIRD_ALLOWED_ORIGINS"] = ALLOWED_ORIGINS
    from server.app import app as fastapi_app
    return fastapi_app

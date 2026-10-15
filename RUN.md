# How to run Jewellery Image Studio

## Quickest: one command on your computer

You need **Python 3.11 or newer** ([python.org/downloads](https://www.python.org/downloads/); on Windows, tick "Add Python to PATH" during install) and **git**.

```bash
git clone https://github.com/abhiydv-design/Lustre.git
cd Lustre
python start.py
```

On Mac or Linux, use `python3` if `python` isn't found.

The first run takes a few minutes: it creates a private Python environment, installs everything, and writes `backend/.env` with test settings. Later runs start in about 2 seconds. Your browser opens the app, and the window shows:

```
  App on this computer:  http://localhost:8000/app
  Team console:          http://localhost:8000/admin   token: 3f9c…
  API documentation:     http://localhost:8000/docs
  Stop:                  Ctrl+C
```

**Test mode** (the default) needs no accounts or keys:
- **Backgrounds** are plain gradients, not AI scenes.
- **Sign-in codes** appear on screen ("Test mode code: 123456").
- **Buying credits** completes instantly with no real payment.

## On your phone

Install Cloudflare's free tunnel tool once:

- **Mac:** `brew install cloudflared`
- **Windows:** `winget install --id Cloudflare.cloudflared`

Then run:

```bash
python start.py --phone
```

It prints a link like `https://something.trycloudflare.com/app`; open it on your phone. The camera, sharing to WhatsApp and downloads all need this https link. Anyone with the link can use it while the window is open, so press Ctrl+C when you're done.

## Real AI backgrounds

1. Create an account at [replicate.com](https://replicate.com), add billing, and copy your API token.
2. Open `backend/.env` and change the three provider lines to:
   ```
   CUTOUT_PROVIDER=rembg
   SCENE_PROVIDER=replicate
   UPSCALE_PROVIDER=replicate
   ```
3. Paste your token after `REPLICATE_API_TOKEN=`.
4. Run `python start.py` again. It installs the AI packages by itself.

Notes:
- **First image:** it's slower, because the cut-out model downloads once (about 1 GB).
- **What costs money:** White and Soft grey don't use AI and cost nothing. Marble and Warm beige call Replicate.
- **If an AI image fails:** the model settings were written from memory and haven't been run against Replicate yet. The jeweller's credit is returned automatically; send the error from the terminal window and it can be fixed.

## Other commands

| Command | What it does |
|---|---|
| `python start.py --test` | Runs the 34 automated tests (about 4 minutes) |
| `python start.py --setup` | Installs and creates `backend/.env`, then stops |
| `python start.py --port 8001` | Uses another port if 8000 is busy |
| `python start.py --no-browser` | Doesn't open the browser |

To start completely fresh, stop the app and delete `backend/data`, which holds all products, photos and accounts.

## With Docker (alternative)

```bash
python start.py --setup        # optional: creates backend/.env with your settings
docker compose up --build      # then open http://localhost:8000/app
```

Data is kept in a Docker volume between restarts. The Docker files haven't been built or run yet (Docker wasn't available where they were written), so if the build fails, send the error.

## Online for real jewellers (Render)

`render.yaml` sets the app up on [render.com](https://render.com) with an https address and a disk for photos:

1. On Render: **New → Blueprint**, then connect the GitHub repo.
2. Fill in the values it asks for: `ADMIN_TOKENS`, `REPLICATE_API_TOKEN` and pack prices.
3. Deploy. Your address will look like `https://jewellery-image-studio.onrender.com/app`.

The disk needs a paid instance, a few dollars a month. These field names follow Render's blueprint format; if Render flags one, adjust it in the dashboard.

**Before sharing the link widely:** SMS isn't connected yet, so test mode shows the sign-in code on screen. That means anyone could sign in as any phone number. That's fine for a small, supervised pilot with jewellers you know. Before a public launch, connect an SMS gateway (`backend/app/sms.py`; Indian SMS needs DLT registration) and set `DEV_MODE=0`.

## Something not working?

| Problem | Fix |
|---|---|
| `python` not found | Install Python 3.11+ from python.org; on Mac/Linux try `python3` |
| "port already in use" | `python start.py --port 8001` |
| Install fails | Delete `backend/.venv` and run `python start.py` again |
| Phone link doesn't appear | Check `cloudflared` is installed: `cloudflared --version` |
| Anything else | Copy the terminal output and send it |

# Vacancy Board — Railway PSUs, Metro Corporations, Railway Board

Checks every source once each morning at **07:00 IST**, works out what is new,
and sends it to Telegram, e-mail and WhatsApp. Also rebuilds a web dashboard
you can open on a laptop or phone.

It runs on GitHub's servers, not on your machine. Nothing needs to be left
switched on. It costs nothing.

---

## What it tracks

**PESB — parsed properly.** Every board-level CPSE vacancy, with organisation,
post, the date the post falls vacant, and the application deadline including
the 3:00 PM cut-off. Filtered to railway-sector CPSEs by default: IRCON, RITES,
RVNL, RailTel, CONCOR, IRFC, IRCTC, DFCCIL, Konkan Railway, Braithwaite.

**PESB Upcoming Vacancies — withdrawn by PESB, August 2026.** This was the
more valuable half: posts falling vacant that had not been advertised yet,
often six to twelve months of notice. PESB has taken the page down — the
address now redirects to its error page and the site's menu offers only
Advertised Vacancies and Vacancies Archive. Nothing on our side can recover
it. The entry is left commented out in `config/sources.yaml`, so if they
restore the page, uncommenting four lines is the whole fix.

Advertised rows still show the date each post falls vacant, so you keep that
much notice; what is gone is sight of a post before PESB advertises it.

**27 career pages** across Railway PSUs, metro and RRTS corporations, and the
Railway Board. These publish as loose PDFs with no structure, so they are
watched for change. When a new document appears, you get the link and, where
the title carries a date, the deadline too.

ED, PD, GM, CGM and CPM posts never reach PESB — they come from this second
group.

> **The `docs/preview-demo.html` file in this bundle contains invented rows.**
> It exists only to show the layout. Every organisation, post and date in it is
> made up. The first live run writes the real board to `docs/index.html` and
> leaves the demo file alone — delete it once you have seen it.

## What it does not do

It reads what the sources publish. It cannot see a post that has not been
notified, and a deadline it reports is only as accurate as the page it came
from. **Confirm on the source before acting on anything.**

---

## Setup

Roughly forty minutes, once. Work through it in order.

### 1. GitHub account and repository

Create an account at github.com if you do not have one, then create a **public**
repository — name it anything, `vacancy-board` is fine.

Public matters for one reason: the free plan only serves web pages from public
repositories. Your credentials do **not** go into the repository — they go into
GitHub's encrypted Secrets store, which stays private either way. Nothing
personal is in these files.

If you would rather not have a repository under your own name, make a second
account with a neutral username. If you would rather keep it private, that also
works — you lose only the web dashboard; Telegram, e-mail and WhatsApp are
unaffected.

Upload every file and folder from this bundle, keeping the structure intact.

### 2. Telegram — the one to set up first

1. In Telegram, search for **@BotFather** and send `/newbot`.
2. Give it a name and a username. BotFather replies with a token that looks
   like `7891234567:AAF...`. That is `TELEGRAM_BOT_TOKEN`.
3. Search for your new bot and send it any message. It will not reply — that is
   expected, you are just opening the channel.
4. Search for **@userinfobot** and send it `/start`. It replies with your
   numeric ID. That is `TELEGRAM_CHAT_ID`.

### 3. E-mail

Gmail with two-factor authentication turned on:
myaccount.google.com → Security → App passwords → generate one for "Mail".
Use the sixteen-character password, not your account password.

```
SMTP_HOST      smtp.gmail.com
SMTP_PORT      465
SMTP_USER      you@gmail.com
SMTP_PASSWORD  the sixteen-character app password
EMAIL_TO       where the digest should land
```

For an official mail server, ask IT for the SMTP host and port — port 587 is
also handled.

### 4. WhatsApp

Two routes. The free one is **CallMeBot**: open
`callmebot.com/blog/free-api-whatsapp-messages/`, follow the two steps there —
you message their number once to authorise it, and it replies with an API key.
Set `WHATSAPP_PHONE` (with country code, no `+`, e.g. `919876543210`) and
`CALLMEBOT_APIKEY`.

It is a free third-party service, so your messages pass through their server.
The content here is public vacancy information, so the exposure is minimal —
but you should know that it is not a Meta service.

The supported alternative is Meta's WhatsApp Cloud API: set `WHATSAPP_TOKEN`
and `WHATSAPP_PHONE_NUMBER_ID` instead and it takes precedence. It needs a Meta
Business account and is a longer setup.

WhatsApp gets a short summary, not the whole board — it is the nudge, the
dashboard is the detail.

**You can skip any channel.** If its secrets are absent, that channel stays
quiet and the others still work.

### 5. Load the credentials

Repository → **Settings** → Secrets and variables → **Actions** → **New
repository secret**, once per line you filled in above.

Then the **Variables** tab, one variable:

```
DASHBOARD_URL   https://YOUR-USERNAME.github.io/vacancy-board/
```

Optionally add `ALWAYS_NOTIFY` = `true` if you want a message every morning
even when nothing has changed. Left off, silence means nothing new.

### 6. Turn on the dashboard

Settings → **Pages** → Source: *Deploy from a branch* → Branch: `main`,
folder: **`/docs`** → Save. The address appears after the first run.

### 7. First run

**Actions** tab → *Daily vacancy check* → **Run workflow**.

Two things about the first run:

- It sets a baseline for the watched pages, so it reports no page changes.
  PESB results come through straight away.
- Some of the 27 career-page addresses are marked `verify: true` in
  `config/sources.yaml` — those are my best reading of each site's structure
  and a few will have moved. The run lists every unreachable source at the
  bottom of the message and the dashboard. Open those sites, find the real
  careers page, correct the URL in the config file, commit. Ten minutes,
  once.

After that it runs itself daily.

---

## Reading the board

A signal aspect on each row carries the urgency:

| | |
|---|---|
| 🔴 red | deadline within 7 days |
| 🟡 amber | open, closing within a month |
| 🟢 green | open, or a vacancy date still some way off |
| ⚪ white | a notice with no machine-readable date — open it |

The dashboard groups these into **Closing soon**, **Open**, **Upcoming
vacancies** and **Recent notices**, and there is a `vacancies.csv` alongside it
that opens straight into Excel.

## Adjusting it

Everything tunable is in `config/sources.yaml`:

- `railway_cpse_only: false` — receive every board-level CPSE vacancy PESB
  advertises, not just railway ones
- `closing_soon_days` — how early the red aspect appears
- `post_keywords` — which designations to report
- `watched:` — add or remove a website

To change the time, edit the `cron` line in
`.github/workflows/daily.yml`. It is in UTC: `30 1 * * *` is 07:00 IST.
GitHub sometimes runs scheduled jobs five to twenty minutes late.

## Running it from this machine

The scheduled cloud run keeps working on its own — this is in addition to it,
for when you want the complete picture.

**Why you would.** GitHub's runners sit outside India and eight of the
twenty-eight sources refuse them, including *the PESB feed* — the only source
that yields properly parsed posts with deadlines. `indianrailways.gov.in`
and MRVC refuse the connection outright; PESB, RVNL, NHSRCL and MPMRCL time
out; Konkan fails TLS; PSU Connect returns 403. A run from an Indian
connection reaches all twenty-eight. This is not fixable in the config — the
same code and URLs work from here and fail there.

Once, to set up:

```powershell
pip install -r requirements.txt
copy .env.example .env      # then put your two Telegram values in it
```

Then:

```powershell
.\run.ps1                # full run: fetch, notify, push the board
.\run.ps1 -DryRun        # print the message, send nothing, change nothing
.\run.ps1 -CheckUrls     # just test every address in the config
.\run.ps1 -NoPush        # run and notify, but leave git alone
```

### A button instead of the terminal

The board's local server starts when you log in, so there is nothing to
launch: open **http://127.0.0.1:8765/** — worth bookmarking — and press
**Refresh now**.

```powershell
.\autostart.ps1 -Status     # is it set up, is it running
.\autostart.ps1 -Remove     # stop starting it at logon
.\autostart.ps1 -Install    # set it up again
```

It runs under `pythonw.exe`, which has no console, so nothing appears on
screen at logon or during a run. `-Install` puts one shortcut in your own
Startup folder; `-Remove` deletes it. No admin rights, no service, no
scheduled task.

If the panel ever stops appearing on the page, the server is not running.
`.\board.ps1` does the same job in a visible window with the errors on show,
and double-clicking **Vacancy Board.cmd** is the same thing without a
terminal. Either way, Ctrl+C or closing the window stops it.

The button runs the same `run.ps1`, so a press is a full run: fetch all
twenty-eight sources, notify, pull and push. **Dry run** and **Check links** are
the other two switches, and **Stop** cancels one mid-way. The log appears under
the buttons as it happens, and after a successful refresh the page reloads
itself so you are looking at the new board.

It serves the board from this machine on `127.0.0.1:8765` — the loopback
address, so nothing outside this machine can reach it, which matters because
anything that can reach it can push commits and send messages. `-Port` moves
it; `-NoOpen` skips opening the browser.

The published board on GitHub Pages does not grow a button. The page checks
whether the local server is the one serving it and stays as it is when it is
not, so the two are the same file.

`run.ps1` pulls before it runs, so it does not collide with the state the
scheduled run commits, and pushes after, so the dashboard reflects what your
machine saw. `-DryRun` restores `data/state.json` and the board files
afterwards, so it genuinely changes nothing.

The underlying commands still work if you prefer them
(`python -m src.main --dry-run` and so on), with one caveat: **state is saved
even on a dry run**, so a bare `--dry-run` consumes the "new" flags and the
next real run reports nothing. `run.ps1 -DryRun` exists to work around that.

> `python -m tests.offline_test` runs the pipeline against fixture data with
> no network. Be aware it **writes those fixtures into `data/state.json`** —
> reset the file afterwards, or run it on a scratch copy.

## Setting up a second machine

Any number of machines can have the button. They share one repository, so
each one pulls before it runs and pushes after — whichever you press Refresh
on, both boards end up saying the same thing. About fifteen minutes.

**1. Python and Git.** Install Python 3.11 or later from python.org, ticking
**Add python.exe to PATH** on the first screen — nothing works without it —
and Git from git-scm.com. Then, in PowerShell:

```powershell
python --version        # expect 3.11 or later
git --version
```

**2. The repository.** Clone it wherever you like:

```powershell
cd $HOME\Documents
git clone https://github.com/HarshLohiya/vacancy-board.git
cd vacancy-board
pip install -r requirements.txt
```

**3. The credentials.** `.env` is deliberately not in the repository — it
holds your Telegram token. Copy the file across from the first machine by
hand (USB stick, or retype it), or start from the template:

```powershell
copy .env.example .env      # then fill in the two Telegram values
```

Without it the run still works and still pushes the board; it just sends no
Telegram message.

**4. One run from the terminal, to settle Git.** The first push asks you to
sign in to GitHub, in a browser window Git opens itself. Get that out of the
way while you can see it:

```powershell
.\run.ps1
```

Do this before step 5. Once the server is running silently in the background,
a sign-in prompt has nowhere to appear and a refresh would simply fail to
push.

**5. The button.**

```powershell
.\autostart.ps1 -Install
```

Then bookmark **http://127.0.0.1:8765/** on that machine. That is it — from
then on, open the bookmark and press **Refresh now**.

Two things to expect:

- **The page is only as fresh as the last run on *that* machine.** Open the
  bookmark on the second laptop after a week away and you are looking at a
  week-old board — press Refresh and it pulls first, so it corrects itself.
  The GitHub Pages address is always current and needs nothing installed.
- **Both machines must be on an Indian connection** for the full picture, for
  the reason above. On a connection outside India a refresh still works, it
  just quietly loses eight sources including PESB.

## If it stops finding things

PESB rows are matched on the table's column *headings*, not on its layout, so a
redesign usually survives. If the headings themselves change, the log says
`no vacancy table recognised` rather than silently reporting nothing — so an
empty board with no such warning means there genuinely was nothing.

One known limitation: PESB puts a CAPTCHA on its job-description PDFs, so links
open the listing page rather than the document itself.

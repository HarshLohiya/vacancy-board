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

**PESB Upcoming Vacancies.** Posts falling vacant that have not been advertised
yet — often six to twelve months of notice. This is the more valuable half.

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

## Running it on your own machine

```bash
pip install -r requirements.txt
python -m src.main --check-urls    # test every address in the config
python -m src.main --dry-run       # full run, prints the message, sends nothing
python -m src.main                 # full run
```

`python -m tests.offline_test` exercises the whole pipeline against fixture
data with no network at all — useful for checking a config change before you
commit it.

## If it stops finding things

PESB rows are matched on the table's column *headings*, not on its layout, so a
redesign usually survives. If the headings themselves change, the log says
`no vacancy table recognised` rather than silently reporting nothing — so an
empty board with no such warning means there genuinely was nothing.

One known limitation: PESB puts a CAPTCHA on its job-description PDFs, so links
open the listing page rather than the document itself.

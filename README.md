# Shorts Automation — αυτόματο pipeline για YouTube Shorts

Παράγει faceless βίντεο (ψυχολογικά facts, αγγλικά) και τα ανεβάζει σε YouTube Shorts.
100% δωρεάν εργαλεία: `edge-tts` (φωνή), Pexels API (background clips), `ffmpeg` (σύνθεση),
YouTube Data API v3 (upload), Windows Task Scheduler (χρονοπρογραμματισμός).

## Δομή
```
content/scripts_pool.json   -> 32 έτοιμα scripts (psychology facts). "used": true/false tracking.
assets/cache/                -> cache των background video clips από Pexels
output/                       -> τελικά rendered .mp4
credentials/client_secret.json -> OAuth credentials (θα το κατεβάσεις εσύ, βήμα 2)
credentials/token.json       -> αποθηκεύεται αυτόματα μετά το πρώτο login
logs/run_log.jsonl           -> log κάθε render/upload
scripts/generate_video.py    -> TTS + Pexels + ffmpeg -> mp4
scripts/upload_youtube.py    -> OAuth + upload στο YouTube
scripts/main.py              -> τρέχει τα δύο παραπάνω μαζί + κρατάει tracking
config.json                  -> API keys + ρυθμίσεις (privacy status, voice, κλπ)
venv/                        -> python virtual environment (ήδη έτοιμο)
```

## Βήμα 1 — Δωρεάν Pexels API key (background video clips)
1. Πήγαινε στο https://www.pexels.com/api/ και κάνε δωρεάν εγγραφή.
2. Θα σου δώσει ένα API key αμέσως.
3. Άνοιξε το `config.json` στη ρίζα του project και βάλε το key στο `"pexels_api_key"`.

## Βήμα 2 — YouTube Data API v3 (OAuth) — δωρεάν, μερικά βήματα
1. Πήγαινε στο https://console.cloud.google.com/ και δημιούργησε ένα νέο project (π.χ. "shorts-automation").
2. Στο μενού, πήγαινε **APIs & Services > Library**, αναζήτησε "YouTube Data API v3" και πάτα **Enable**.
3. Πήγαινε **APIs & Services > OAuth consent screen**:
   - Τύπος: **External**.
   - Συμπλήρωσε όνομα app, email — τα υπόλοιπα προαιρετικά.
   - Στο βήμα "Test users", πρόσθεσε το δικό σου Google/YouTube email (`mikesheeesh@gmail.com` ή όποιο συνδέεται με το κανάλι σου).
   - Άφησέ το σε **Testing** mode (δεν χρειάζεται δημοσίευση/verification για προσωπική χρήση).
4. Πήγαινε **APIs & Services > Credentials > Create Credentials > OAuth client ID**:
   - Application type: **Desktop app**.
   - Δώσε ένα όνομα, πάτα Create.
   - Κατέβασε το JSON (κουμπί download).
5. Μετονόμασε το αρχείο σε `client_secret.json` και βάλ' το μέσα στο `credentials\` φάκελο του project.

**Σημείωση quota**: Το δωρεάν daily quota είναι 10.000 units. Κάθε upload video κοστίζει 1.600 units,
άρα ~6 uploads/μέρα default — αρκεί άνετα για τα 3-4/μέρα που θέλεις.

## Βήμα 3 — Πρώτο τρέξιμο (test)
Άνοιξε PowerShell/terminal μέσα στο `shorts-automation` folder.

**3α. Test μόνο render (χωρίς upload)** — επιβεβαιώνει ότι TTS + Pexels + ffmpeg δουλεύουν:
```
.\venv\Scripts\python.exe scripts\main.py --render-only
```
Θα φτιάξει ένα mp4 μέσα στο `output\`. Άνοιξέ το και έλεγξε ήχο/captions/ratio.

**3β. Test upload (private)** — θα ανοίξει browser για το πρώτο OAuth login/consent:
```
.\venv\Scripts\python.exe scripts\main.py
```
Με default `youtube_privacy_status: "private"` στο `config.json`, το πρώτο βίντεο θα ανέβει **private**
(θα το βλέπεις μόνο εσύ στο YouTube Studio). Όταν είσαι σίγουρος/η ότι όλα δουλεύουν καλά, άλλαξε στο
`config.json` το `"youtube_privacy_status"` σε `"public"` για να ανεβαίνουν κανονικά.

## Βήμα 4 — Windows Task Scheduler (3-4 videos/μέρα)
Άνοιξε **Task Scheduler** (αναζήτηση στο Start menu) > **Create Task**:
- General: όνομα "Shorts Automation", "Run whether user is logged on or not" (προαιρετικό).
- Triggers: πρόσθεσε 3-4 triggers, π.χ. καθημερινά στις 10:00, 14:00, 18:00, 22:00.
- Actions > New:
  - Program/script: `C:\Users\kazan\shorts-automation\venv\Scripts\python.exe`
  - Arguments: `scripts\main.py`
  - Start in: `C:\Users\kazan\shorts-automation`
- Save (θα σου ζητήσει τον κωδικό Windows σου).

Ή γρήγορα μέσω PowerShell (τρέξε το ως Administrator μία φορά):
```powershell
$action = New-ScheduledTaskAction -Execute "C:\Users\kazan\shorts-automation\venv\Scripts\python.exe" -Argument "scripts\main.py" -WorkingDirectory "C:\Users\kazan\shorts-automation"
$triggers = @(
  New-ScheduledTaskTrigger -Daily -At 10:00am
  New-ScheduledTaskTrigger -Daily -At 2:00pm
  New-ScheduledTaskTrigger -Daily -At 6:00pm
  New-ScheduledTaskTrigger -Daily -At 10:00pm
)
Register-ScheduledTask -TaskName "ShortsAutomation" -Action $action -Trigger $triggers
```

## Πότε θα χρειαστείς εμένα ξανά
Το `content/scripts_pool.json` έχει 32 έτοιμα scripts. Με 3-4/μέρα, τελειώνουν σε ~8-10 μέρες.
Όταν αδειάσει (ή θες νέο θέμα/niche), απλά πες μου "φτιάξε άλλα 30 scripts" — θα τα γράψω στη
ίδια μορφή (ακολουθώντας πάντα τη δομή Viral Content Strategist) και θα τα προσθέσω στο pool, δωρεάν.

## Troubleshooting
- **"'ffmpeg' not found"**: άνοιξε νέο terminal (το PATH ενημερώθηκε μετά την εγκατάσταση) ή κάνε restart.
- **Pexels 429 / rate limit**: απίθανο στη συχνότητα που θέλεις (~20 requests/μέρα έναντι 200/ώρα free tier).
- **YouTube upload quota exceeded**: σταμάτα να ανεβάζεις μέχρι το επόμενο daily reset (Pacific Time midnight).
- **OAuth "access blocked: app not verified"**: βεβαιώσου ότι το email σου είναι στη λίστα "Test users" στο OAuth consent screen (βήμα 2.3).

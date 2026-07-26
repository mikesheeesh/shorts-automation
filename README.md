# Shorts Automation — αυτόματο pipeline για YouTube Shorts

Παράγει faceless βίντεο (ψυχολογικά facts, αγγλικά) και τα ανεβάζει σε YouTube Shorts.
100% δωρεάν εργαλεία: `edge-tts` (φωνή), Pexels API (background clips), `ffmpeg` (σύνθεση),
YouTube Data API v3 (upload), **GitHub Actions** (χρονοπρογραμματισμός — τρέχει στο cloud,
όχι στο laptop).

Repo: https://github.com/mikesheeesh/shorts-automation (private)

## Πώς τρέχει σήμερα
Το **GitHub Actions** workflow (`.github/workflows/shorts.yml`) τρέχει 4 φορές/μέρα
(10:00, 14:00, 18:00, 22:00 Athens time) εντελώς στο cloud: render + upload + commit πίσω
του `content/scripts_pool.json` (used tracking). Δεν χρειάζεται το laptop να είναι
αναμμένο/συνδεδεμένο. Το τοπικό Windows Task Scheduler task ("ShortsAutomation") έχει
**απενεργοποιηθεί** (όχι διαγραφεί) για να μην ανεβαίνουν διπλά βίντεο.

Τα local αρχεία (`venv/`, `config.json`, `credentials/`) παραμένουν χρήσιμα για:
- Τοπικό test render (`scripts/main.py --render-only`)
- Το εβδομαδιαίο OAuth refresh (παρακάτω)
- Να ξαναγράφεις/προσθέτεις scripts στο `content/scripts_pool.json`

## ⚠️ Εβδομαδιαίο manual βήμα — OAuth token refresh
Επειδή μείναμε 100% δωρεάν (χωρίς Google app verification, βλ. γιατί παρακάτω), το YouTube
OAuth refresh token **λήγει αυτόματα κάθε 7 μέρες** όσο η Google app είναι σε "Testing" mode.
Χρειάζεται αυτό το 2λεπτο βήμα περίπου κάθε βδομάδα, αλλιώς το GitHub Actions θα αρχίσει να
αποτυγχάνει στο upload:

```powershell
cd C:\Users\kazan\shorts-automation
del credentials\token.json
.\venv\Scripts\python.exe scripts\upload_youtube.py --refresh-only
# θα ανοίξει browser για Google login/consent (ίδιο email, ίδια app)
& "C:\Program Files\GitHub CLI\gh.exe" secret set TOKEN_JSON --repo mikesheeesh/shorts-automation < credentials\token.json
```

Αν το ξεχάσεις και το upload αρχίσει να αποτυγχάνει στο GitHub Actions log με σφάλμα OAuth/
invalid_grant, απλά κάνε τα 3 βήματα παραπάνω ξανά — τίποτα δεν χάνεται, απλά χάνεις κάποια
uploads μέχρι να το ξανακάνεις.

*(Γιατί όχι μόνιμη λύση: θα χρειαζόταν Google app verification, που με τη σειρά του θέλει ένα
πραγματικό (πληρωμένο) domain για το "Authorized domains" πεδίο — το `github.io` δεν γίνεται
δεκτό γιατί είναι στη Public Suffix List. Αποφασίσαμε να μείνουμε 100% δωρεάν αντί να αγοράσουμε domain.)*

## Δομή
```
content/scripts_pool.json     -> έτοιμα scripts (psychology facts). "used": true/false tracking.
assets/cache/                  -> cache background video clips από Pexels (τοπικό μόνο, gitignored)
assets/fonts/caption_font.ttf  -> bundled font (Archivo Black, OFL) — ίδιο τοπικά και σε CI
assets/branding/                -> banner.png / profile.png για το κανάλι
output/                         -> τελικά rendered .mp4 (gitignored)
credentials/client_secret.json -> OAuth client credentials (τοπικό μόνο, gitignored)
credentials/token.json         -> τρέχον OAuth token (τοπικό μόνο, gitignored)
docs/                           -> GitHub Pages (privacy policy / homepage) — δεν χρειάζεται πλέον για verification, μένει ως τεκμηρίωση
.github/workflows/shorts.yml   -> GitHub Actions: render+upload 4x/μέρα, commit-back scripts_pool.json
scripts/generate_video.py      -> TTS + Pexels + ffmpeg -> mp4
scripts/upload_youtube.py      -> OAuth + upload στο YouTube (+ --refresh-only)
scripts/main.py                -> τρέχει τα δύο παραπάνω μαζί + κρατάει tracking
config.json / config.example.json -> API keys + ρυθμίσεις (το config.json είναι gitignored)
venv/                           -> python virtual environment (τοπικό μόνο)
```

## Τοπικό setup (αν χρειαστεί ξανά από την αρχή)
1. **Pexels API key** (δωρεάν): https://www.pexels.com/api/ → βάλε το key στο `config.json`
   (`pexels_api_key`). Ήδη ρυθμισμένο, και υπάρχει και ως GitHub secret `PEXELS_API_KEY`.
2. **YouTube OAuth**: `client_secret.json` ήδη στο `credentials/` (Google Cloud project,
   OAuth consent screen σε Testing mode, το email σου στα Test users). Αν χαθεί, φτιάξε νέο
   από **Google Cloud Console > APIs & Services > Credentials > OAuth client ID > Desktop app**.
3. Test render χωρίς upload: `.\venv\Scripts\python.exe scripts\main.py --render-only`
4. Test με upload: `.\venv\Scripts\python.exe scripts\main.py`

**Σημείωση quota**: Δωρεάν daily quota 10.000 units, κάθε upload κοστίζει 1.600 units,
άρα ~6 uploads/μέρα default — αρκεί άνετα για τα 4/μέρα.

## Πότε θα χρειαστείς εμένα ξανά
1. **Κάθε ~7 μέρες**: το OAuth refresh παραπάνω (μπορώ να σου το θυμίζω αν θες recurring reminder).
2. **Όταν αδειάσει το `scripts_pool.json`** (32 scripts / 4 τη μέρα ≈ 8 μέρες): πες μου "φτιάξε
   άλλα 30 scripts" — θα τα γράψω στην ίδια μορφή (Viral Content Strategist δομή) και θα τα
   κάνω commit+push στο repo.

## Troubleshooting
- **GitHub Actions run αποτυγχάνει με OAuth/invalid_grant error**: το refresh token έληξε
  (7 μέρες), κάνε το βήμα refresh παραπάνω.
- **"'ffmpeg' not found" (τοπικά)**: άνοιξε νέο terminal (το PATH ενημερώθηκε μετά την εγκατάσταση).
- **Pexels 429 / rate limit**: απίθανο στη συχνότητα που τρέχουμε (~20 requests/μέρα έναντι
  200/ώρα free tier).
- **YouTube upload quota exceeded**: σταμάτα μέχρι το επόμενο daily reset (Pacific Time midnight).
- **OAuth "access blocked: app not verified"**: βεβαιώσου ότι το email σου είναι στη λίστα
  "Test users" στο OAuth consent screen.
- **Θες να ξαναδείς τα GitHub Actions logs**: `gh run list --repo mikesheeesh/shorts-automation`
  και `gh run view <id> --log`.

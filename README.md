# Well-Net — Ethiopian Wellness Ecosystem
## Setup Guide for D:/alx/Personalprojects/v2/well-net/

---

## Folder structure on your machine
```
D:/alx/Personalprojects/v2/well-net/
├── backend/          ← Django flat project
│   ├── config/       ← settings, urls, wsgi
│   ├── users/        ← auth, profiles, family
│   ├── foods/        ← food DB, meal log, scoring
│   ├── wellness/     ← wellness models
│   ├── ai/           ← Claude API, SMS, Telegram
│   ├── experts/      ← professional marketplace
│   ├── packages/     ← wellness packages
│   ├── notifications/← off-peak deals, Celery tasks
│   ├── core/         ← shared base, permissions
│   ├── manage.py
│   └── requirements.txt
└── frontend/         ← Next.js 14 App Router
    ├── src/
    │   ├── app/      ← pages (dashboard, log, ai, experts, packages)
    │   ├── components/
    │   ├── services/ ← all API calls
    │   ├── store/    ← Zustand global state
    │   ├── types/    ← TypeScript interfaces
    │   └── lib/      ← api client, utils
    └── package.json
```

---

## Step 1 — Clone/copy files to your machine
Copy the backend and frontend folders to:
`D:/alx/Personalprojects/v2/well-net/`

---

## Step 2 — Backend setup (run in Git Bash or PowerShell)
```bash
cd D:/alx/Personalprojects/v2/well-net/backend

# Create virtual environment
python -m venv venv
source venv/Scripts/activate      # Windows Git Bash
# OR: venv\Scripts\activate.bat   # Windows CMD

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Edit .env — add your DB password and Anthropic API key

# Create PostgreSQL database
# Open pgAdmin or run: createdb wellnet

# Run migrations
python manage.py makemigrations users foods wellness ai experts packages notifications
python manage.py migrate

# Seed the Ethiopian food database
python manage.py seed_foods

# Create superuser (for Django admin)
python manage.py createsuperuser

# Run server
python manage.py runserver
# → http://localhost:8000
```

---

## Step 3 — Frontend setup
```bash
cd D:/alx/Personalprojects/v2/well-net/frontend

# Install dependencies
npm install

# Create env file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# Run dev server
npm run dev
# → http://localhost:3000
```

---

## Step 4 — Verify everything works
1. Open http://localhost:8000/admin — login with superuser
2. Check http://localhost:8000/api/v1/foods/ — should return 18 foods
3. Open http://localhost:3000 — should redirect to login

---

## Key API endpoints
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/auth/register/ | Register |
| POST | /api/v1/auth/login/ | Get JWT tokens |
| GET  | /api/v1/foods/ | Ethiopian food DB |
| POST | /api/v1/foods/log/ | Log a meal |
| GET  | /api/v1/foods/daily/ | Today's nutrition |
| GET  | /api/v1/foods/weekly/ | 7-day trend |
| GET  | /api/v1/ai/tips/ | AI wellness tips |
| GET  | /api/v1/ai/feed/ | Wellness journey feed |
| POST | /api/v1/ai/meal-plan/ | AI family meal plan |
| GET  | /api/v1/experts/ | Licensed professionals |
| GET  | /api/v1/packages/ | Wellness packages |
| GET  | /api/v1/notifications/deals/ | Kuriftu off-peak deals |
| POST | /api/v1/ai/sms/ | Africa's Talking webhook |
| POST | /api/v1/ai/telegram/ | Telegram bot webhook |

---

## Hackathon demo checklist
- [ ] `python manage.py seed_foods` — loads 18 verified Ethiopian foods
- [ ] Create a test user via /api/v1/auth/register/
- [ ] Log a meal with injera + misir_wot — score should be 75+
- [ ] Check /api/v1/ai/tips/ — should return AI wellness tips
- [ ] Create an OffPeakDeal in Django admin for demo notifications
- [ ] Test SMS via Africa's Talking sandbox

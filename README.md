# Lash Zone London - AI Receptionist

A complete 24/7 AI-powered phone receptionist for beauty and lash studios.

## Features

- **AI Voice Receptionist (Luna)**: Natural conversations with clients using GPT-4o
- **24/7 Availability**: Never miss a call, even outside business hours
- **Booking Assistance**: Help clients book appointments and send booking links via SMS
- **FAQ Management**: Configure what information Luna can provide
- **SMS Integration**: Send booking links and notifications
- **Escalation Handling**: Automatically alert management for complaints, refunds, allergic reactions
- **Call Recording & Transcript**: Review all conversations in the admin dashboard
- **Admin Dashboard**: Manage settings, FAQs, and view call history

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- Twilio account
- OpenAI API key
- Supabase account

### 1. Database Setup

Run the SQL schema in your Supabase SQL Editor:

```bash
# Open Supabase Dashboard > SQL Editor
# Copy and paste the contents of database/schema.sql
# Execute
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend/lash-zone-admin
pnpm install
pnpm dev
```

### 4. Twilio Configuration

In your Twilio Console:

1. Go to Phone Numbers > Your Number
2. Set the Voice webhook to:
   ```
   https://your-domain.com/webhook/incoming-call
   ```
3. Set the status callback to:
   ```
   https://your-domain.com/webhook/call-status
   ```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TWILIO_ACCOUNT_SID` | Twilio account SID | ACxxx... |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | xxx |
| `TWILIO_PHONE_NUMBER` | Twilio phone number | +447455709725 |
| `OPENAI_API_KEY` | OpenAI API key | sk-proj-xxx |
| `SUPABASE_URL` | Supabase project URL | https://xxx.supabase.co |
| `SUPABASE_ANON_KEY` | Supabase anon key | eyJxxx |
| `SUPABASE_SERVICE_KEY` | Supabase service key | eyJxxx |
| `STUDIO_NAME` | Your business name | Lash Zone London |
| `STUDIO_PHONE` | Your business phone | 07748252038 |
| `OWNER_PHONE` | Management phone | 07748252038 |
| `BOOKING_URL` | Online booking URL | https://book.example.com |
| `BASE_URL` | Production URL | https://api.example.com |

## Project Structure

```
lash-zone-ai-receptionist/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   └── receptionist.py      # AI conversation engine
│   │   ├── api/
│   │   │   └── routes.py          # API endpoints
│   │   ├── database/
│   │   │   └── supabase_client.py # Database operations
│   │   ├── main.py                # FastAPI application
│   │   └── voice_handler.py       # Twilio integration
│   ├── database/
│   │   └── schema.sql             # Database schema
│   └── requirements.txt
├── frontend/
│   └── lash-zone-admin/           # React admin dashboard
│       └── src/
│           ├── pages/             # Dashboard pages
│           ├── components/        # Shared components
│           └── lib/api.ts         # API client
├── SPEC.md                        # Project specification
└── README.md
```

## Deployment

### Backend (Railway, Render, Fly.io)

1. Push code to GitHub
2. Connect your repository to deployment platform
3. Set environment variables
4. Deploy

### Frontend (Vercel, Netlify)

1. Build: `cd frontend/lash-zone-admin && pnpm build`
2. Deploy the `dist` folder

### Important Notes

- Use HTTPS for all endpoints (Twilio requirement)
- Set correct BASE_URL for production
- Configure Twilio webhooks to point to production URL

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook/incoming-call` | Twilio incoming call webhook |
| POST | `/webhook/call-status` | Call status updates |
| POST | `/webhook/sms-received` | SMS received webhook |
| GET | `/api/calls` | List call history |
| GET | `/api/calls/{id}` | Call details with transcript |
| GET | `/api/calls/search` | Search calls |
| GET | `/api/appointments` | List appointments |
| POST | `/api/appointments` | Create appointment |
| GET | `/api/availability` | Check time slot availability |
| GET | `/api/escalations` | List escalation requests |
| POST | `/api/escalations` | Create escalation |
| PUT | `/api/escalations/{id}` | Resolve escalation |
| GET | `/api/faqs` | List FAQ knowledge base |
| POST | `/api/faqs` | Create FAQ |
| PUT | `/api/faqs/{id}` | Update FAQ |
| DELETE | `/api/faqs/{id}` | Delete FAQ |
| GET | `/api/config` | Get all configuration |
| PUT | `/api/config` | Update configuration |
| POST | `/api/sms/send` | Send SMS message |
| GET | `/health` | Health check |

## How Luna Works

### Conversation Flow

1. **Greeting**: Luna welcomes caller and offers help
2. **Identify Intent**: Understand what caller needs
3. **Handle Request**: Provide info, book appointment, or escalate
4. **Confirm & Close**: Ensure satisfaction, offer more help

### Escalation Triggers

Luna automatically escalates when caller mentions:
- Complaint or dissatisfaction
- Refund request
- Allergic reaction
- Management decision needed
- Complex or unusual requests

### Booking Flow

1. Identify desired service
2. Check availability
3. Collect client details (name, phone)
4. Confirm appointment OR send SMS booking link
5. End with reminder and offer for more help

## Customization

### AI Personality

Edit `backend/app/ai/receptionist.py` to customize:
- System prompt (personality, tone)
- Escalation keywords
- Booking confirmation messages

### FAQ Management

Use the admin dashboard to add/edit FAQs:
- Question patterns (keywords that trigger the answer)
- Answers
- Categories

### Studio Information

Configure in Settings:
- Studio name and address
- Opening hours
- Booking URL
- Owner phone for escalations

## License

MIT License

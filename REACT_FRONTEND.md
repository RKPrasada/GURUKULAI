# VidyaBot React Frontend

Complete React 18 + TypeScript frontend migration from Streamlit. Modern SPA with real-time authentication, diagnostic testing, adaptive learning, and progress tracking.

## 🚀 Quick Start

### Development Mode

```bash
# Install dependencies (one time)
cd web
npm install

# Start dev server (watches for changes)
npm run dev

# Backend should be running on :8000
# Frontend opens at http://localhost:3000
```

### Using the Launcher

```bash
# Starts both API (:8000) and React frontend (:3000)
python launcher_react.py
```

### Production Build

```bash
npm run build      # Creates optimized dist/ folder
npm run preview    # Test production build locally
```

## 📁 Project Structure

```
web/
├── src/
│   ├── components/
│   │   ├── Layout.tsx          # Header, sidebar, navigation
│   │   ├── AuthForm.tsx        # Reusable auth form wrapper + FormInput/FormSelect helpers
│   │
│   ├── pages/
│   │   ├── LoginPage.tsx       # Login with username/password + forgot password link
│   │   ├── RegisterPage.tsx    # Registration with exam selection & language preference
│   │   ├── ForgotPasswordPage.tsx   # 2-step: email → token → new password
│   │   ├── HomePage.tsx        # Dashboard with diagnostic prompt or study/test shortcuts
│   │   ├── DiagnosticPage.tsx  # 30-question placement test with real-time scoring
│   │   ├── StudyPage.tsx       # Topic search + chat + notes display
│   │   ├── TestPage.tsx        # Adaptive MCQ with difficulty selection
│   │   ├── ProgressPage.tsx    # Charts, accuracy by topic, recommendations
│   │
│   ├── services/
│   │   └── api.ts              # Axios client with bearer token + 401 auto-logout
│   │
│   ├── store/
│   │   └── auth.ts             # Zustand store: student + token, localStorage persistence
│   │
│   ├── types/
│   │   └── index.ts            # TypeScript interfaces: Student, Question, DiagnosticSession, etc.
│   │
│   ├── App.tsx                 # React Router: public + protected routes
│   ├── main.tsx                # Entry point
│   └── index.css               # Tailwind + base styles
│
├── vite.config.ts              # Vite config with @ alias + API proxy to :8000
├── tsconfig.json               # TypeScript strict mode + path aliases
├── tailwind.config.js          # Primary #5C35CC, secondary #FF9800, dark mode enabled
├── package.json                # Dependencies + build scripts
└── index.html                  # HTML entry point
```

## 🔐 Authentication Flow

### Registration
1. User fills form with username, email, password, exam target, language
2. POST `/api/auth/register` → bcrypt hashed, stored in data/users.jsonl
3. Returns access_token + student profile
4. Stored in Zustand + localStorage (persistent across refreshes)

### Login
1. POST `/api/auth/login` with username + password
2. Returns access_token + student profile
3. Auto-redirected to `/` (home)

### Forgot Password (2-step)
1. POST `/api/auth/forgot-password` with email
2. Returns reset_token (valid 1 hour)
3. POST `/api/auth/reset-password` with new password + token
4. Token is invalidated after use

### Protected Routes
- Bearer token injected in every request via Axios interceptor
- 401 response → auto-logout, clear localStorage, redirect to /login
- Unauthenticated users redirected to /login

## 📊 Pages & Features

### LoginPage
- Form with username + password
- "Forgot password?" link
- "Register here" link for new users

### RegisterPage
- Multi-step form: username, email, full name, exam target, language
- Exam options: RRB NTPC, NDA, JEE, NEET
- Language: English or हिंदी
- Password confirmation validation

### ForgotPasswordPage
- **Step 1:** Email input → sends reset token
- **Step 2:** Token + new password + confirmation
- Success → redirect to login in 2s

### HomePage
- **If diagnostic not done:** Prominent button "Start Diagnostic" with yellow alert
- **If diagnostic done:** 
  - 3 stat cards: Questions Done, Study Streak, Average Accuracy
  - 3 action cards: Study, Practice Tests, View Progress
  - Recent weak topics (top 5) with scores

### DiagnosticPage
- 30-question placement test
- Real-time progress bar + question counter
- Single-select MCQ with radio buttons
- Previous/Next navigation
- Unanswered questions block "Next" button
- On submit: calculates weakness_map, updates student profile, redirects home

### StudyPage
- Left panel: Search bar + recommended topics (from weakness_map)
- Right panel: Chat interface or topic detail view
- POST `/api/session/chat` with query
- Returns structured notes + AI response
- Click note card → detail view with full content
- Bilingual (English + Hindi)

### TestPage
- Difficulty selector: Easy, Medium, Hard, Adaptive
- POST `/api/session/assessment/start` with difficulty
- N questions at selected difficulty
- Previous/Next navigation
- "Finish" → submit answers, update total_questions_attempted, redirect to /progress

### ProgressPage
- **Stats cards:** Questions Done, Average Accuracy, Study Streak, Topics Covered
- **Bar chart:** Accuracy by topic (recharts)
- **Pie chart:** Performance distribution (Strong/Decent/Need Help)
- **Detailed list:** All topics with accuracy bars and percentages
- **Recommendations:** Suggest focusing on topics with <60% accuracy

## 🎨 Styling & UI

### Tailwind CSS
- Custom colors: primary `#5C35CC` (purple), secondary `#FF9800` (orange)
- Dark mode enabled by default (user can toggle)
- Responsive: mobile-first grid layouts (1 col → 2/3 col on larger screens)
- Shadows, rounded corners, transitions on hover

### Components
- **Layout:** Header (logo + exam + user name), sidebar with nav, mobile hamburger, logout button
- **Forms:** Reusable FormInput + FormSelect with labels, errors, validation
- **Cards:** StatCard, ActionCard, TopicCard with icon + description
- **Loading:** Spinner on data fetch, "⏳ Processing..." on submit buttons

### Icons (lucide-react)
- BookOpen, Zap, BarChart3, Award, ChevronRight, Clock, Flame, TrendingUp, Target, MessageSquare, Search

## 🔌 API Integration

All endpoints require Bearer token in Authorization header (injected by Axios interceptor).

### Auth Endpoints
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/forgot-password
POST /api/auth/reset-password
POST /api/auth/change-password
```

### Session Endpoints
```
POST /api/session/diagnostic/start → { session_id, questions: [30] }
POST /api/session/diagnostic/submit → { weakness_map: [...], session_id }
POST /api/session/chat → { response, notes: [...] }
POST /api/session/assessment/start → { session_id, questions: [...] }
POST /api/session/assessment/answer → { score, feedback }
```

### Student Endpoints
```
GET /api/student/{student_id}
```

## 🔒 Security

- Passwords hashed with bcrypt before storage
- Bearer token (HMAC-SHA256) for all authenticated requests
- 1-hour expiry on reset tokens
- 401 response → immediate logout + localStorage clear
- PII scrubbing in all responses (InputGuard, OutputGuard)
- No sensitive data in localStorage except token + basic student profile

## 🌐 Internationalization

Pages support English + Hindi (हिंदी) based on `student.preferred_language`:
- Labels, buttons, messages translated inline
- Select language during registration
- Change in profile settings

## 📦 Dependencies

```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-router-dom": "^6.20.0",
  "axios": "^1.6.5",
  "zustand": "^4.4.7",
  "lucide-react": "^0.294.0",
  "recharts": "^2.10.3",
  "tailwindcss": "^3.4.1"
}
```

## 🧪 Development Tips

### Hot Module Replacement (HMR)
Vite automatically reloads on file changes. No full page refresh needed.

### TypeScript Strict Mode
All files use strict type checking. Run `npm run build` to catch type errors.

### Path Aliases
Use `@/` to import from src/:
```tsx
import { useAuthStore } from '@/store/auth'
import api from '@/services/api'
```

### Environment Variables
Create `.env` in the `web/` directory:
```
VITE_API_URL=http://localhost:8000
```

## 🚀 Deployment

### Build for Production
```bash
npm run build
```
Generates `dist/` folder with optimized static files. Serve with any web server (nginx, Node, etc.).

### Docker Example
```dockerfile
FROM node:20-alpine as builder
WORKDIR /app
COPY web/ .
RUN npm install && npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 📝 Notes

- This replaces the old Streamlit frontend (frontend/ directory)
- Streamlit had limitations with routing and state management
- React provides better UX with smooth transitions, real-time updates, and persistent state
- Backend API (api.main:app) is fully compatible with both frontends

## 🐛 Troubleshooting

### Port 3000 already in use
```bash
# Find process using port 3000 and kill it, or use different port
lsof -i :3000
kill -9 <PID>

# Or change port in vite.config.ts or environment
```

### API 401 Unauthorized
- Check if token is being sent: Open DevTools → Network → check Authorization header
- Verify token is valid: try login again
- Check if API is running on :8000

### Build fails
```bash
npm install     # Reinstall dependencies
npm run build   # Check for TypeScript errors
```

---

**Status:** ✅ Ready for use
**Frontend Type:** React 18 SPA
**Last Updated:** June 29, 2026

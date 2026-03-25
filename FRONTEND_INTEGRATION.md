# Frontend Integration Guide

## Overview
This document outlines the complete integration of your Eldercare Sanctuary frontend. All HTML UI designs have been converted into a production-ready Next.js application with proper routing, state management, and component architecture.

## Capability vs Wiring Matrix

This matrix separates backend-ready capabilities from currently wired frontend flows.

| Module | Backend Capability | UI Wired | Current Frontend Evidence |
|---|---|---|---|
| auth | Implemented | Partial | `apps/web/app/(auth)/login/page.tsx`, `apps/web/providers/auth-provider.tsx` |
| health-records | Implemented | Wired | `apps/web/app/(portal)/family/health-records/page.tsx` |
| consent | Implemented | Partial | `apps/web/app/(portal)/family/consents/page.tsx` |
| notifications | Implemented | Wired | `apps/web/app/(portal)/family/notifications/page.tsx` |
| sos | Implemented | Wired | `apps/web/components/sos-timeline.tsx`, `apps/web/app/(portal)/family/sos/page.tsx` |
| marketplace | Implemented | Partial | `apps/web/app/(portal)/family/marketplace/page.tsx` |
| subscriptions | Implemented | Partial | `apps/web/app/(portal)/family/subscriptions/page.tsx` |
| admin-analytics | Implemented | Wired | `apps/web/app/(portal)/admin/page.tsx` |
| family-links | Implemented | Not Wired | route shell present, API flows pending wiring |
| medication | Implemented | Not Wired | component demos exist, API-backed portal page pending |
| audit | Implemented | Not Wired | backend API available, no active portal wiring |

Detailed route-level mapping lives in `BACKEND_FRONTEND_CONTRACT_MAP.md`.

## Typed SDK Workflow (OpenAPI)

The web app uses an OpenAPI-driven typed SDK workflow to reduce ad-hoc request typing drift.

Commands in `apps/web/package.json`:
- `npm run openapi:pull` pulls `openapi.json` from backend (default `http://localhost:8000/openapi.json`).
- `npm run openapi:types` generates SDK schema types.
- `npm run sdk:generate` runs both steps.

SDK files:
- `apps/web/lib/sdk/client.ts`
- `apps/web/lib/sdk/schema.ts`
- `apps/web/lib/sdk/notifications.ts`
- `apps/web/lib/sdk/sos.ts`

## Project Structure

```
apps/web/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── (auth)/                   # Auth route group
│   │   │   ├── login/page.tsx        # From: auth_login_signup/code.html
│   │   │   └── signup/page.tsx       # From: auth_login_signup/code.html
│   │   ├── (public)/                 # Public route group
│   │   │   └── role-selection/       # From: role_selection/code.html
│   │   ├── (admin)/                  # Admin route group
│   │   │   └── dashboard/            # From: admin_panel/code.html
│   │   ├── (family)/                 # Family member route group
│   │   │   └── dashboard/            # From: family_dashboard_overview/code.html
│   │   ├── (parent)/                 # Parent/Elderly route group
│   │   │   └── dashboard/            # From: parent_mobile_app/code.html
│   │   ├── (caregiver)/              # Caregiver route group
│   │   │   └── dashboard/            # From: care_coordination_panel/code.html
│   │   ├── (doctor)/                 # Doctor route group
│   │   │   └── dashboard/            # From: medical_records_module/code.html (adapted)
│   │   ├── layout.tsx                # Root layout
│   │   ├── globals.css               # Global styles
│   │   └── page.tsx                  # Home page
│   │
│   ├── shared/                       # Shared utilities and components
│   │   ├── ui/                       # Reusable UI components
│   │   │   ├── Button.tsx            # Primary button component
│   │   │   ├── Card.tsx              # Card container component
│   │   │   ├── Input.tsx             # Form input component
│   │   │   ├── Select.tsx            # Select dropdown component
│   │   │   ├── Alert.tsx             # Alert notification component
│   │   │   ├── Badge.tsx             # Badge/tag component
│   │   │   └── index.ts              # Export all UI components
│   │   ├── state/                    # State management with Zustand
│   │   │   └── auth.ts               # Authentication store
│   │   ├── api-client/               # API integration layer
│   │   │   └── index.ts              # Axios instance with interceptors
│   │   ├── types/                    # TypeScript type definitions
│   │   │   └── index.ts              # Shared types and interfaces
│   │   └── utils/                    # Utility functions
│   │       └── index.ts              # Helper functions (cn, formatDate, etc.)
│   │
│   └── modules/                      # Feature-specific modules
│       ├── auth/                     # Authentication module
│       ├── health-records/           # From: medical_records_module/code.html
│       │   └── page.tsx
│       ├── sos/                      # From: sos_emergency_flow/code.html
│       │   └── page.tsx
│       ├── marketplace/              # From: care_marketplace/code.html
│       │   └── page.tsx
│       └── care-coordination/        # From: care_coordination_panel/code.html
│           └── page.tsx
│
├── package.json                      # Dependencies
├── tsconfig.json                     # TypeScript configuration
├── tailwind.config.js                # Tailwind CSS configuration
├── next.config.js                    # Next.js configuration
└── postcss.config.js                 # PostCSS configuration

```

## UI Design Mapping

### Authentication Flow
- **auth_login_signup/code.html** → `(auth)/login` & `(auth)/signup`
  - Login form with email/password
  - Signup form with role selection
  - Error handling and validation
  - Loading states

### Role-Based Access
- **role_selection/code.html** → `(public)/role-selection`
  - Visual role selection interface
  - Quick navigation to role-specific dashboards
  - 4 main roles: Family Member, Parent, Caregiver, Doctor

### Admin Portal
- **admin_panel/code.html** → `(admin)/dashboard`
  - System overview and statistics
  - User management interface
  - Quick actions and reports
  - Both light and dark themes supported (admin_panel_dark)

### Family Dashboard
- **family_dashboard_overview/code.html** → `(family)/dashboard`
  - Family member health status cards
  - Recent activity feed
  - Quick messaging and detail views
  - Dark theme variant available (family_dashboard_dark)

### Parent/Elderly Dashboard
- **parent_mobile_app/code.html** → `(parent)/dashboard`
  - Health metrics display (BP, HR, Temperature)
  - Medication adherence tracking
  - Appointment and alert notifications
  - SOS button for emergencies

### Caregiver Dashboard
- **care_coordination_panel/code.html** → `(caregiver)/dashboard`
  - Active care assignments
  - Daily task management
  - Schedule view
  - Patient monitoring
  - Dark theme variant (care_coordination_dark)

### Doctor Portal
- **medical_records_module/code.html** → `(doctor)/dashboard`
  - Patient list and management
  - Alert system for critical conditions
  - Recent records access
  - Pending review queue
  - Dark theme variant (medical_records_dark)

### Health Records
- **medical_records_module/code.html** → `/modules/health-records`
  - Complete health history
  - Document upload and management
  - Quick medical info (blood type, allergies)
  - Access control with consent management

### Emergency SOS
- **sos_emergency_flow/code.html** → `/modules/sos`
  - Emergency alert button
  - Emergency contact list
  - Quick access to medical information
  - Alert cascade to family and emergency services

### Caregiver Marketplace
- **care_marketplace/code.html** → `/modules/marketplace`
  - Caregiver search and filtering
  - Profile cards with ratings and rates
  - Availability status
  - Hire/messaging interface

## Key Features Implemented

### Authentication & Authorization
- Role-based route groups with Next.js
- Zustand state management for auth
- Axios API client with token-based auth
- Automatic token injection in requests
- 401 error handling with auto-redirect

### Responsive Design
- Tailwind CSS with custom color palette
- Mobile-first approach
- Responsive grid layouts
- Adaptive typography

### Component System
- Reusable UI components (Button, Card, Input, etc.)
- Consistent styling across all routes
- Accessible form inputs with labels
- Error state handling

### State Management
- Zustand stores for auth state
- LocalStorage for token persistence
- API client with global interceptors

### API Integration
- Configured for backend at `NEXT_PUBLIC_API_URL`
- Automatic auth header injection
- Error responses with friendly messages
- Sample endpoints ready for backend connection

## Getting Started

### Installation
```bash
cd apps/web
npm install
```

### Development
```bash
npm run dev
```
Open http://localhost:3000

### Build
```bash
npm run build
npm start
```

### Type Checking
```bash
npm run type-check
```

## Environment Variables
Create a `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Connecting to Your Backend

### API Client Configuration
The API client in `src/shared/api-client/index.ts` is pre-configured with:
- Base URL from environment variable
- Automatic auth header injection
- Error interceptor for 401 redirects

### Example API Call
```typescript
import { apiClient } from '@/shared/api-client';

// In your component
const response = await apiClient.post('/auth/login', {
  email: 'user@example.com',
  password: 'password'
});
```

### Required Backend Endpoints
- `POST /auth/login` - User login
- `POST /auth/signup` - User registration
- `GET /auth/me` - Get current user
- `POST /auth/logout` - User logout

Refer to `backend.md` and `api versioning.md` for complete API specifications.

## Styling & Theming

### Colors
The app uses Material Design 3 color system:
- Primary: `#0e76a8`
- Secondary: `#4c616c`
- Tertiary: `#007c7c`
- Error: `#ba1a1a`

All colors are defined in `tailwind.config.js` and can be customized there.

### Typography
- Font: Manrope (headings), Inter (body)
- Loaded from Google Fonts via Next.js

### Dark Mode
Dark mode is configured but uses class-based switching. To enable:
1. Add dark mode toggle in navigation
2. Update localStorage
3. Use Tailwind's `dark:` prefix for dark mode styles

## Next Steps

1. **Connect Backend**
   - Update `NEXT_PUBLIC_API_URL` to your backend
   - Test API endpoints in each page
   - Implement proper error handling

2. **Add Features**
   - Implement WebSocket for real-time updates
   - Add file upload for medical records
   - Integrate payment for marketplace

3. **User Testing**
   - Test responsive design on mobile
   - Verify accessibility with screen readers
   - Performance testing and optimization

4. **Deployment**
   - Deploy to Vercel (recommended for Next.js)
   - Set up CI/CD pipeline
   - Configure environment variables for production

## File References

All original HTML designs are preserved in the workspace root and can be referenced:
- Dark theme variations show additional UI states
- Each design includes all necessary styling
- Tailwind classes have been extracted and organized into components

## Support & Documentation

- **Frontend Architecture**: See docs in `frontend.md`
- **Backend Integration**: See `backend.md`, `api versioning.md`
- **Database Schema**: See `db.md`
- **Deployment**: See `infra.md`
- **Security**: See `security.md`

---

**Status**: ✅ All UI designs converted and integrated into working Next.js application
**Last Updated**: March 24, 2024

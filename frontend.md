apps/web/
├─ package.json
├─ next.config.js
├─ src/
│  ├─ app/                               # app router
│  │  ├─ (public)/
│  │  ├─ (auth)/
│  │  ├─ (admin)/
│  │  ├─ (family)/
│  │  ├─ (parent)/
│  │  ├─ (caregiver)/
│  │  ├─ (doctor)/
│  │  ├─ api/                            # BFF endpoints if needed
│  │  ├─ layout.tsx
│  │  └─ page.tsx
│  ├─ modules/                           # feature slices
│  │  ├─ auth/
│  │  ├─ family-linking/
│  │  ├─ health-records/
│  │  ├─ medications/
│  │  ├─ sos/
│  │  ├─ marketplace/
│  │  ├─ consent/
│  │  ├─ notifications/
│  │  ├─ subscriptions/
│  │  ├─ analytics/
│  │  ├─ ai-assistant/
│  │  └─ iot-devices/
│  ├─ shared/
│  │  ├─ ui/
│  │  ├─ forms/
│  │  ├─ tables/
│  │  ├─ charts/
│  │  ├─ hooks/
│  │  ├─ state/                          # zustand/redux/query cache
│  │  ├─ api-client/
│  │  ├─ websocket/
│  │  ├─ auth/
│  │  ├─ guards/
│  │  ├─ config/
│  │  ├─ types/
│  │  ├─ constants/
│  │  └─ utils/
│  ├─ styles/
│  └─ tests/
│     ├─ unit/
│     ├─ integration/
│     └─ e2e/
├─ public/
└─ middleware.ts
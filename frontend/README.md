# Frontend — Study Agent

Frontend Study Agent berbasis **Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui**.

## Struktur

```
frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx      # halaman login
│   │   │   └── signup/page.tsx     # halaman signup
│   │   ├── dashboard/page.tsx      # daftar goals (protected)
│   │   ├── globals.css             # Tailwind + shadcn CSS variables
│   │   ├── layout.tsx              # root layout (font Inter, Toaster)
│   │   └── page.tsx                # landing page
│   ├── components/
│   │   ├── ui/                     # komponen shadcn/ui
│   │   ├── error-state.tsx
│   │   ├── goal-card.tsx
│   │   ├── loading.tsx
│   │   ├── navbar.tsx
│   │   └── protected-route.tsx
│   └── lib/
│       ├── hooks/
│       │   ├── use-auth.ts         # hook auth
│       │   └── use-toast.ts        # state toast (shadcn)
│       ├── api.ts                  # axios client + endpoints
│       ├── auth-store.ts           # zustand store
│       └── utils.ts                # cn()
├── .env.local                      # NEXT_PUBLIC_API_URL
├── tailwind.config.ts
└── package.json
```

## Prasyarat

- Node.js 20+
- Backend Study Agent berjalan di `http://localhost:8000`

## Cara Run

```bash
cd frontend
npm install
npm run dev
```

Buka `http://localhost:3000`.

Pastikan `frontend/.env.local` berisi:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Scripts

```bash
npm run dev      # dev server
npm run build    # production build
npm run start    # jalankan hasil build
npm run lint     # ESLint
```

## Halaman

| Route | Deskripsi |
|---|---|
| `/` | Landing page (hero, fitur, footer) |
| `/signup` | Registrasi akun |
| `/login` | Login |
| `/dashboard` | Daftar goals user (butuh login) |

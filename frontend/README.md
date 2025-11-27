# Threat Intelligence Frontend

React + Vite application providing the management interface for the FastAPI backend.

## Technology Stack

- React 18 + TypeScript
- Vite 5
- Tailwind CSS 3
- React Query 5
- React Router 6
- Axios + Zustand

## Installation

> Node.js 20+ and npm 10+ are required.

```bash
cd frontend
npm install
npm run dev
```

Environment variables should be added to the `.env` file by referencing the `env.example` file.

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── components/    # Layout and widget components
│   ├── features/      # Pages and feature modules
│   ├── lib/           # API client and utilities
│   ├── config/        # Environment and configuration files
│   └── styles/        # Tailwind and global styles
```

## Development

### Start Development Server

```bash
npm run dev
```

The application will be available at http://localhost:5173

### Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For Docker deployment, this is automatically set to `/api` (relative path via nginx proxy).

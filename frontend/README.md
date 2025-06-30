# ReadList Assistant Frontend

React-based frontend application for the ReadList Assistant book recommendation system.

## Features

- **Book Browsing**: Grid and list view modes for browsing books
- **Advanced Filtering**: Filter by genre, ratings, and search terms
- **Sorting Options**: Sort by popularity, rating, title, or author
- **Responsive Design**: Mobile-friendly interface
- **Book Details**: Detailed view with metadata and external links
- **Real-time Updates**: Live filtering and search

## Technology Stack

- **React 18**: Modern React with hooks and functional components
- **TypeScript**: Type-safe development
- **Material-UI**: Component library for consistent design
- **React Router**: Client-side routing
- **Axios**: HTTP client for API communication

## Setup

1. Install dependencies:
```bash
npm install
# or
yarn install
```

2. Start the development server:
```bash
npm start
# or
yarn start
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
src/
├── components/     # React components
│   ├── BookList.tsx      # Main book browsing interface
│   ├── BookDetail.tsx    # Individual book details
│   ├── Navbar.tsx        # Navigation bar
│   ├── FilterBar.tsx     # Filtering controls
│   └── BookTable.tsx     # Table view component
├── config.ts       # API configuration and endpoints
├── types.ts        # TypeScript type definitions
└── App.tsx         # Main application component
```

## Configuration

The frontend connects to the backend API at `http://localhost:8000` by default.
You can configure this by setting the `REACT_APP_API_BASE_URL` environment variable.

## Development

- **Hot Reload**: Changes are automatically reflected in the browser
- **TypeScript**: Full type safety and IntelliSense support
- **ESLint**: Code linting for consistent style
- **Prettier**: Automatic code formatting

## Build for Production

```bash
npm run build
# or
yarn build
```

This creates an optimized production build in the `build/` directory.

## Author

ReadList Assistant Team
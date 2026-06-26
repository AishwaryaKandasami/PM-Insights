import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PM Insights',
  description: 'Turn app store reviews into PM artifacts with AI',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

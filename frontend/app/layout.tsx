import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/providers/AuthProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL('https://etablo.japonkonutlari.com'),
  title: "BitSheet24 - Veri Senkronizasyonu | Japon Konutları",
  description: "Bitrix24 verilerinizi otomatik olarak Google Sheets'e aktarın - Japon Konutları",
  icons: {
    icon: [
      { url: '/favicon-32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-16.png', sizes: '16x16', type: 'image/png' },
    ],
    apple: '/logo-192.png',
  },
  openGraph: {
    title: 'BitSheet24 - Veri Senkronizasyonu',
    description: 'Bitrix24 verilerinizi otomatik olarak Google Sheets\'e aktarın',
    images: ['/logo.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className="antialiased bg-gradient-to-br from-slate-50 to-slate-100">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
import type { Metadata } from "next";
import { Inter_Tight, JetBrains_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";

const interTight = Inter_Tight({
  subsets: ["latin"],
  variable: "--font-inter-tight",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SDR Machine",
  description: "Máquina de Prospecção Automatizada",
};

const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem('sdr-theme');if(t)document.documentElement.setAttribute('data-theme',t)}catch(e){}})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" data-theme="light" suppressHydrationWarning>
      <head>
        <Script id="theme-init" strategy="beforeInteractive">{THEME_INIT_SCRIPT}</Script>
      </head>
      <body
        className={`${interTight.variable} ${jetbrainsMono.variable} font-sans bg-bg text-text min-h-screen`}
      >
        {children}
      </body>
    </html>
  );
}

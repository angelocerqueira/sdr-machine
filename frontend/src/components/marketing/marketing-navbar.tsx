"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";

export function MarketingNavbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function handleScroll() {
      setScrolled(window.scrollY > 80);
    }
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-bg/80 backdrop-blur-xl border-b border-border-subtle"
          : "bg-transparent border-b border-transparent"
      }`}
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <nav className="mx-auto max-w-6xl flex items-center justify-between px-6 py-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-accent-dim flex items-center justify-center">
            <span className="text-bg text-[11px] font-bold">S</span>
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-text">
            SDR <span className="text-accent">Machine</span>
          </span>
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-8">
          <a
            href="#como-funciona"
            className="text-sm text-text-secondary hover:text-text transition-colors"
          >
            Como Funciona
          </a>
          <a
            href="#features"
            className="text-sm text-text-secondary hover:text-text transition-colors"
          >
            Features
          </a>
        </div>

        {/* CTA */}
        <div className="flex items-center gap-3">
          <Link
            href="/app"
            className="hidden sm:inline text-sm text-text-secondary hover:text-text transition-colors"
          >
            Login
          </Link>
          <a
            href="#agendar"
            className="bg-accent text-bg text-sm font-semibold rounded-lg px-4 py-2 hover:bg-accent-dim transition-colors"
          >
            Agendar Demo
          </a>
        </div>
      </nav>
    </motion.header>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";

export function MarketingNavbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function handleScroll() {
      setScrolled(window.scrollY > window.innerHeight * 0.8);
    }
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.header
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      style={{
        backgroundColor: scrolled ? "color-mix(in oklch, var(--paper-0) 80%, transparent)" : "transparent",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid var(--line-2)" : "1px solid transparent",
      }}
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <nav className="mx-auto max-w-6xl flex items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-[15px] font-semibold tracking-tight" style={{ color: "var(--ink-0)" }}>
            SDR Machine
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          <a href="#como-funciona" className="text-sm transition-colors" style={{ color: "var(--ink-2)" }}>
            Como funciona
          </a>
          <a href="#pratica" className="text-sm transition-colors" style={{ color: "var(--ink-2)" }}>
            Veja na prática
          </a>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/app" className="hidden sm:inline text-sm transition-colors" style={{ color: "var(--ink-2)" }}>
            Login
          </Link>
          <a
            href="#agendar"
            className="text-sm font-medium rounded-md px-4 py-2 hover:opacity-90 transition-opacity"
            style={{ background: "var(--ink-0)", color: "var(--paper-0)" }}
          >
            Agendar demo
          </a>
        </div>
      </nav>
    </motion.header>
  );
}

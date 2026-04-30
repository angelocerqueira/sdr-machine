"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SettingsIndex() {
  const router = useRouter();
  useEffect(() => {
    if (window.matchMedia("(min-width: 1024px)").matches) {
      router.replace("/app/settings/perfil");
    }
  }, [router]);
  return null;
}

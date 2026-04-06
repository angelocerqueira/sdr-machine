"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getLeadByPublicId } from "@/lib/api";
import { LpPreview } from "@/components/lp-preview";

export default function LpPreviewPage() {
  const { id: publicId } = useParams<{ id: string }>();
  const [leadName, setLeadName] = useState("Carregando...");

  useEffect(() => {
    getLeadByPublicId(publicId).then((lead) => setLeadName(lead.nome));
  }, [publicId]);

  return <LpPreview publicId={publicId} leadName={leadName} />;
}

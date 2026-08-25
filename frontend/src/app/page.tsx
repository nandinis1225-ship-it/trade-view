"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/terminal");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-black text-white/60">
      Opening terminal…
    </main>
  );
}

import { NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function GET() {
  const upstream = await fetch(`${BACKEND}/metrics`);
  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}

import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
  const limit = req.nextUrl.searchParams.get("limit") ?? "20";
  const upstream = await fetch(`${BACKEND}/sessions?limit=${limit}`);
  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}

export async function POST() {
  const upstream = await fetch(`${BACKEND}/sessions`, { method: "POST" });
  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}

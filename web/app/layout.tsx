import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = {title:"DataMind AI",description:"Evidence-based adaptive data analysis"};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
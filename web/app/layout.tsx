import type { Metadata } from "next";
import "./globals.css";
import { StoreProvider } from "../lib/store";
import Shell from "../components/Shell";

export const metadata: Metadata = {
  title: "WhyBot · Your Company Brain",
  description: "Ask your company brain why, who owns it, and what breaks. Powered by HydraDB.",
  icons: { icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧠</text></svg>" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <StoreProvider>
          <Shell>{children}</Shell>
        </StoreProvider>
      </body>
    </html>
  );
}

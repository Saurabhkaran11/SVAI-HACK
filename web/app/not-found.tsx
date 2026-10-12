import Link from "next/link";

export default function NotFound() {
  return (
    <div className="glass card empty">
      <h2>Page not found</h2>
      <Link href="/" className="btn">Back to Ask</Link>
    </div>
  );
}

import Link from "next/link";

export default function Header() {
  return (
    <div className="border-b bg-white">
      <div className="max-w-4xl mx-auto px-8 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold">
          Bedriftshjelpen
        </Link>
        <div className="flex gap-6">
          <Link href="/" className="text-gray-400 hover:text-gray-600">
            Hjem
          </Link>
          <Link href="/kontakt" className="text-gray-400 hover:text-gray-600">
            Kontakt
          </Link>
          <Link href="/om" className="text-gray-400 hover:text-gray-600">
            Om oss
          </Link>
          <a href="https://twitter.com" className="text-gray-400 hover:text-gray-600">
            ->
          </a>
        </div>
      </div>
    </div>
  );
}

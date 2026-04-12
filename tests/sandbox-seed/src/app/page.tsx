"use client";

import Header from "@/components/Header";
import UserList from "@/components/UserList";

export default function Home() {
  return (
    <div>
      <Header />
      <div className="max-w-4xl mx-auto p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-4">Velkommen til Bedriftshjelpen</h1>
          <p className="text-gray-600">
            Vi hjelper norske bedrifter med digitalisering og effektivisering.
          </p>
        </div>

        <img src="/hero-banner.jpg" className="w-full rounded-lg mb-8" />

        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="p-6 border rounded-lg">
            <h3 className="font-semibold mb-2">Rådgivning</h3>
            <p className="text-sm text-gray-500">Få eksperthjelp med din digitale strategi.</p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="font-semibold mb-2">Utvikling</h3>
            <p className="text-sm text-gray-500">Skreddersydde løsninger for din bedrift.</p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="font-semibold mb-2">Support</h3>
            <p className="text-sm text-gray-500">Døgnåpen kundeservice når du trenger det.</p>
          </div>
        </div>

        <div
          className="bg-blue-600 text-white px-6 py-3 rounded-lg text-center cursor-pointer"
          onClick={() => window.location.href = "/kontakt"}
        >
          Ta kontakt med oss
        </div>

        <div className="mt-12">
          <h2 className="text-2xl font-bold mb-4">Våre kunder</h2>
          <UserList />
        </div>
      </div>
    </div>
  );
}

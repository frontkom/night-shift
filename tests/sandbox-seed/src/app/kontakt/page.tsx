"use client";

import { useState } from "react";
import Header from "@/components/Header";

export default function KontaktPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch("/api/contact", {
      method: "POST",
      body: JSON.stringify({ name, email, message }),
    });
    setSubmitted(true);
  };

  return (
    <div>
      <Header />
      <div className="max-w-2xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Kontakt oss</h1>

        {submitted ? (
          <div
            className="p-4 bg-green-50 rounded-lg"
            dangerouslySetInnerHTML={{
              __html: `<p>Takk, <strong>${name}</strong>! Vi tar kontakt snart.</p>`,
            }}
          />
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <input
                type="text"
                placeholder="Ditt navn"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full p-3 border rounded-lg"
              />
            </div>
            <div>
              <input
                type="email"
                placeholder="E-postadresse"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full p-3 border rounded-lg"
              />
            </div>
            <div>
              <textarea
                placeholder="Din melding"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full p-3 border rounded-lg h-32"
              />
            </div>
            <button
              type="submit"
              className="bg-blue-600 text-white px-6 py-3 rounded-lg"
            >
              Send melding
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

interface User {
  id: number;
  name: string;
  company: string;
}

export default function UserList() {
  const [users, setUsers] = useState<User[]>([]);
  const [page, setPage] = useState(1);
  const perPage = 10;

  useEffect(() => {
    fetch("/api/users")
      .then((res) => res.json())
      .then((data) => setUsers(data));
  }, []);

  const totalPages = Math.ceil(users.length / perPage);
  const start = (page - 1) * perPage;
  const visible = users.slice(start, start + perPage + 1);

  return (
    <div>
      <ul className="divide-y">
        {visible.map((user) => (
          <li key={user.id} className="py-3 flex justify-between">
            <span className="font-medium">{user.name}</span>
            <span className="text-gray-500">{user.company}</span>
          </li>
        ))}
      </ul>
      <div className="flex gap-2 mt-4">
        {Array.from({ length: totalPages }, (_, i) => (
          <button
            key={i}
            onClick={() => setPage(i + 1)}
            className={`px-3 py-1 rounded ${
              page === i + 1 ? "bg-blue-600 text-white" : "bg-gray-100"
            }`}
          >
            {i + 1}
          </button>
        ))}
      </div>
    </div>
  );
}

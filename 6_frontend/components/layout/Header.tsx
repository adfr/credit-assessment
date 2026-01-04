"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/applications": "Applications",
  "/applications/new": "New Application",
  "/monitoring": "Monitoring",
};

export function Header() {
  const pathname = usePathname();

  // Get the current page title
  const getTitle = () => {
    if (pageTitles[pathname]) {
      return pageTitles[pathname];
    }

    // Handle dynamic routes
    if (pathname.includes("/applications/") && pathname.includes("/workflow")) {
      return "Workflow";
    }
    if (pathname.includes("/applications/") && pathname.includes("/analyst")) {
      return "AI Analyst";
    }
    if (pathname.includes("/applications/")) {
      return "Application Details";
    }

    return "Credit Risk Platform";
  };

  // Generate breadcrumbs
  const getBreadcrumbs = () => {
    const parts = pathname.split("/").filter(Boolean);
    const breadcrumbs = [{ name: "Home", href: "/" }];

    let path = "";
    parts.forEach((part, index) => {
      path += `/${part}`;

      if (part === "applications") {
        breadcrumbs.push({ name: "Applications", href: "/applications" });
      } else if (part === "new") {
        breadcrumbs.push({ name: "New", href: path });
      } else if (part === "workflow") {
        breadcrumbs.push({ name: "Workflow", href: path });
      } else if (part === "analyst") {
        breadcrumbs.push({ name: "Analyst", href: path });
      } else if (part === "monitoring") {
        breadcrumbs.push({ name: "Monitoring", href: "/monitoring" });
      } else if (index === 1 && parts[0] === "applications") {
        breadcrumbs.push({ name: part.slice(0, 8) + "...", href: path });
      }
    });

    return breadcrumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{getTitle()}</h1>
          {breadcrumbs.length > 1 && (
            <nav className="mt-1 flex" aria-label="Breadcrumb">
              <ol className="flex items-center space-x-2">
                {breadcrumbs.map((crumb, index) => (
                  <li key={crumb.href} className="flex items-center">
                    {index > 0 && (
                      <svg
                        className="h-4 w-4 text-gray-400 mx-2"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                    <Link
                      href={crumb.href}
                      className={`text-sm ${
                        index === breadcrumbs.length - 1
                          ? "text-gray-500"
                          : "text-blue-600 hover:text-blue-800"
                      }`}
                    >
                      {crumb.name}
                    </Link>
                  </li>
                ))}
              </ol>
            </nav>
          )}
        </div>

        <div className="flex items-center space-x-4">
          <button className="p-2 text-gray-400 hover:text-gray-500">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </button>
          <button className="p-2 text-gray-400 hover:text-gray-500">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}

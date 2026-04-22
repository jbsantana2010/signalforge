export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">LeadForge</h1>
        <p className="text-gray-600 mb-8">Multi-tenant lead generation platform</p>
        <div className="space-x-4">
          <a
            href="/f/solar-prime"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Demo Funnel
          </a>
          <a
            href="/admin/login"
            className="inline-block px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors"
          >
            Admin Login
          </a>
        </div>
      </div>
    </div>
  );
}

export default function FunnelNotFound() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Funnel Not Found</h1>
        <p className="text-gray-600 mb-6">
          The funnel you are looking for does not exist or is no longer active.
        </p>
        <a
          href="/"
          className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          Go Home
        </a>
      </div>
    </div>
  );
}

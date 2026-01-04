'use client'

import { useState, useEffect } from 'react'

interface DashboardStats {
  total_applications: number
  pending_review: number
  approved_today: number
  declined_today: number
}

interface RecentApplication {
  application_id: string
  company_name: string
  requested_amount: number
  status: string
  submitted_at: string
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    total_applications: 0,
    pending_review: 0,
    approved_today: 0,
    declined_today: 0,
  })
  const [recentApps, setRecentApps] = useState<RecentApplication[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulated data for demo
    setStats({
      total_applications: 156,
      pending_review: 12,
      approved_today: 8,
      declined_today: 2,
    })

    setRecentApps([
      {
        application_id: 'APP-A1B2C3D4',
        company_name: 'ACME Corporation',
        requested_amount: 5000000,
        status: 'under_review',
        submitted_at: '2024-01-15T10:30:00',
      },
      {
        application_id: 'APP-E5F6G7H8',
        company_name: 'TechStart Inc',
        requested_amount: 2500000,
        status: 'approved',
        submitted_at: '2024-01-15T09:15:00',
      },
      {
        application_id: 'APP-I9J0K1L2',
        company_name: 'BuildRight LLC',
        requested_amount: 8000000,
        status: 'pending',
        submitted_at: '2024-01-15T08:00:00',
      },
    ])

    setLoading(false)
  }, [])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800'
      case 'declined':
        return 'bg-red-100 text-red-800'
      case 'under_review':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <a
          href="/applications/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          New Application
        </a>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-500">Total Applications</p>
          <p className="text-3xl font-bold text-gray-900">{stats.total_applications}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-500">Pending Review</p>
          <p className="text-3xl font-bold text-yellow-600">{stats.pending_review}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-500">Approved Today</p>
          <p className="text-3xl font-bold text-green-600">{stats.approved_today}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-500">Declined Today</p>
          <p className="text-3xl font-bold text-red-600">{stats.declined_today}</p>
        </div>
      </div>

      {/* Recent Applications */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Applications</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Application ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Company
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {recentApps.map((app) => (
                <tr key={app.application_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                    {app.application_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {app.company_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatCurrency(app.requested_amount)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(app.status)}`}>
                      {app.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <a
                      href={`/applications/${app.application_id}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      View
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Health */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Model Health</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-500">PD Model AUC</p>
            <p className="text-xl font-semibold text-gray-900">0.82</p>
            <span className="text-xs text-green-600">Healthy</span>
          </div>
          <div>
            <p className="text-sm text-gray-500">PSI Score</p>
            <p className="text-xl font-semibold text-gray-900">0.08</p>
            <span className="text-xs text-green-600">Stable</span>
          </div>
          <div>
            <p className="text-sm text-gray-500">Approval Rate</p>
            <p className="text-xl font-semibold text-gray-900">68%</p>
            <span className="text-xs text-gray-500">Last 30 days</span>
          </div>
          <div>
            <p className="text-sm text-gray-500">Avg Processing Time</p>
            <p className="text-xl font-semibold text-gray-900">2.3 days</p>
            <span className="text-xs text-gray-500">Last 30 days</span>
          </div>
        </div>
      </div>
    </div>
  )
}

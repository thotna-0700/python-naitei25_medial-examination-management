export interface Bill {
  id: number
  patientId: number
  appointmentId?: number
  amount: number
  status: BillStatus
  dueDate: string
  paidDate?: string
  description: string
  items: BillItem[]
  createdAt: string
  updatedAt: string
}

export interface BillItem {
  id: number
  serviceId: number
  serviceName: string
  quantity: number
  unitPrice: number
  totalPrice: number
}

export enum BillStatus {
  PENDING = 'PENDING',
  PAID = 'PAID',
  OVERDUE = 'OVERDUE',
  CANCELLED = 'CANCELLED'
}

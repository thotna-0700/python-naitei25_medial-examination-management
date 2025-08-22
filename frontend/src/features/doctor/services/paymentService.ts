import { api } from '../../../shared/services/api';
import type { Bill } from '../types/payment';

const paymentService = {
    async getBillByAppointmentId(appointmentId: number): Promise<Bill | null> {
        try {
            const response = await api.get(`/bills/`, {
                params: { appointment_id: appointmentId }
            });
            // API trả về danh sách trong results, lấy bill đầu tiên hoặc null nếu không có
            return response.data.results?.[0] || null;
        } catch (error: any) {
            console.error('Lỗi khi lấy hóa đơn theo appointment:', error.response?.data || error.message);
            throw error;
        }
    },
};

export { paymentService };
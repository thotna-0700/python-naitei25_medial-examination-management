import { Document, Page, Text, View, StyleSheet, Font } from "@react-pdf/renderer";
import { Bill, BillDetail } from "../../../types/payment";
import { ServiceOrder } from "../../../types/serviceOrder";
import { Patient } from "../../../types/patient";

// ✅ Font custom
Font.register({
    family: "Gesco",
    src: "/fonts/1FTV-HF-Gesco-id0oy5.ttf",
});

Font.register({
    family: "Signature",
    src: "/fonts/NVN-Motherland-Signature-ruxnss.ttf",
});

const styles = StyleSheet.create({
    page: {
        padding: 40,
        fontSize: 11,
        fontFamily: "Gesco",
        lineHeight: 1.4,
    },
    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        borderBottom: "2pt solid black",
        paddingBottom: 10,
        marginBottom: 15,
    },
    logo: { fontFamily: "Signature", fontSize: 18, fontWeight: "bold", color: "#2563eb" },
    hospitalInfo: { fontSize: 10 },
    title: { textAlign: "center", fontSize: 16, fontWeight: "bold", marginBottom: 10 },
    section: { marginBottom: 12 },
    row: { flexDirection: "row", justifyContent: "space-between", marginBottom: 4 },
    table: { display: "table", width: "100%", borderStyle: "solid", borderWidth: 1, borderRight: 0, borderBottom: 0, marginTop: 10 },
    tableRow: { flexDirection: "row" },
    tableHeader: { backgroundColor: "#f3f4f6", fontWeight: "bold" },
    tableCell: {
        borderStyle: "solid",
        borderWidth: 1,
        borderLeft: 0,
        borderTop: 0,
        padding: 5,
        fontSize: 10,
    },
    //Phần service
    sttCell: { width: "8%", textAlign: "center" }, 
    nameCell: { width: "42%" },                   
    priceCell: { width: "25%", textAlign: "right" },
    totalCell: { width: "25%", textAlign: "right" },

    //Phần booking
    nameCellB: { width: "75%" },                   
    totalCellB: { width: "35%", textAlign: "right" },
    totalCellBK: { width: "31.8%", textAlign: "right" },

    footer: { marginTop: 30, flexDirection: "row", justifyContent: "flex-end" },
    signatureBox: { textAlign: "center", width: 180, fontFamily: "Gesco" },
    bold: { fontWeight: "bold" },
    green: { color: "green" },
});

export function BillPDF({ bill, services, patient }: { bill: Bill; services: ServiceOrder[]; patient?: Patient }) {
    const totalServiceCost = services.reduce((s, svc) => s + (svc.service?.price || 0), 0);
    const totalAmountToPay = (bill.totalCost || 0) + totalServiceCost - (bill.insuranceDiscount || 0);

    return (
        <Document>
            <Page size="A4" style={styles.page}>
                {/* Header */}
                <View style={styles.header}>
                    <Text style={styles.logo}>WeCare</Text>
                    <View style={styles.hospitalInfo}>
                        <Text>PHÒNG KHÁM ĐA KHOA QUỐC TẾ WECARE</Text>
                        <Text>Số 1 Hàn Thuyên, Thủ Đức, TP.HCM</Text>
                        <Text>ĐT: 028 4567896 | Email: wecare@hospital.com.vn</Text>
                    </View>
                    <View>
                        <Text style={styles.bold}>HÓA ĐƠN</Text>
                        <Text>Số: {bill.billId}</Text>
                    </View>
                </View>

                {/* Title */}
                <Text style={styles.title}>CHI TIẾT HÓA ĐƠN THANH TOÁN</Text>

                {/* Patient Info */}
                <View style={styles.section}>
                    <Text>Họ và tên bệnh nhân: {patient?.fullName ?? "-"}</Text>
                    <Text>Ngày sinh: {patient?.birthday
                        ? new Date(patient.birthday).toLocaleDateString("vi-VN")
                        : "-"}</Text>
                    <Text>Tuổi: {patient?.age ?? "-"}</Text>
                    <Text>Địa chỉ: {patient?.address ?? "-"}</Text>
                </View>

                {/* General info */}
                <View style={styles.section}>
                    <Text>Mã hóa đơn: #{String(bill.billId || 0).padStart(4, "0")}</Text>
                    <Text>Ngày tạo: {bill.createdAt ? new Date(bill.createdAt).toLocaleDateString("vi-VN") : "-"}</Text>
                </View>

                {/* Services table */}
                <Text style={[styles.bold, { marginBottom: 6 }]}>Dịch vụ sử dụng</Text>
                <View style={styles.table}>
                    <View style={[styles.tableRow, styles.tableHeader]}>
                        <Text style={[styles.tableCell, styles.sttCell]}>STT</Text>
                        <Text style={[styles.tableCell, styles.nameCell]}>Tên dịch vụ</Text>
                        <Text style={[styles.tableCell, styles.priceCell]}>Đơn giá</Text>
                        <Text style={[styles.tableCell, styles.totalCell]}>Thành tiền</Text>
                    </View>
                    {services.map((svc, idx) => (
                        <View style={styles.tableRow} key={idx}>
                            <Text style={[styles.tableCell, styles.sttCell]}>{idx + 1}</Text>
                            <Text style={[styles.tableCell, styles.nameCell]}>{svc.service?.serviceName}</Text>
                            <Text style={[styles.tableCell, styles.priceCell]}>
                                {(svc.service?.price || 0).toLocaleString("vi-VN")} VNĐ
                            </Text>
                            <Text style={[styles.tableCell, styles.totalCell]}>
                                {(svc.service?.price || 0).toLocaleString("vi-VN")} VNĐ
                            </Text>
                        </View>
                    ))}
                    <View style={styles.tableRow}>
                        <Text style={[styles.tableCell, { flex: 3 }]}>Tổng phí dịch vụ</Text>
                        <Text style={styles.tableCell}>
                            {totalServiceCost.toLocaleString("vi-VN")} VNĐ
                        </Text>
                    </View>
                </View>

                {/* Bill Details */}
                <Text style={[styles.bold, { marginTop: 15, marginBottom: 6 }]}>
                    Chi tiết đặt lịch
                </Text>
                <View style={styles.table}>
                    <View style={[styles.tableRow, styles.tableHeader]}>
                        <Text style={[styles.tableCell, styles.nameCellB]}>Nội dung</Text>
                        <Text style={[styles.tableCell, styles.totalCellB]}>Thành tiền</Text>
                    </View>
                    {bill.billDetails?.map((detail: BillDetail, idx: number) => (
                        <View style={styles.tableRow} key={detail.detailId}>
                            <Text style={[styles.tableCell, styles.nameCellB]}>{detail.itemName}</Text>
                            {/* <Text style={[styles.tableCell, styles.priceCellB]}>
                                {detail.unitPrice?.toLocaleString("vi-VN")} VNĐ
                            </Text> */}
                            <Text style={[styles.tableCell, styles.totalCellB]}>
                                {detail.totalPrice?.toLocaleString("vi-VN")} VNĐ
                            </Text>
                        </View>
                    ))}
                    <View style={styles.tableRow}>
                        <Text style={[styles.tableCell, { flex: 3 }]}>Tổng phí đặt lịch</Text>
                        <Text style={[styles.tableCell, styles.totalCellBK]}>
                            {bill.totalCost?.toLocaleString("vi-VN")} VNĐ
                        </Text>
                    </View>
                </View>

                {/* Discounts & Total */}
                {bill.insuranceDiscount > 0 && (
                    <View style={[styles.row, { marginTop: 10 }]}>
                        <Text>BHYT chi trả</Text>
                        <Text>-{bill.insuranceDiscount.toLocaleString("vi-VN")} VNĐ</Text>
                    </View>
                )}
                <View style={[styles.row, { marginTop: 10 }]}>
                    <Text style={styles.bold}>Tổng tiền cần thanh toán</Text>
                    <Text style={[styles.bold, styles.green]}>
                        {totalAmountToPay.toLocaleString("vi-VN")} VNĐ
                    </Text>
                </View>

                {/* Signature */}
                <View style={styles.footer}>
                    <View style={styles.signatureBox}>
                        <Text style={{ marginTop: 20 }}>
                            Ngày {new Date().toLocaleDateString("vi-VN")}
                        </Text>
                        <Text style={styles.bold}>Người lập hóa đơn</Text>
                        <Text style={{ marginTop: 50 }}>(Ký, ghi rõ họ tên)</Text>
                    </View>
                </View>
            </Page>
        </Document>
    );
}

import React, { useState, useEffect } from 'react';
import { CreditCard, Receipt, CheckCircle, History, X } from 'lucide-react';
import { api } from '../api';

const Billing = () => {
  const [bills, setBills] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showGenModal, setShowGenModal] = useState(false);
  const [genData, setGenData] = useState({ appointment_id: '' });
  const [payData, setPayData] = useState({ bill_id: '', amount: '', method: 'Credit Card' });
  const [paymentProcessing, setPaymentProcessing] = useState(false);
  const [paymentError, setPaymentError] = useState('');
  const [statusUpdatingId, setStatusUpdatingId] = useState(null);

  useEffect(() => {
    fetchBills();
  }, []);

  const fetchBills = async () => {
    setLoading(true);
    try {
      const [billData, appointmentData] = await Promise.all([
        api.get('/billing/'),
        api.get('/appointments/')
      ]);
      setBills(billData);
      setAppointments(appointmentData);
    } catch (error) {
      alert('Failed to fetch bills');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    try {
      const result = await api.post('/billing/generate', { appointment_id: Number(genData.appointment_id) });
      alert(result.already_exists ? 'An invoice already exists for that appointment.' : 'Bill generated successfully!');
      setShowGenModal(false);
      setGenData({ appointment_id: '' });
      await fetchBills();
    } catch (error) {
      alert(error.message || 'Generation failed');
    }
  };

  const unbilledAppointments = appointments.filter((appointment) =>
    appointment.status !== 'cancelled' && !bills.some((bill) => bill.appointment_id === appointment.appointment_id)
  );

  const outstandingBills = bills.filter((bill) => bill.payment_status === 'unpaid' && Number(bill.remaining_amount ?? bill.amount) > 0);

  const selectBillForPayment = (billId) => {
    const selected = bills.find((bill) => String(bill.bill_id) === String(billId));
    setPayData({
      ...payData,
      bill_id: billId,
      amount: selected ? String(selected.remaining_amount ?? selected.amount) : ''
    });
    setPaymentError('');
  };

  const handlePayment = async (event) => {
    event.preventDefault();
    setPaymentProcessing(true);
    setPaymentError('');
    try {
      const result = await api.post('/billing/pay', {
        bill_id: parseInt(payData.bill_id),
        amount: parseFloat(payData.amount),
        method: payData.method
      });
      alert(result.payment_status === 'processing'
        ? 'Payment saved as In Process. The invoice will remain unpaid until the payment is confirmed.'
        : result.invoice_status === 'paid'
          ? 'Cash payment recorded. Invoice is fully paid.'
          : 'Cash payment recorded. A balance remains on this invoice.');
      setPayData({ bill_id: '', amount: '', method: 'Credit Card' });
      await fetchBills();
    } catch (error) {
      setPaymentError(error.message || 'Payment failed. Check the invoice and try again.');
    } finally {
      setPaymentProcessing(false);
    }
  };

  const updatePaymentStatus = async (bill) => {
    const nextStatus = bill.payment_status === 'paid' ? 'unpaid' : 'paid';
    if (!window.confirm(`Manually mark invoice #${bill.bill_id} as ${nextStatus}?`)) return;
    setStatusUpdatingId(bill.bill_id);
    try {
      await api.patch(`/billing/${bill.bill_id}/status`, { payment_status: nextStatus });
      await fetchBills();
    } catch (error) {
      alert(error.message || 'Unable to update invoice status');
    } finally {
      setStatusUpdatingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-clinical-dark">Billing & Payments</h1>
          <p className="text-slate-500">Manage invoicing, insurance claims, and payments.</p>
        </div>
        <button
          onClick={() => setShowGenModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Receipt size={20}/>
          <span>Generate New Bill</span>
        </button>
      </div>

      {showGenModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-xl font-bold text-clinical-dark">Generate Invoice</h2>
              <button onClick={() => setShowGenModal(false)} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
                <X size={20} className="text-slate-400"/>
              </button>
            </div>
            <form onSubmit={handleGenerate} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Appointment</label>
                <select
                  className="input-field"
                  value={genData.appointment_id}
                  onChange={e => setGenData({...genData, appointment_id: e.target.value})}
                  required
                >
                  <option value="">Choose an unbilled appointment</option>
                  {unbilledAppointments.map((appointment) => (
                    <option key={appointment.appointment_id} value={appointment.appointment_id}>
                      Appointment #{appointment.appointment_id} · Patient #{appointment.patient_id} · Doctor #{appointment.doctor_id} · {new Date(appointment.start_time).toLocaleString()}
                    </option>
                  ))}
                </select>
                {unbilledAppointments.length === 0 && <p className="mt-2 text-sm text-slate-500">There are no unbilled appointments available.</p>}
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setShowGenModal(false)} className="px-4 py-2 text-slate-500 hover:text-slate-700 font-medium">Cancel</button>
                <button type="submit" disabled={!unbilledAppointments.length} className="btn-primary px-6 disabled:opacity-50">Generate Bill</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <section id="payment-portal" className="card border border-blue-100">
        <div className="mb-5 flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-clinical-blue"><CreditCard size={22}/></div>
          <div><h2 className="text-lg font-bold">Process Payment</h2><p className="text-sm text-slate-500">Choose an unpaid invoice, enter the amount received, and select the payment method.</p></div>
        </div>
        <form onSubmit={handlePayment} className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4 xl:items-end">
          <label className="block text-xs font-bold uppercase text-slate-500">Invoice
            <select className="input-field mt-1" value={payData.bill_id} onChange={(event) => selectBillForPayment(event.target.value)} required>
              <option value="">Choose an unpaid invoice</option>
              {outstandingBills.map((bill) => <option key={bill.bill_id} value={bill.bill_id}>#INV-{bill.bill_id} · Balance ₹{Number(bill.remaining_amount ?? bill.amount).toLocaleString('en-IN')}</option>)}
            </select>
          </label>
          <label className="block text-xs font-bold uppercase text-slate-500">Payment amount (₹)
            <input type="number" min="0.01" step="0.01" max={bills.find((bill) => String(bill.bill_id) === String(payData.bill_id))?.remaining_amount ?? undefined} placeholder="Amount received" className="input-field mt-1" value={payData.amount} onChange={(event) => setPayData({ ...payData, amount: event.target.value })} required/>
          </label>
          <label className="block text-xs font-bold uppercase text-slate-500">Payment method
            <select className="input-field mt-1" value={payData.method} onChange={(event) => setPayData({ ...payData, method: event.target.value })}>
              <option>Credit Card</option><option>Debit Card</option><option>UPI</option><option>Cash</option>
            </select>
          </label>
          <button type="submit" disabled={paymentProcessing || !outstandingBills.length} className="btn-primary flex min-h-10 items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50">
            <CreditCard size={17}/>{paymentProcessing ? 'Processing…' : 'Process Payment'}
          </button>
        </form>
        {outstandingBills.length === 0 && <p className="mt-3 text-sm text-slate-500">There are no outstanding invoices to process.</p>}
        {paymentError && <p role="alert" className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{paymentError}</p>}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 card">
          <h2 className="text-lg font-bold mb-4">Recent Invoices</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                <tr className="border-b border-slate-100">
                  <th className="px-6 py-3 font-semibold">Invoice ID</th>
                  <th className="px-6 py-3 font-semibold">Amount</th>
                  <th className="px-6 py-3 font-semibold">Status</th>
                  <th className="px-6 py-3 font-semibold">Date</th>
                  <th className="px-6 py-3 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr><td colSpan="5" className="px-6 py-10 text-center text-slate-500">Loading bills...</td></tr>
                ) : bills.length === 0 ? (
                  <tr><td colSpan="5" className="px-6 py-10 text-center text-slate-500">No bills found.</td></tr>
                ) : (
                  bills.map((bill) => (
                    <tr key={bill.bill_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-sm font-medium text-slate-600">#INV-{bill.bill_id}</td>
                      <td className="px-6 py-4 text-sm font-bold">₹{Number(bill.amount).toLocaleString('en-IN')}<p className="text-xs font-normal text-slate-500">Collected ₹{Number(bill.collected_amount ?? bill.amount_paid ?? 0).toLocaleString('en-IN')} · Due ₹{Number(bill.outstanding_amount ?? bill.remaining_amount ?? bill.amount).toLocaleString('en-IN')}</p></td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                          bill.payment_status === 'paid' ? 'bg-emerald-100 text-emerald-600' : bill.payment_status === 'processing' ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-600'
                        }`}>
                          {bill.payment_status === 'processing' ? 'In Process' : bill.payment_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-500">{new Date(bill.bill_date).toLocaleDateString()}</td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap items-center gap-3">
                          {bill.payment_status === 'unpaid' && <button onClick={() => { selectBillForPayment(bill.bill_id); document.getElementById('payment-portal')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }} className="text-clinical-blue hover:underline text-sm font-medium">Pay Now</button>}
                          <button disabled={statusUpdatingId === bill.bill_id} onClick={() => updatePaymentStatus(bill)} className="text-xs font-semibold text-slate-600 hover:underline disabled:opacity-50">
                            {statusUpdatingId === bill.bill_id ? 'Updating…' : bill.payment_status === 'paid' ? 'Mark Unpaid' : 'Mark Paid'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <History size={20}/> Quick Summary
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Total Billed</span>
                <span className="font-bold">₹{bills.reduce((acc, b) => acc + Number(b.amount || 0), 0).toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Total Collected</span>
                <span className="font-bold text-emerald-600">₹{bills.reduce((acc, bill) => acc + Number(bill.collected_amount ?? bill.amount_paid ?? (bill.payment_status === 'paid' ? bill.amount : 0)), 0).toLocaleString('en-IN')}</span>
              </div>
              <div className="border-t border-slate-100 pt-3 flex justify-between text-sm">
                <span className="font-bold">Outstanding</span>
                <span className="font-bold text-rose-600">₹{bills.reduce((acc, bill) => acc + Number(bill.outstanding_amount ?? bill.remaining_amount ?? bill.amount ?? 0), 0).toLocaleString('en-IN')}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Billing;

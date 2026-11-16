import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes, useOutletContext } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import StaffAssignments from './pages/StaffAssignments';
import PatientRegistry from './pages/PatientRegistry';
import Doctors from './pages/Doctors';
import PatientProfile from './pages/PatientProfile';
import DoctorProfile from './pages/DoctorProfile';
import Appointments from './pages/Appointments';
import Billing from './pages/Billing';
import Reports from './pages/Reports';
import EHR from './pages/EHR';
import History from './pages/History';
import StaffRecord from './pages/StaffRecord';
import { canReadStaffRecords, canRunOperations, homeForRole, isClinician } from './access';

const adminOnly = (role) => role === 'admin';

const RolePage = ({ allowed, children }) => {
  const { role } = useOutletContext();
  return allowed(role) ? children : <Navigate replace to={homeForRole(role)}/>;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route element={<Layout />}>
          <Route path="/staff" element={<RolePage allowed={adminOnly}><StaffAssignments /></RolePage>} />
          <Route path="/signup" element={<Navigate replace to="/staff" />} />
          <Route path="/dashboard" element={<RolePage allowed={isClinician}><Dashboard /></RolePage>} />
          <Route path="/patients" element={<RolePage allowed={canRunOperations}><PatientRegistry /></RolePage>} />
          <Route path="/patients/:id" element={<RolePage allowed={canRunOperations}><PatientProfile /></RolePage>} />
          <Route path="/doctors" element={<RolePage allowed={isClinician}><Doctors /></RolePage>} />
          <Route path="/doctors/:id" element={<RolePage allowed={isClinician}><DoctorProfile /></RolePage>} />
          <Route path="/appointments" element={<RolePage allowed={canReadStaffRecords}><Appointments /></RolePage>} />
          <Route path="/billing" element={<RolePage allowed={canRunOperations}><Billing /></RolePage>} />
          <Route path="/reports" element={<RolePage allowed={isClinician}><Reports /></RolePage>} />
          <Route path="/ehr" element={<RolePage allowed={canReadStaffRecords}><EHR /></RolePage>} />
          <Route path="/ehr/:id" element={<RolePage allowed={canReadStaffRecords}><StaffRecord /></RolePage>} />
          <Route path="/history" element={<RolePage allowed={isClinician}><History /></RolePage>} />
        </Route>
        <Route path="*" element={<Navigate replace to="/" />} />
      </Routes>
    </Router>
  );
}

export default App;

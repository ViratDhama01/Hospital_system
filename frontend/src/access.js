export const isClinician = (role) => role === 'admin' || role === 'doctor';
export const canRunOperations = (role) => isClinician(role) || role === 'receptionist';
export const canReadStaffRecords = (role) => canRunOperations(role) || role === 'nurse';

export const roleLabel = (role) => ({
  admin: 'Chief Administrator', doctor: 'Doctor', receptionist: 'Receptionist', nurse: 'Nurse'
}[role] || role);

export const homeForRole = (role) => isClinician(role) ? '/dashboard' : '/appointments';

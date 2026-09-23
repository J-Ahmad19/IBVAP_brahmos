import React, { createContext, useContext, useState, type ReactNode } from 'react';

export type Role = 'VIEWER' | 'OPERATOR' | 'ADMIN';

interface AuthContextType {
  role: Role;
  setRole: (role: Role) => void;
  canOperate: boolean;
  canAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Default to ADMIN for easier development, but allow switching
  const [role, setRole] = useState<Role>('ADMIN');

  const value = {
    role,
    setRole,
    canOperate: role === 'OPERATOR' || role === 'ADMIN',
    canAdmin: role === 'ADMIN',
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

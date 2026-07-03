import { Outlet, useNavigate } from 'react-router-dom';
import { HomeIcon, LayoutDashboard, LogIn, LogOut } from 'lucide-react';
import { Dock, DockIcon, DockItem, DockLabel } from '@/components/core/dock';
import { clearToken } from '@/lib/api';
import { useAuthState } from '@/lib/useAuthState';

export function Layout() {
  const navigate = useNavigate();
  const loggedIn = useAuthState();

  const navItems = loggedIn
    ? [
        { title: 'Home', icon: HomeIcon, onClick: () => navigate('/') },
        { title: 'Dashboard', icon: LayoutDashboard, onClick: () => navigate('/dashboard') },
        {
          title: 'Logout',
          icon: LogOut,
          onClick: () => {
            clearToken();
            navigate('/');
          },
        },
      ]
    : [
        { title: 'Home', icon: HomeIcon, onClick: () => navigate('/') },
        { title: 'Login', icon: LogIn, onClick: () => navigate('/login') },
      ];

  return (
    <div className="min-h-screen bg-black">
      <div className="pb-28">
        <Outlet />
      </div>

      <div className="fixed bottom-2 left-1/2 max-w-full -translate-x-1/2">
        <Dock className="items-end border border-neutral-800 pb-3">
          {navItems.map((item) => (
            <DockItem
              key={item.title}
              className="aspect-square cursor-pointer rounded-full bg-neutral-800"
              onClick={item.onClick}
            >
              <DockLabel>{item.title}</DockLabel>
              <DockIcon>
                <item.icon className="h-full w-full text-neutral-300" />
              </DockIcon>
            </DockItem>
          ))}
        </Dock>
      </div>
    </div>
  );
}

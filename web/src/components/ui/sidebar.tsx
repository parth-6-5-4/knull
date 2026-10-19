"use client";

/* Adapted from Aceternity UI's sidebar (ui.aceternity.com/components/sidebar),
   retinted to the console token system, lucide icons instead of tabler,
   button-based links for in-app views, and a backdrop drawer on mobile. */
import { cn } from "@/lib/utils";
import React, { useState, createContext, useContext } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Menu, X } from "lucide-react";

export interface SidebarLinkItem {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
}

interface SidebarContextProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  animate: boolean;
}

const SidebarContext = createContext<SidebarContextProps | undefined>(undefined);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) throw new Error("useSidebar must be used within a SidebarProvider");
  return context;
};

export const SidebarProvider = ({
  children,
  open: openProp,
  setOpen: setOpenProp,
  animate = true,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  const [openState, setOpenState] = useState(false);
  const open = openProp !== undefined ? openProp : openState;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setOpenState;
  return (
    <SidebarContext.Provider value={{ open, setOpen, animate }}>
      {children}
    </SidebarContext.Provider>
  );
};

export const Sidebar = ({
  children,
  open,
  setOpen,
  animate,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => (
  <SidebarProvider open={open} setOpen={setOpen} animate={animate}>
    {children}
  </SidebarProvider>
);

export const SidebarBody = (props: { children?: React.ReactNode; className?: string }) => (
  <>
    <DesktopSidebar {...props} />
    <MobileSidebar {...props} />
  </>
);

/* Desktop: a slim rail that expands on hover. */
export const DesktopSidebar = ({ className, children }: { className?: string; children?: React.ReactNode }) => {
  const { open, setOpen, animate } = useSidebar();
  return (
    <motion.nav
      aria-label="views"
      initial={false}
      className={cn(
        "hidden h-full flex-none flex-col overflow-hidden border-r border-line bg-ink px-3 py-4 md:flex",
        className,
      )}
      animate={{ width: animate ? (open ? 224 : 64) : 224 }}
      transition={{ type: "spring", stiffness: 320, damping: 34 }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {children}
    </motion.nav>
  );
};

/* Mobile: slide-in drawer over a dimmed backdrop. Toggled from the navbar. */
export const MobileSidebar = ({ className, children }: { className?: string; children?: React.ReactNode }) => {
  const { open, setOpen } = useSidebar();
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-ink/70 backdrop-blur-sm md:hidden"
            onClick={() => setOpen(false)}
          />
          <motion.nav
            aria-label="views"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className={cn(
              "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-line bg-surface p-4 md:hidden",
              className,
            )}
          >
            <button
              aria-label="close navigation"
              onClick={() => setOpen(false)}
              className="absolute right-3 top-3 rounded-md p-1.5 text-faint transition-colors hover:bg-raised hover:text-foreground"
            >
              <X className="size-4" strokeWidth={1.75} />
            </button>
            {children}
          </motion.nav>
        </>
      )}
    </AnimatePresence>
  );
};

/* Hamburger toggle for the mobile drawer; render inside the navbar. */
export function SidebarToggle({ className }: { className?: string }) {
  const { setOpen } = useSidebar();
  return (
    <button
      aria-label="open navigation"
      onClick={() => setOpen(true)}
      className={cn(
        "flex-none rounded-md p-1.5 text-muted transition-colors hover:bg-raised hover:text-foreground md:hidden",
        className,
      )}
    >
      <Menu className="size-[18px]" strokeWidth={1.75} />
    </button>
  );
}

export const SidebarLink = ({ link, className }: { link: SidebarLinkItem; className?: string }) => {
  const { open, animate } = useSidebar();
  return (
    <button
      onClick={link.onClick}
      aria-current={link.active ? "page" : undefined}
      className={cn(
        "group/sidebar flex items-center gap-3 rounded-lg px-3 py-2 text-left text-[13px] whitespace-nowrap transition-colors",
        link.active ? "bg-overlay text-foreground" : "text-muted hover:bg-raised hover:text-foreground",
        className,
      )}
    >
      <span className={cn("flex-none", link.active ? "text-accent" : "text-faint")}>{link.icon}</span>
      <motion.span
        initial={false}
        animate={{
          display: animate ? (open ? "inline-block" : "none") : "inline-block",
          opacity: animate ? (open ? 1 : 0) : 1,
        }}
        className="!m-0 inline-block whitespace-pre !p-0 transition duration-150 group-hover/sidebar:translate-x-1"
      >
        {link.label}
      </motion.span>
    </button>
  );
};

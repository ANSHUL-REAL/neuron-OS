import { Github, Linkedin, Mail } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const CONTACT_LINKS = [
  {
    href: "https://github.com/ANSHUL-REAL",
    icon: Github,
    label: "GitHub"
  },
  {
    href: "https://www.linkedin.com/in/anshul-nautiyal-42760236b/",
    icon: Linkedin,
    label: "LinkedIn"
  },
  {
    href: "mailto:anshulnautiyal0512@gmail.com",
    icon: Mail,
    label: "Email"
  }
];

export function ContactMenu() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    window.addEventListener("mousedown", handlePointerDown);
    return () => window.removeEventListener("mousedown", handlePointerDown);
  }, []);

  return (
    <div ref={rootRef} className="contact-menu">
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="Contact Me"
        className="contact-trigger"
        type="button"
        onClick={() => setOpen((current) => !current)}
      >
        Contact Me
      </button>
      {open ? (
        <div className="contact-popover">
          {CONTACT_LINKS.map((item) => {
            const Icon = item.icon;
            return (
              <a key={item.label} className="contact-link" href={item.href} rel="noreferrer" target="_blank">
                <Icon size={16} />
                <span>{item.label}</span>
              </a>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

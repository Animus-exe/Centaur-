import React from "react";

export default function SidebarSection({ title, children }) {
  return (
    <section className="section">
      <h3 className="sectionTitle">{title}</h3>
      {children}
    </section>
  );
}
